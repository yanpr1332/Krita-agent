"""Run against an explicitly launched disposable Bridge; TEST_OUT must be a fresh output root."""
import sys,json
from pathlib import Path
sys.path.insert(0,'src');sys.path.insert(0,'.cache/test-deps')
from krita_agent.client import Client
from PIL import Image
import os
c=Client(os.environ['KRITA_AGENT_TOKEN'],int(os.environ.get('TEST_PORT','47701')))
out=Path(os.environ.get('TEST_OUT','.cache/round2/stable'))
results=[]
def run(cmd,**p):
 try:
  r=c.request(cmd,**p);results.append(dict(command=cmd,parameters=p,ok=True,result=r));return r
 except Exception as e:results.append(dict(command=cmd,parameters=p,ok=False,error=str(e)))
run('capabilities');run('canvas.create',width=256,height=256,name='Round2 acceptance');run('layer.create',name='Paint')
run('layer.tree');run('layer.inspect',name='Paint');run('layer.rename',name='Paint',new_name='Ink');run('layer.set',name='Ink',properties={'opacity':0.65,'visible':True,'locked':False,'alpha_locked':False,'color_label':2,'blending_mode':'normal'})
run('pixel.fill',name='Ink',x=10,y=10,width=80,height=80,color='#ffcc88',confirm=True)
run('layer.move',name='Ink',dx=3,dy=4);run('layer.duplicate',name='Ink',new_name='Copy');run('layer.group',name='Group');run('layer.reorder',name='Copy',index=0);run('layer.scale',name='Copy',width=64,height=64,confirm=True);run('layer.rotate',name='Copy',degrees=15,confirm=True)
run('selection.rectangle',x=10,y=10,width=30,height=30);run('selection.info');run('layer.select',name='Ink');run('selection.copy');run('selection.cut',confirm=True);run('selection.paste',x=100,y=100);run('selection.clear')
run('brush.list',query='Basic',limit=10);run('brush.inspect',name='b) Basic-5 Size')
Image.new('RGBA',(24,24),(255,0,0,128)).save(out/'input.png')
run('image.import',path='input.png',name='Imported');run('reference.import',path='input.png',name='Reference')
for kind in ['canvas','layer','region']:
 run('preview.'+kind,name='Ink',x=0,y=0,width=128,height=128,filename=kind+'.png')
run('pixel.clear',name='Ink',x=10,y=10,width=10,height=10,confirm=True)
run('history.undo');run('history.redo');run('document.list');run('document.activate',index=0);run('document.crop',x=0,y=0,width=200,height=200,confirm=True);run('layer.delete',name='Copy',confirm=True);run('document.save',path='round2.kra');run('document.export',path='round2.png');run('document.close',index=0,confirm=True);run('document.open',path='round2.kra');run('layer.tree')
# Workflow and durable job controls on the live Bridge.
import time
from krita_agent.workflow import compile_workflow
steps=compile_workflow({'steps':[{'command':'layer.rename','parameters':{'name':'Ink','new_name':'Final Ink'}},{'command':'layer.inspect','parameters':{'name':'Final Ink'}}]})
j=run('job.submit',steps=steps)
if j:
 for _ in range(100):
  status=c.request('job.status',id=j['id'])
  if status['state'] in ('completed','failed'):break
  time.sleep(.05)
 run('job.status',id=j['id']);run('job.history',id=j['id']);run('job.recover',id=j['id'])
j=run('job.submit',steps=[{'command':'document.info','parameters':{}}]*400)
if j:
 run('job.pause',id=j['id']);run('job.resume',id=j['id']);run('job.cancel',id=j['id'])
# Denials are required, not ignored errors.
for cmd,params in [('layer.delete',{'name':'Final Ink'}),('pixel.fill',{'name':'Final Ink','x':0,'y':0,'width':1,'height':1,'color':'#ffffff'}),('image.import',{'path':'../outside.png'}),('preview.canvas',{'filename':'../escape.png'}),('document.save',{'path':'round2.kra'})]:
 try:c.request(cmd,**params);results.append(dict(command=cmd,expected_denial=True,ok=False))
 except Exception as e:results.append(dict(command=cmd,expected_denial=True,ok=True,error=str(e)))
Path('docs/acceptance-evidence/round2-'+os.environ.get('TEST_BUILD','stable')+'.json').write_text(json.dumps(results,indent=2))
for r in results:
 if not r['ok']:print(r['command'],r['error'])
print('TOTAL',len(results),'FAIL',sum(not r['ok'] for r in results))
sys.exit(1 if any(not r['ok'] for r in results) else 0)
