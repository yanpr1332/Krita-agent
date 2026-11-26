"""R18 rights-aware local lineart library tests; uses SYNTHETIC pixels only."""
from copy import deepcopy
import json

import pytest
from PIL import Image, ImageDraw

from krita_agent.cli import parser_build
from krita_agent.lineart_cli_v18 import execute
from krita_agent.lineart_library_v18 import (
    REQUEST_SCHEMA, INDEX_SCHEMA, ARTICLE_SCHEMA,
    analyze_library, validate_manifest, retrieve, discover_article_images,
)
from krita_agent.protocol import TaskError


def rights(**overrides):
    v={
        "basis":"owned", "can_store_locally":True,
        "can_analyze_locally":True,
        "external_upload_permitted":False,
        "training_permitted":False,
        "can_publish_preview":False,
    }
    v.update(overrides)
    return v


def manifest():
    return {
        "schema":REQUEST_SCHEMA,
        "assets":[
            {"id":"cat_ink","file":"ink.png","kind":"lineart",
             "creator":"Synthetic fixture author",
             "source_note":"Original programmatically drawn regression ink",
             "tags":["cat","animal","thin_contour"],
             "rights":rights()},
            {"id":"cat_copy","file":"ink.png","kind":"lineart",
             "creator":"Synthetic fixture author",
             "source_note":"Same bytes; duplicate detection fixture",
             "tags":["cat","animal","outline"],
             "rights":rights()},
            {"id":"cup_color","file":"color.png","kind":"colored",
             "creator":"Synthetic fixture author",
             "source_note":"Original synthetic illustration test",
             "tags":["cup","ceramic","color"],
             "rights":rights(external_upload_permitted=True,
                             external_provider="explicit-mock-provider")},
        ],
    }


def fixtures(tmp_path):
    a=Image.new("RGB",(128,128),"white")
    brush=ImageDraw.Draw(a)
    brush.ellipse((20,15,99,115),outline="black",width=3)
    brush.line([(25,25),(40,42),(50,33)],fill="black",width=2)
    a.save(tmp_path/"ink.png")
    Image.new("RGB",(128,128),"#5f91b1").save(tmp_path/"color.png")
    return tmp_path


def test_local_r18_analysis_rights_hashes_and_desc_are_deterministic(tmp_path):
    root=fixtures(tmp_path)
    a=analyze_library(root,manifest())
    b=analyze_library(root,manifest())
    assert a==b
    assert a["schema"]==INDEX_SCHEMA
    assert a["exact_duplicate_groups"]==[["cat_copy","cat_ink"]]
    assert a["model_requests"]==0 and a["network_requests"]==0
    assert a["training_performed"] is False and a["artwork_accepted"] is False
    assert "file" not in a["assets"][0]  # private local path not stored in index
    ink=a["assets"][0]["measurements"]
    assert ink["width"]==128 and ink["height"]==128
    assert ink["paper_ratio"]>.7
    assert ink["ink_ratio"]<.3
    assert len(ink["dhash_64"])==16
    assert ink["physical_stroke_trajectory_observed"] is False
    assert ink["stylus_pressure_observed"] is False


def test_search_filters_by_specific_rights_and_never_uploads_pixels(tmp_path):
    index=analyze_library(fixtures(tmp_path),manifest())
    result=retrieve(index,["cat","animal"])
    assert [x["id"] for x in result]==["cat_copy","cat_ink"]
    assert result[0]["metadata_only"] is True
    assert result[0]["no_external_upload_performed"] is True
    assert retrieve(index,["cat"],"training")==[]
    assert retrieve(index,["cat"],"publish")==[]
    assert retrieve(index,["cup"],"external_upload")[0]["id"]=="cup_color"
    assert retrieve(index,["cup"],"training")==[]
    assert retrieve(index,["cup"],"local")[0]["id"]=="cup_color"
    with pytest.raises(TaskError,match="purpose/limit"):
        retrieve(index,["cat"],"remote-shell")
    with pytest.raises(TaskError,match="safe lowercase"):
        retrieve(index,["CAT"])


@pytest.mark.parametrize("mutate,match",[
    (lambda m: m["assets"][0]["rights"].update(basis="unknown"),"basis"),
    (lambda m: m["assets"][0]["rights"].update(can_analyze_locally=False),"consent"),
    (lambda m: m["assets"][0]["rights"].update(external_upload_permitted=True),"provider"),
    (lambda m: m["assets"][0]["rights"].update(training_permitted="yes"),"boolean"),
    (lambda m: m["assets"][0].update(file="../ink.png"),"basename"),
    (lambda m: m["assets"][0].update(file="C:\\private\\ink.png"),"basename"),
    (lambda m: m["assets"][0].update(kind="sketch_and_exec"),"kind"),
    (lambda m: m["assets"][0].update(file="x.svg"),"basenames"),
    (lambda m: m["assets"][0].update(extra="os.system"),"unknown"),
    (lambda m: m["assets"][0].update(tags=["Cat"]),"tag"),
    (lambda m: m["assets"][0].update(id="cup_color"),"duplicate"),
])
def test_manifest_denies_unknown_rights_paths_and_commands(mutate,match):
    data=manifest()
    mutate(data)
    with pytest.raises(TaskError,match=match):
        validate_manifest(data)


def test_wrong_mime_and_oversized_decoder_guard(tmp_path):
    fixtures(tmp_path)
    p=tmp_path/"fake.png"
    p.write_text("not actually a png",encoding="utf-8")
    data=manifest()
    data["assets"][0]["file"]="fake.png"
    data["assets"]=data["assets"][:1]
    with pytest.raises(TaskError,match="Unreadable"):
        analyze_library(tmp_path,data)


def test_saved_html_image_discovery_is_offline_and_review_gated():
    html="""<html><head><title>A user-exported image tutorial</title></head><body>
      <img src="https://example.com/placeholder.jpg"
           data-src="https://mmbiz.qpic.cn/mmbiz_jpg/art/0?wx_fmt=jpeg" alt="cat outline" width="960" height="1280"/>
      <img src="//mmbiz.qpic.cn/mmbiz_png/art/1?wx_fmt=png" alt="white paper sketch"/>
      <img src="https://mmbiz.qpic.cn/mmbiz_jpg/art/0?wx_fmt=jpeg"/>
      <img src="http://127.0.0.1:8888/image.png"/>
      <img src="file:///c:/secrets.png"/>
      <img src="javascript:alert(1)"/>
      <img src="https://localhost/secret.jpg"/>
      <img src="https://example.com/qr.jpg" alt="QR code" width="64" height="64"/>
      <img srcset="https://example.com/ink1.png 1x, https://example.com/ink2.png 2x"/>
      </body></html>"""
    report=discover_article_images(html)
    assert report["schema"]==ARTICLE_SCHEMA
    assert report["title"]=="A user-exported image tutorial"
    urls=[row["url"] for row in report["images"]]
    assert len(urls)==4
    assert "https://mmbiz.qpic.cn/mmbiz_jpg/art/0?wx_fmt=jpeg" in urls
    assert "https://mmbiz.qpic.cn/mmbiz_png/art/1?wx_fmt=png" in urls
    assert all(not s.startswith(("file:","javascript:")) for s in urls)
    assert all("127.0.0.1" not in s and "localhost" not in s for s in urls)
    assert report["images"][2]["potential_decoration"] is True
    assert report["downloads_performed"] is False
    assert report["network_requests"]==0
    assert report["every_image_requires_rights_review"] is True
    with pytest.raises(TaskError,match="bounded"):
        discover_article_images("a"*1_500_001)


def test_cli_explicit_output_is_exclusive_and_never_calls_native(tmp_path):
    fixtures(tmp_path)
    request=tmp_path/"source.json"
    request.write_text(json.dumps(manifest(),ensure_ascii=False),encoding="utf-8")
    output=tmp_path/"local-index.json"
    args=parser_build().parse_args([
        "lineart","analyze","--root",str(tmp_path),
        "--manifest",str(request),"--output",str(output)])
    summary=execute(args)
    assert summary["exclusive_create"] is True
    assert output.is_file()
    assert not (tmp_path/"artwork.kra").exists()
    with pytest.raises(TaskError,match="will not overwrite"):
        execute(args)
    search=parser_build().parse_args([
        "lineart","search","--index",str(output),
        "--tag","cat","--purpose","local"])
    query=execute(search)
    assert len(query["results"])==2
    html=tmp_path/"article.html"
    html.write_text("<title>Hello</title><img data-src='https://example.com/cat.png'>",
                    encoding="utf-8")
    parsed=parser_build().parse_args([
        "lineart","article-images","--html",str(html)])
    assert execute(parsed)["discovered"]==1
    assert not (tmp_path/"article.png").exists()


def test_source_sha_changes_after_source_file_mutation(tmp_path):
    fixtures(tmp_path)
    a=analyze_library(tmp_path,manifest())
    image=Image.new("RGB",(128,128),"#ffddcc")
    image.save(tmp_path/"ink.png")
    b=analyze_library(tmp_path,manifest())
    assert a["assets"][0]["sha256"]!=b["assets"][0]["sha256"]
    assert a["exact_duplicate_groups"]==b["exact_duplicate_groups"]
