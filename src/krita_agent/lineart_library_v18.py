"""R18 local-only, consent-gated line-art catalog and HTML image discovery.

No network, browser automation, model calls, training, clipboard access, or
Krita native execution. Static image measurements are weak visual descriptors,
never recovered physical pen pressure or original stroke chronology.
"""
import hashlib
import ipaddress
import math
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .protocol import TaskError

REQUEST_SCHEMA = "krita-agent-lineart-request/1"
INDEX_SCHEMA = "krita-agent-lineart-index/1"
ARTICLE_SCHEMA = "krita-agent-article-images/1"
RIGHTS = frozenset(("owned","public_domain","licensed","explicit_permission"))
KINDS = frozenset(("lineart","sketch","colored","color_pair","photo","unknown"))
PURPOSES = frozenset(("local","external_upload","training","publish"))
EXTS = frozenset((".png",".jpg",".jpeg",".webp"))
MAX_ASSETS = 100
MAX_FILE = 8*1024*1024
MAX_PIXELS = 16_000_000
ID = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
TAG = re.compile(r"[a-z][a-z0-9_-]{0,39}\Z")


def _exact_map(raw, fields, context):
    if type(raw) is not dict or set(raw)-set(fields):
        raise TaskError(context + " has unknown or invalid fields")
    return raw


def _text(raw, name, maxlen):
    if type(raw) is not str or not 1 <= len(raw.strip()) <= maxlen:
        raise TaskError(name + " must be bounded, nonempty text")
    return raw.strip()


def _validate_rights(raw):
    _exact_map(raw, ("basis","can_store_locally","can_analyze_locally",
                     "external_upload_permitted","training_permitted",
                     "can_publish_preview","external_provider"), "rights")
    basis=raw.get("basis")
    if basis not in RIGHTS:
        raise TaskError("Lineart source rights basis must be explicitly authorized")
    if raw.get("can_store_locally") is not True or raw.get("can_analyze_locally") is not True:
        raise TaskError("Lineart source requires explicit local storage and analysis consent")
    for field in ("external_upload_permitted","training_permitted",
                  "can_publish_preview"):
        if type(raw.get(field,False)) is not bool:
            raise TaskError("Lineart rights flags must be boolean")
    external=raw.get("external_upload_permitted",False)
    provider=raw.get("external_provider")
    if external:
        provider=_text(provider,"external provider",80)
    elif provider is not None:
        raise TaskError("Cannot declare provider without external upload consent")
    return {
        "basis":basis, "can_store_locally":True,"can_analyze_locally":True,
        "external_upload_permitted":external,
        "training_permitted":raw.get("training_permitted",False),
        "can_publish_preview":raw.get("can_publish_preview",False),
        "external_provider":provider,
    }


def validate_manifest(raw):
    _exact_map(raw,("schema","assets"),"lineart request")
    if raw.get("schema")!=REQUEST_SCHEMA:
        raise TaskError("Unknown lineart request schema")
    items=raw.get("assets")
    if type(items) is not list or not 1<=len(items)<=MAX_ASSETS:
        raise TaskError("Lineart request requires 1..100 assets")
    result=[];ids=set()
    for item in items:
        _exact_map(item,("id","file","kind","creator","source_note",
                         "tags","rights"),"lineart asset")
        ident=item.get("id")
        if type(ident) is not str or ID.fullmatch(ident) is None or ident in ids:
            raise TaskError("Invalid or duplicate lineart asset ID")
        ids.add(ident)
        filename=item.get("file")
        if (type(filename) is not str or not filename
                or len(filename)>180 or "\x00" in filename
                or "\\" in filename):
            raise TaskError("Unsafe lineart basename")
        path=Path(filename)
        if path.is_absolute() or len(path.parts)!=1 or path.name!=filename or path.suffix.lower() not in EXTS:
            raise TaskError("Lineart files must be authorized image basenames")
        kind=item.get("kind")
        if kind not in KINDS:
            raise TaskError("Unsupported lineart asset kind")
        raw_tags=item.get("tags",[])
        if type(raw_tags) is not list or not 1<=len(raw_tags)<=12:
            raise TaskError("Lineart requires 1..12 search tags")
        tags=[]
        for tag in raw_tags:
            if type(tag) is not str or TAG.fullmatch(tag) is None or tag in tags:
                raise TaskError("Unsafe or duplicate lineart tag")
            tags.append(tag)
        result.append({
            "id":ident,"file":filename,"kind":kind,
            "creator":_text(item.get("creator"),"creator",120),
            "source_note":_text(item.get("source_note"),"source note",240),
            "tags":sorted(tags),"rights":_validate_rights(item.get("rights")),
        })
    return {"schema":REQUEST_SCHEMA,"assets":result}


def _safe_local_image(root,filename):
    base=Path(root).expanduser()
    if base.is_symlink():
        raise TaskError("Authorized image root must not be a symlink")
    base=base.resolve()
    if not base.is_dir():
        raise TaskError("Authorized image root missing")
    item=base/filename
    if item.is_symlink() or not item.is_file() or item.resolve().parent!=base:
        raise TaskError("Lineart image missing, a link, or escapes the authorized root")
    if not 0<item.stat().st_size<=MAX_FILE:
        raise TaskError("Lineart image exceeds 8 MiB source budget")
    return item


def _descriptor(path):
    try:
        from PIL import Image,ImageOps,UnidentifiedImageError
    except ImportError as exc:
        raise TaskError("Pillow is required for bounded local lineart inspection") from exc
    try:
        with Image.open(path) as im:
            if im.width*im.height>MAX_PIXELS or min(im.size)<8:
                raise TaskError("Lineart dimensions exceed safe 16MP bounds")
            if im.format not in ("PNG","JPEG","WEBP"):
                raise TaskError("Unexpected lineart image format")
            image=ImageOps.exif_transpose(im).convert("L")
            image.thumbnail((256,256))
            width,height=im.size
        values=list(image.getdata())
        n=len(values)
        ink=sum(v<128 for v in values)
        paper=sum(v>=224 for v in values)
        # Directional edge proxy; does not recover stroke order, pressure or
        # accurate vector paths. Use bounded 128x128 image for CPU cost.
        smaller=image.resize((128,128))
        q=list(smaller.getdata())
        gx=gy=0
        for y in range(127):
            for x in range(127):
                i=y*128+x
                gx+=abs(q[i+1]-q[i])
                gy+=abs(q[i+128]-q[i])
        dh=image.resize((9,8))
        dhp=list(dh.getdata())
        d_hash=0
        for y in range(8):
            for x in range(8):
                d_hash=(d_hash<<1)|(1 if dhp[y*9+x]>dhp[y*9+x+1] else 0)
        return {
            "width":width,"height":height,
            "ink_ratio":round(ink/n,5),
            "paper_ratio":round(paper/n,5),
            "edge_horizontal":round(gx/(127*127*255),5),
            "edge_vertical":round(gy/(127*127*255),5),
            "dhash_64":"%016x"%d_hash,
            "classifier":"numeric_pixel_proxy_only",
            "physical_stroke_trajectory_observed":False,
            "stylus_pressure_observed":False,
        }
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        raise TaskError("Unreadable or unsafe local lineart image") from exc


def analyze_library(root,raw_manifest):
    """Analyze explicitly permitted local images into a nonimage JSON index."""
    manifest=validate_manifest(raw_manifest)
    assets=[];hash_to_ids=defaultdict(list)
    for item in manifest["assets"]:
        image=_safe_local_image(root,item["file"])
        h=hashlib.sha256()
        with image.open("rb") as f:
            for chunk in iter(lambda:f.read(65536),b""):
                h.update(chunk)
        sha=h.hexdigest()
        measures=_descriptor(image)
        hash_to_ids[sha].append(item["id"])
        assets.append({
            "id":item["id"],"kind":item["kind"],
            "sha256":sha,
            "creator":item["creator"],
            "source_note":item["source_note"],
            "tags":item["tags"],"rights":item["rights"],
            "measurements":measures,
            "review_status":"pending",
            "human_visual_quality_accepted":False,
        })
    return {
        "schema":INDEX_SCHEMA,"assets":assets,
        "exact_duplicate_groups":sorted(
            [sorted(v) for v in hash_to_ids.values() if len(v)>1]),
        "model_requests":0,"network_requests":0,"native_effects":"none",
        "training_performed":False,
        "pixel_paths_collected":False,
        "artwork_accepted":False,
    }


def retrieve(index,tags,purpose="local",limit=5):
    """Return ranked *metadata* with explicit purpose permission filtering."""
    if type(index) is not dict or index.get("schema")!=INDEX_SCHEMA:
        raise TaskError("Unknown lineart index schema")
    if purpose not in PURPOSES or type(limit) is not int or not 1<=limit<=20:
        raise TaskError("Invalid search purpose/limit")
    if type(tags) is not list or not 1<=len(tags)<=12 or any(
            type(x) is not str or TAG.fullmatch(x) is None for x in tags):
        raise TaskError("Search requires safe lowercase tags")
    entries=index.get("assets")
    if type(entries) is not list or len(entries)>MAX_ASSETS:
        raise TaskError("Unsafe lineart index contents")
    q=set(tags);candidates=[]
    for item in entries:
        if type(item) is not dict or type(item.get("tags")) is not list:
            raise TaskError("Malformed lineart index entry")
        rights=item.get("rights")
        if type(rights) is not dict:
            raise TaskError("Index missing source rights")
        allowed={
            "local":rights.get("can_analyze_locally") is True,
            "external_upload":rights.get("external_upload_permitted") is True,
            "training":rights.get("training_permitted") is True,
            "publish":rights.get("can_publish_preview") is True,
        }[purpose]
        if not allowed:
            continue
        matching=sorted(q.intersection(item["tags"]))
        if not matching:
            continue
        # Intersection count first, then tag precision; deterministic ties.
        score=round(len(matching)/len(q),5)
        candidates.append({
            "id":item["id"],"sha256":item["sha256"],
            "matching_tags":matching,"score":score,
            "metadata_only":True,
            "source_permission_checked_for":purpose,
            "no_external_upload_performed":True,
        })
    return sorted(candidates,key=lambda c:(-c["score"],c["id"]))[:limit]


def _secure_http_url(value):
    if type(value) is not str or not value or len(value)>4096:
        return None
    value=value.strip()
    if value.startswith("//"):
        value="https:"+value
    try:
        parsed=urlsplit(value)
        host=parsed.hostname
        port=parsed.port
        if parsed.scheme not in ("http","https") or not host or port not in (None,80,443):
            return None
        if parsed.username or parsed.password:
            return None
        if host.lower() in ("localhost","localhost.localdomain") or host.lower().endswith((".local",".internal")):
            return None
        try:
            ip=ipaddress.ip_address(host)
            if not ip.is_global:
                return None
        except ValueError:
            pass
    except ValueError:
        return None
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,parsed.query,""))


class _ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images=[];self.title="";self.in_title=False
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="title":
            self.in_title=True
        if tag!="img" or len(self.images)>=200:
            return
        url=None
        for key in ("data-src","data-original","src","data-lazy-src"):
            url=_secure_http_url(d.get(key))
            if url:
                break
        if not url and d.get("srcset"):
            for item in d["srcset"].split(",")[:8]:
                candidate=_secure_http_url(item.strip().split(" ")[0])
                if candidate:
                    url=candidate;break
        if not url or any(row["url"]==url for row in self.images):
            return
        dims={}
        for key in ("width","height"):
            s=d.get(key)
            dims[key]=int(s) if s and s.isdigit() and int(s)<100000 else None
        alt=(d.get("alt") or "")[:120]
        deco=any(word in alt.lower() for word in (
            "qr","二维码","logo","avatar","头像","公众号"))
        deco=deco or (dims["width"] is not None and
                      dims["height"] is not None and
                      max(dims.values())<=96)
        self.images.append({
            "index":len(self.images),"url":url,"alt":alt,**dims,
            "potential_decoration":deco,
            "rights_review_required":True,
        })
    def handle_endtag(self,tag):
        if tag=="title":self.in_title=False
    def handle_data(self,data):
        if self.in_title and len(self.title)<180:
            self.title+=data[:180-len(self.title)]


def discover_article_images(html):
    """Parse a user-exported document; discover HTTPS image links, DO NOT GET."""
    if type(html) is not str or len(html)>1_500_000:
        raise TaskError("HTML must be a bounded locally supplied text")
    parser=_ArticleParser()
    try:
        parser.feed(html)
        parser.close()
    except (ValueError,AssertionError) as exc:
        raise TaskError("Malformed HTML article") from exc
    return {
        "schema":ARTICLE_SCHEMA,"title":parser.title.strip()[:180],
        "images":parser.images,
        "discovered":len(parser.images),
        "network_requests":0,"model_requests":0,
        "downloads_performed":False,"access_controls_bypassed":False,
        "every_image_requires_rights_review":True,
    }
