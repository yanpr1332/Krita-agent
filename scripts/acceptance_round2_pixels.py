"""Pixel assertions against a disposable live Krita document."""
import argparse,json,sys,time
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image,ImageChops
from krita_agent.client import Client
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session', default='.cache/round2/current.json', help='Private test session JSON: token, out, build; Bridge port 47721')
args=parser.parse_args()
info=json.loads(Path(args.session).read_text());out=Path(info['out']);c=Client(info['token'],47721);records=[];counter=int(time.time())

def req(cmd,**p):return c.request(cmd,**p)
def snapshot():
 global counter
 counter+=1;name=f'pixel-{counter:03}.png';req('document.export',path=name);return Image.open(out/name).convert('RGBA')
def check(name,fn):
 try: detail=fn();records.append({'check':name,'ok':True,'detail':detail})
 except Exception as e:records.append({'check':name,'ok':False,'error':str(e)})
def equal(actual,expected,tolerance=0):
 diff=ImageChops.difference(actual,expected)
 assert max(v[1] for v in diff.getextrema())<=tolerance, diff.getextrema()
def fresh(name):
 req('canvas.create',width=128,height=128,name=name)
 for node in req('layer.tree'):req('layer.delete',id=node['id'],confirm=True)
 req('layer.create',name='Pixels')
def fill(x,y,w,h,color):req('pixel.fill',name='Pixels',x=x,y=y,width=w,height=h,color=color,confirm=True)
def pixel(image,xy,expected,tol=0):
 actual=image.getpixel(xy);assert all(abs(a-b)<=tol for a,b in zip(actual,expected)),(xy,actual,expected)

def imports():
 fresh('Import RGBA');im=Image.new('RGBA',(8,8),(230,40,70,128));im.save(out/'fixture.png');req('image.import',path='fixture.png',name='Imported',x=10,y=12);a=snapshot();pixel(a,(12,14),(230,40,70,128),2);pixel(a,(0,0),(0,0,0,0));return 'RGBA channels and alpha match within 2/255'
def selection():
 fresh('Selection');fill(10,10,12,8,'#ff0000');before=snapshot();req('selection.rectangle',x=10,y=10,width=12,height=8);req('selection.copy');req('selection.paste',x=50,y=40);req('selection.clear');a=snapshot();pixel(a,(52,42),(255,0,0,255));pixel(a,(12,12),(255,0,0,255));req('selection.rectangle',x=10,y=10,width=12,height=8);req('selection.cut',confirm=True);req('selection.clear');b=snapshot();pixel(b,(12,12),(0,0,0,0));pixel(b,(52,42),(255,0,0,255));return 'copy/paste destination and cut source verified'
def transforms():
 fresh('Transforms');fill(10,20,20,10,'#00ff00');req('layer.move',name='Pixels',dx=5,dy=7);a=snapshot();assert a.getbbox()==(15,27,35,37),a.getbbox();req('layer.scale',name='Pixels',width=40,height=20,origin_x=15,origin_y=27,confirm=True);b=snapshot();bbox=b.getbbox();assert abs((bbox[2]-bbox[0])-40)<=4 and abs((bbox[3]-bbox[1])-20)<=4,bbox;req('layer.rotate',name='Pixels',degrees=90,confirm=True);d=snapshot();bb=d.getbbox();assert abs((bb[2]-bb[0])-20)<=4 and abs((bb[3]-bb[1])-40)<=4,bb;return {'move':a.getbbox(),'scale':bbox,'rotate':bb}
def history():
 fresh('Undo redo');req('brush.configure',preset='b) Basic-5 Size',size=12,color='#ff0000');blank=snapshot();req('draw.line',x1=20,y1=20,x2=80,y2=20);paint=snapshot();assert paint.getbbox();req('history.undo');time.sleep(.3);equal(snapshot(),blank);req('history.redo');time.sleep(.3);equal(snapshot(),paint);return 'native stroke undo blank and redo byte-equivalent RGBA'
def properties():
 fresh('Properties');fill(10,10,20,10,'#0000ff');original=snapshot();req('layer.set',name='Pixels',properties={'visible':False});assert snapshot().getbbox() is None;req('layer.set',name='Pixels',properties={'visible':True,'opacity':0.5});pixel(snapshot(),(15,15),(0,0,255,128),1);req('layer.set',name='Pixels',properties={'opacity':1.0});equal(snapshot(),original);req('pixel.clear',name='Pixels',x=10,y=10,width=20,height=10,confirm=True);assert snapshot().getbbox() is None;return 'visibility, opacity, restored pixels and clear'
def previews_roundtrip():
 fresh('Preview roundtrip');fill(10,10,20,10,'#ff0000');base=snapshot()
 req('preview.region',x=0,y=0,width=128,height=128,filename=f'region-{counter}.png');equal(Image.open(out/f'region-{counter}.png').convert('RGBA'),base)
 req('preview.canvas',width=128,height=128,filename=f'canvas-{counter}.png');equal(Image.open(out/f'canvas-{counter}.png').convert('RGBA'),base)
 req('preview.layer',name='Pixels',width=128,height=128,filename=f'layer-{counter}.png');equal(Image.open(out/f'layer-{counter}.png').convert('RGBA'),base)
 req('layer.duplicate',name='Pixels',new_name='Duplicate');req('layer.set',name='Pixels',properties={'visible':False});equal(snapshot(),base)
 req('layer.delete',name='Duplicate',confirm=True);assert snapshot().getbbox() is None
 req('layer.set',name='Pixels',properties={'visible':True});req('document.crop',x=5,y=5,width=64,height=64,confirm=True);cropped=snapshot();equal(cropped,base.crop((5,5,69,69)))
 req('document.save',path=f'pixels-{counter}.kra');saved=counter;req('document.open',path=f'pixels-{saved}.kra');equal(snapshot(),cropped)
 return 'region/canvas/layer previews, duplicate/delete, crop and KRA reopen match all RGBA pixels'
def alpha_paste_blend():
 fresh('Alpha compositing');im=Image.new('RGBA',(8,8),(255,0,0,128));im.save(out/'alpha-fixture.png');req('image.import',path='alpha-fixture.png',name='Source',x=10,y=10)
 req('selection.rectangle',x=10,y=10,width=8,height=8);req('selection.copy');req('layer.select',name='Pixels');fill(40,40,8,8,'#0000ff');req('selection.paste',x=40,y=40);req('selection.clear');pixel(snapshot(),(42,42),(128,0,127,255),1)
 req('layer.set',name='Source',properties={'visible':False});req('layer.create',name='Blend');req('pixel.fill',name='Blend',x=40,y=40,width=8,height=8,color='#00ff00',confirm=True);req('layer.set',name='Blend',properties={'blending_mode':'multiply'});pixel(snapshot(),(42,42),(0,0,0,255),1)
 return 'semi-transparent selection source-over and multiply blending verified'
def references_order():
 fresh('Reference and stacking');im=Image.new('RGBA',(8,8),(25,200,80,255));im.save(out/'reference-fixture.png');req('reference.import',path='reference-fixture.png',name='Linked');pixel(snapshot(),(2,2),(25,200,80,255),1)
 req('layer.set',name='Linked',properties={'visible':False});assert snapshot().getbbox() is None
 fill(10,10,8,8,'#ff0000');req('layer.create',name='Top');req('pixel.fill',name='Top',x=10,y=10,width=8,height=8,color='#0000ff',confirm=True);pixel(snapshot(),(12,12),(0,0,255,255));req('layer.reorder',name='Top',index=0);pixel(snapshot(),(12,12),(255,0,0,255))
 return 'linked file pixels and layer stacking order verified'
for name,fn in [('import_rgba',imports),('selection_pixels',selection),('transform_pixels',transforms),('undo_redo_pixels',history),('properties_clear',properties),('previews_roundtrip',previews_roundtrip),('alpha_paste_blend',alpha_paste_blend),('references_order',references_order)]:check(name,fn)
f=Path('docs/acceptance-evidence')/('round2-pixels-'+info['build']+'.json');f.write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2));sys.exit(any(not r['ok'] for r in records))

