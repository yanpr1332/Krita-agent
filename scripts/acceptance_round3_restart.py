"""Real process restart acceptance against the owned current test session."""
import os,sys,json,time,subprocess,secrets,hashlib,zipfile,uuid
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image,ImageChops
from krita_agent.client import Client
v=json.loads(Path('.cache/round2/current.json').read_text());out=Path(v['out']);c=Client(v['token'],47721);results=[]
exe={'stable':r'D:\computer\Krita\Krita (x64)\bin\krita.exe','qt5':r'D:\computer\Krita\Krita_Next\QT5\krita-x64-5.4.0-prealpha-2687e5d4\bin\krita.exe','qt6':r'D:\computer\Krita\Krita_Next\QT6\krita-x64-6.1.0-prealpha-2687e5d4\bin\krita.exe'}[v['build']]
def q(cmd,**p):return c.request(cmd,**p)
def restart():
 global c
 subprocess.run(['taskkill','/PID',str(v['pid']),'/F'],check=True,capture_output=True)
 v['token']=secrets.token_urlsafe(32);env=os.environ.copy();env.update(KRITA_AGENT_TOKEN=v['token'],KRITA_AGENT_PORT='47721',KRITA_AGENT_OUTPUT_DIR=str(out),KRITA_AGENT_INPUT_DIR=str(out),KRITA_AGENT_DOCK='1')
 proc=subprocess.Popen([exe,'--nosplash'],env=env);v['pid']=proc.pid;Path('.cache/round2/current.json').write_text(json.dumps(v));c=Client(v['token'],47721)
 for _ in range(90):
  try:q('status');return
  except Exception:time.sleep(.5)
 raise RuntimeError('restart not connected')
def shot():
 r=q('preview.canvas',width=96,height=96,filename='restart/'+uuid.uuid4().hex+'.png');return Image.open(r['path']).convert('RGBA')
q('canvas.create',width=96,height=96,name='Restart safety');q('layer.create',name='Ink');q('document.save',path='transactions/cross-session.kra');transaction=q('pixel.transaction.fill',name='Ink',x=10,y=10,width=8,height=8,color='#ff0000',confirm=True);q('document.save',path='transactions/cross-session.kra',overwrite=True);q('selection.rectangle',x=10,y=10,width=8,height=8);q('selection.copy');q('clipboard.save',name='restart.kclip');q('selection.clear')
steps=[{'command':'checkpoint.create','parameters':{}},{'command':'draw.line','parameters':{'x1':40,'y1':40,'x2':70,'y2':40}}]+[{'command':'document.info','parameters':{}}]*398
job=q('job.submit',steps=steps)
for _ in range(200):
 cps=q('checkpoint.list');matches=[x for x in cps if x['job_id']==job['id']]
 if matches:break
 time.sleep(.01)
q('job.pause',id=job['id']);cp=q('checkpoint.inspect',id=matches[0]['id']);original=Path(cp['path']).read_bytes();before=shot();restart();assert q('status')['active_document'] is False
state=q('job.status',id=job['id']);assert state['state']=='interrupted';assert q('job.recover',id=job['id'])['replay_safe'] is False
q('document.open',path='transactions/cross-session.kra');q('pixel.transaction.undo',id=transaction['id'],confirm=True);assert shot().getpixel((12,12))[:3]==(255,255,255);q('pixel.transaction.redo',id=transaction['id'],confirm=True);assert shot().getpixel((12,12))[:3]==(255,0,0)
rest=q('checkpoint.restore',id=cp['id'],confirm=True);assert rest['restored']['path']!=cp['path'];assert Path(cp['path']).read_bytes()==original
with zipfile.ZipFile(cp['path']) as z:
 import io
 expected=Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA')
assert all(hi==0 for lo,hi in ImageChops.difference(expected,shot()).getextrema())
q('clipboard.load',name='restart.kclip');q('selection.rectangle',x=10,y=10,width=8,height=8);q('layer.select',name='Ink');q('selection.paste',x=60,y=60);q('selection.clear');assert shot().getpixel((62,62))[:3]==(255,0,0)
res=q('checkpoint.resume',id=cp['id'],confirm=True)
for _ in range(500):
 terminal=q('job.status',id=res['new_job']['id'])
 if terminal['state'] in ('completed','failed'):break
 time.sleep(.03)
assert terminal['state']=='completed',terminal
assert Path(cp['path']).read_bytes()==original
results.append({'case':'crash_restore_resume_cross_session_clip','ok':True,'checkpoint':cp,'interrupted':state,'resumed':terminal,'from_step':res['from_step'],'original_unchanged':True,'clipboard_pixels':True,'persisted_pixel_undo_redo':True,'zero_auto_playback':True})
Path('docs/acceptance-evidence/round3-restart-'+v['build']+'.json').write_text(json.dumps(results,indent=2));print('restart/copy/suffix/clipboard passed')
