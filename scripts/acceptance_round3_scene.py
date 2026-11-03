"""Structured scene and first-round drawing regression on disposable documents."""
import sys,json,time,zipfile
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image
from krita_agent.client import Client
from krita_agent.creative_plans import compile_scene
from krita_agent.protocol import compile_task
v=json.loads(Path('.cache/round2/current.json').read_text());c=Client(v['token'],47721);out=Path(v['out']);results=[]
for kind,file,compiler in [('scene','examples/round3-scene.json',compile_scene),('round1-pressure','examples/pressure-demo.json',compile_task)]:
 spec=json.loads(Path(file).read_text());steps=compiler(spec);assert steps==compiler(spec)
 for step in steps:
  if step['command']=='draw.stroke':
   pts=step['parameters']['points'];assert len(pts)<=2048;assert all(0<=p.get('pressure',1)<=1 for p in pts);assert all(b.get('time_ms',0)>=a.get('time_ms',0) for a,b in zip(pts,pts[1:]))
 j=c.submit(steps)
 for _ in range(1000):
  s=c.request('job.status',id=j['id'])
  if s['state'] in ('completed','failed'):break
  time.sleep(.03)
 assert s['state']=='completed',s
 layers=c.request('layer.tree');name='scene-regression-'+kind+'.kra';c.request('document.save',path=name);c.request('document.export',path='scene-regression-'+kind+'.png')
 with zipfile.ZipFile(out/name) as z:assert z.testzip() is None and 'maindoc.xml' in z.namelist()
 c.request('document.open',path=name);assert [x['name'] for x in c.request('layer.tree')]==[x['name'] for x in layers]
 im=Image.open(out/('scene-regression-'+kind+'.png')).convert('RGB');assert len(im.getcolors(im.width*im.height))>1
 results.append({'case':kind,'ok':True,'steps':len(steps),'job':s,'layers':[x['name'] for x in layers],'size':im.size})
Path('docs/acceptance-evidence/round3-scene-round1-'+v['build']+'.json').write_text(json.dumps(results,indent=2));print('scene and pressure-demo passed')
