"""Controlled crash tests using a temporary instrumented copy of the plugin.
The fixture gates before save, after durable manifest and after 10 real stroke
segments. Production plugin is restored in finally; no transport eval is added.
"""
import sys,os,json,time,subprocess,secrets,shutil,uuid,io
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image,ImageChops
from krita_agent.client import Client
fixture=Path('.cache/round3-instrumented');executables={'stable':r'D:\computer\Krita\Krita (x64)\bin\krita.exe','qt5':r'D:\computer\Krita\Krita_Next\QT5\krita-x64-5.4.0-prealpha-2687e5d4\bin\krita.exe','qt6':r'D:\computer\Krita\Krita_Next\QT6\krita-x64-6.1.0-prealpha-2687e5d4\bin\krita.exe'}
proc=None
try:
 subprocess.run([sys.executable,"scripts/prepare_round3_crash_fixture.py"],check=True)
 subprocess.run([sys.executable,str(fixture/'scripts/install_plugin.py'),'--apply','--replace'],check=True)
 for build,exe in executables.items():
  rows=[]
  for phase in ['before_save','after_save','during_stroke']:
   out=(Path('.cache')/('round3-crash-'+build+'-'+phase+'-'+uuid.uuid4().hex[:8])).resolve();out.mkdir()
   token=secrets.token_urlsafe(32);env=os.environ.copy();env.update(KRITA_AGENT_TOKEN=token,KRITA_AGENT_PORT='47731',KRITA_AGENT_OUTPUT_DIR=str(out),KRITA_AGENT_INPUT_DIR=str(out),KRITA_AGENT_DOCK='1',KRITA_ACCEPTANCE_CRASH_PHASE=phase)
   def start():
    global proc,c
    proc=subprocess.Popen([exe,'--nosplash'],env=env);c=Client(token,47731,timeout=60)
    for _ in range(180):
     try:c.request('status');return
     except Exception:time.sleep(.3)
    raise RuntimeError('startup failed')
   start();c.request('canvas.create',width=128,height=128,name='Crash fixture');c.request('layer.create',name='Ink');c.request('brush.configure',preset='b) Basic-5 Size',size=8,color='#ff0000')
   points=[{'x':10+i%100,'y':10+(i//100)%100,'pressure':.6} for i in range(64)]
   steps=[{'command':'checkpoint.create','parameters':{}},{'command':'draw.stroke','parameters':{'mode':'segmented','points':points}}]+[{'command':'document.info','parameters':{}}]*398
   job=c.submit(steps);event=out/'crash-event.json'
   for _ in range(2000):
    if event.is_file():break
    time.sleep(.005)
   assert event.is_file(),'fixture gate not reached';e=json.loads(event.read_text());assert e['pid']==proc.pid
   proc.terminate();proc.wait(timeout=15)
   import socket
   try:
    connection=socket.create_connection(('127.0.0.1',47731),timeout=.3)
   except OSError:pass
   else:connection.close();raise AssertionError('test listener survived process exit')
   env.pop('KRITA_ACCEPTANCE_CRASH_PHASE');start();assert c.request('status')['active_document'] is False
   state=c.request('job.status',id=job['id']);assert state['state']=='interrupted';checkpoints=c.request('checkpoint.list')
   if phase=='before_save':assert not checkpoints and not list((out/'checkpoints').glob('*.kra'))
   else:
    assert len(checkpoints)==1;cp=c.request('checkpoint.inspect',id=checkpoints[0]['id']);source=Path(cp['path']);original=source.read_bytes();rest=c.request('checkpoint.restore',id=cp['id'],confirm=True)
    import zipfile
    with zipfile.ZipFile(source) as z:expected=Image.open(io.BytesIO(z.read('mergedimage.png'))).convert('RGBA')
    preview=c.request('preview.canvas',width=128,height=128,filename='restored.png');actual=Image.open(preview['path']).convert('RGBA');assert all(hi==0 for lo,hi in ImageChops.difference(expected,actual).getextrema())
    resumed=c.request('checkpoint.resume',id=cp['id'],confirm=True)
    for _ in range(1500):
     terminal=c.request('job.status',id=resumed['new_job']['id'])
     if terminal['state'] in ('completed','failed'):break
     time.sleep(.02)
    assert terminal['state']=='completed';assert source.read_bytes()==original
   rows.append({'phase':phase,'ok':True,'event':e,'interrupted':state,'zero_auto_playback':True,'instrumentation':'temporary fixture gate; during_stroke after 10 completed native paintLine segments'})
   proc.terminate();proc.wait(timeout=15);proc=None;print(build,phase,'PASS',flush=True)
  Path('docs/acceptance-evidence/round3-crash-phases-'+build+'.json').write_text(json.dumps(rows,indent=2))
finally:
 if proc is not None and proc.poll() is None:proc.terminate();proc.wait(timeout=15)
 subprocess.run([sys.executable,'scripts/install_plugin.py','--apply','--replace'],check=True)
