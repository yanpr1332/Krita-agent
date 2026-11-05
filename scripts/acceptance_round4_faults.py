"""Real accepted-but-lost reply and owned-process overlay recovery checks."""
import sys,os,json,time,uuid,secrets,subprocess,zipfile,io,hashlib
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image,ImageChops
from krita_agent.client import Client
from krita_agent import scheduler
v=json.loads(Path('.cache/round2/current.json').read_text());out=Path(v['out']);c=Client(v['token'],47721,timeout=60);results=[]
def q(cmd,**p):return c.request(cmd,**p)
def equal(a,b):assert a.size==b.size and all(hi==0 for lo,hi in ImageChops.difference(a,b).getextrema())
def export():return Path(q('document.export',path='recovery/'+uuid.uuid4().hex+'.png')['path'])
main=json.loads(Path('docs/acceptance-evidence/round4-native-'+v['build']+'.json').read_text());long=next(r['result'] for r in main if r['case']=='1200_native_steps_checkpoints');cp=long['ledger']['completed'][-1]['checkpoint'];q('checkpoint.restore',id=cp['id'],confirm=True)
class DropReply:
 calls=0;accepted=None
 def submit(self,steps):
  self.calls+=1;self.accepted=c.submit(steps);raise TimeoutError('Injected loss AFTER native acceptance')
normal=scheduler.run(c,{'steps':[{'command':'document.info','parameters':{}}]*2},out/('ledger-metadata-'+uuid.uuid4().hex),batch_steps=1,poll_interval=.05);assert normal['state']=='completed';saved=scheduler.inspect_ledger(normal['ledger']);assert all(x['batch_sha256'] and x['elapsed_seconds']>=0 for x in saved['completed']);results.append({'case':'durable_completed_batch_metadata','ok':True,'ledger':saved})
wrapper=DropReply();r=scheduler.run(wrapper,{'steps':[{'command':'document.info','parameters':{}}]},out/('lost-reply-'+uuid.uuid4().hex));assert r['state']=='unknown_needs_review' and wrapper.calls==1
for _ in range(200):
 s=q('job.status',id=wrapper.accepted['id'])
 if s['state']=='completed':break
 time.sleep(.03)
assert s['state']=='completed';results.append({'case':'accepted_reply_lost','ok':True,'submit_calls':1,'ledger':r,'actual_job':s})
exe={'stable':r'D:\computer\Krita\Krita (x64)\bin\krita.exe','qt5':r'D:\computer\Krita\Krita_Next\QT5\krita-x64-5.4.0-prealpha-2687e5d4\bin\krita.exe','qt6':r'D:\computer\Krita\Krita_Next\QT6\krita-x64-6.1.0-prealpha-2687e5d4\bin\krita.exe'}[v['build']]
def restart():
 global c
 subprocess.run(['taskkill','/PID',str(v['pid']),'/F'],check=True,capture_output=True);v['token']=secrets.token_urlsafe(32);env=dict(os.environ,QT_SCALE_FACTOR={'stable':'1','qt5':'1.25','qt6':'1.5'}[v['build']],KRITA_AGENT_TOKEN=v['token'],KRITA_AGENT_PORT='47721',KRITA_AGENT_OUTPUT_DIR=str(out),KRITA_AGENT_INPUT_DIR=str(out),KRITA_AGENT_DOCK='1');proc=subprocess.Popen([exe,'--nosplash'],env=env);v['pid']=proc.pid;Path('.cache/round2/current.json').write_text(json.dumps(v));c=Client(v['token'],47721,timeout=60)
 for _ in range(180):
  try:q('status');return
  except Exception:time.sleep(.3)
 raise AssertionError('restart connection failed')
for phase in ['after_overlay_before_patch','after_patch_before_save']:
 backup=q('checkpoint.create');raw=Path(backup['path']).read_bytes();before=Image.open(export()).convert('RGBA');layer=q('revision.overlay.begin',checkpoint_id=backup['id'],confirm=True,name='CrashOverlay-'+uuid.uuid4().hex[:8])
 if phase=='after_patch_before_save':q('pixel.transaction.fill',id=layer['id'],x=2500,y=2500,width=8,height=8,color='#ff0000',confirm=True);assert Image.open(export()).convert('RGBA').getpixel((2502,2502))[:3]==(255,0,0)
 j=c.submit([{'command':'document.info','parameters':{}}]*400);q('job.pause',id=j['id']);restart();assert q('status')['active_document'] is False;assert q('job.status',id=j['id'])['state']=='interrupted';q('checkpoint.restore',id=backup['id'],confirm=True);equal(Image.open(export()).convert('RGBA'),before);assert Path(backup['path']).read_bytes()==raw
 results.append({'case':phase,'ok':True,'checkpoint':backup['id'],'zero_auto_replay':True,'rgba_equal':True,'original_checkpoint_unchanged':True,'graph_nodes':len(q('document.graph')['nodes'])})
limits=q('runtime.limits');assert limits['protocol']==1 and limits['max_steps']==400 and limits['max_stroke_points']==2048;results.append({'case':'v1_limits_unchanged','ok':True,'limits':limits})
Path('docs/acceptance-evidence/round4-faults-'+v['build']+'.json').write_text(json.dumps(results,indent=2));print('lost reply and two integrated 4096 overlay crashes passed')
