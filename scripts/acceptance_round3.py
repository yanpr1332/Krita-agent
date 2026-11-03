"""Round3 live acceptance. Requires disposable test session JSON, never user artwork."""
import sys,json,time,hashlib,zipfile,traceback,uuid
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image,ImageChops
from krita_agent.client import Client
from krita_agent.revisions import propose,apply
from krita_agent.creative_plans import compile_scene
v=json.loads(Path('.cache/round2/current.json').read_text());out=Path(v['out']);c=Client(v['token'],47721);rows=[];seq=uuid.uuid4().hex[:8]
assert Path.cwd().resolve() in out.resolve().parents, 'Test output must stay inside repository cache'
def q(cmd,**p):
 with (out/"native-trace.jsonl").open("a",encoding="utf-8") as log:log.write(json.dumps({"command":cmd,"parameters":p,"time":time.time()})+"\n")
 return c.request(cmd,**p)
def case(name,fn):
 try:rows.append({'case':name,'ok':True,'result':fn()})
 except Exception as e:rows.append({'case':name,'ok':False,'error':str(e),'trace':traceback.format_exc()})
def deny(cmd,**p):
 try:q(cmd,**p)
 except Exception as e:
  if any(term in str(e).lower() for term in ("timed out","disconnected","winerror")):raise AssertionError("Transport failure is not a valid denial") from e
  return str(e)
 raise AssertionError('UNEXPECTED ACCEPT '+cmd)
def fresh(name):
 q('canvas.create',width=96,height=96,name=name)
 for n in q('layer.tree'):q('layer.delete',id=n['id'],confirm=True)
 return q('layer.create',name='Ink')
def shot():
 name='evidence/'+uuid.uuid4().hex+'.png';r=q('preview.canvas',width=96,height=96,filename=name);return Image.open(r['path']).convert('RGBA')
def eq(a,b):assert a.size==b.size and all(hi==0 for lo,hi in ImageChops.difference(a,b).getextrema())
def fill(color='#ff0000',**extra):return q('pixel.transaction.fill',name='Ink',x=10,y=10,width=20,height=20,color=color,confirm=True,**extra)
def pixels():
 fresh('Transactions');before=shot();r=fill();after=shot();assert after.getpixel((15,15))==(255,0,0,255)
 q('pixel.transaction.inspect',id=r['id']);q('pixel.transaction.undo',id=r['id'],confirm=True);eq(shot(),before);q('pixel.transaction.redo',id=r['id'],confirm=True);eq(shot(),after)
 m=json.loads((out/'.krita-agent-pixel-history'/(r['id']+'.json')).read_text());assert m['state']=='applied'
 stale=fill('#0000ff');deny('pixel.transaction.undo',id=r['id'],confirm=True)
 clear=q('pixel.transaction.clear',name='Ink',x=10,y=10,width=20,height=20,confirm=True);assert shot().getbbox() is None;q('pixel.transaction.undo',id=clear['id'],confirm=True)
 target=Image.new('RGBA',(96,96),(0,255,0,255));target.save(out/'patch.png');q('pixel.transaction.patch',name='Ink',x=0,y=0,width=8,height=8,path='patch.png',confirm=True);assert shot().getpixel((2,2))==(0,255,0,255)
 denials=[deny('pixel.transaction.fill',name='missing',x=0,y=0,width=1,height=1,color='#fff',confirm=True),deny('pixel.transaction.fill',name='Ink',x=0,y=0,width=1,height=1,color='invalid',confirm=True),deny('pixel.transaction.patch',name='Ink',x=0,y=0,width=1,height=1,path='../escape.png',confirm=True),deny('pixel.transaction.undo',id=r['id'])]
 q('layer.set',name='Ink',properties={'locked':True});denials.append(deny('pixel.transaction.clear',name='Ink',x=0,y=0,width=1,height=1,confirm=True));q('layer.set',name='Ink',properties={'locked':False});fresh('Other');denials.append(deny('pixel.transaction.undo',id=r['id'],confirm=True));return {'transaction':m['id'],'denials':denials}
def checkpoint():
 fresh('Checkpoint');fill();before=shot();start=time.perf_counter();r=q('checkpoint.create');elapsed=time.perf_counter()-start;p=Path(r['path']);digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==r['sha256']
 with zipfile.ZipFile(p) as z:assert 'maindoc.xml' in z.namelist() and z.testzip() is None
 q('checkpoint.inspect',id=r['id']);q('checkpoint.list');deny('checkpoint.restore',id=r['id']);rest=q('checkpoint.restore',id=r['id'],confirm=True);assert rest['restored']['path']!=r['path'];eq(shot(),before);assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 manifest=out/'.krita-agent-checkpoints'/(r['id']+'.json');orig=manifest.read_bytes();data=json.loads(orig);data['sha256']='0'*64;manifest.write_text(json.dumps(data));deny('checkpoint.inspect',id=r['id']);manifest.write_bytes(orig)
 missing=p.with_suffix('.missing');p.rename(missing)
 try:deny('checkpoint.inspect',id=r['id'])
 finally:missing.rename(p)
 deny('checkpoint.create',path=r['path']);deny('checkpoint.create',path='../outside.kra');return {'seconds':elapsed,'bytes':p.stat().st_size,'sha256':digest}
def masks():
 fresh('Masks');fill();q('selection.rectangle',x=10,y=10,width=10,height=20);r=q('mask.create',kind='transparency',name='Alpha',parent_name='Ink');q('selection.clear');a=shot();assert a.getpixel((15,15))[3]==255 and a.getpixel((25,15))[3]==0
 q('mask.inspect',id=r['id']);q('layer.set',name='Alpha',properties={'visible':False});assert shot().getpixel((25,15))[3]==255;q('layer.set',name='Alpha',properties={'visible':True});q('selection.rectangle',x=10,y=10,width=5,height=5);q('mask.create',kind='selection',name='Saved selection',parent_name='Ink');q('mask.selection.set',name='Saved selection');q('selection.clear');before=shot();name='masks-'+seq+'.kra';q('document.save',path=name);q('document.open',path=name);eq(shot(),before);assert any(n['type']=='transparencymask' for n in q('layer.tree'));return r
def filters():
 fresh('Filters');fill();available=q('filter.list')['filters'];assert 'invert' in available;before=shot();r=q('filter.mask.create',name='Invert',filter='invert',parent_name='Ink',confirm=True);after=shot();assert after.getpixel((15,15))[:3]==(0,255,255),after.getpixel((15,15))
 q('layer.set',name='Invert',properties={'visible':False});eq(shot(),before);q('layer.set',name='Invert',properties={'visible':True});q('filter.configure',name='Invert',properties={'dummy_acceptance':False},confirm=True);deny('filter.mask.create',name='Bad',filter='unknown-acceptance',parent_name='Ink',confirm=True)
 q('layer.set',name='Ink',properties={'locked':True});deny('filter.mask.create',name='Locked',filter='invert',parent_name='Ink',confirm=True);q('layer.set',name='Ink',properties={'locked':False});q('layer.delete',name='Invert',confirm=True);q('filter.layer.create',name='Invert layer',filter='invert',confirm=True);assert shot().getpixel((15,15))[:3]==(0,255,255)
 name='filters-'+seq+'.kra';before=shot();q('document.save',path=name);q('document.open',path=name);eq(shot(),before);return {'filter':'invert','mask':r}
def selection():
 results=[]
 for mode in ['replace','add','subtract','intersect','xor','feather','grow','shrink','border','invert','smooth']:
  fresh('Selection '+mode);q('pixel.fill',name='Ink',x=0,y=0,width=96,height=96,color='#ffffff',confirm=True)
  q('selection.rectangle',x=10,y=10,width=20,height=20)
  if mode in ['replace','add','subtract','intersect','xor']:q('selection.combine',mode=mode,x=20,y=10,width=20,height=20)
  else:q('selection.modify',mode=mode,radius=2)
  q('mask.create',kind='transparency',name='Coverage',parent_name='Ink');q('selection.clear');im=shot();alpha=im.getchannel('A');values=list(alpha.getdata());mass=sum(values)/255
  expected={'replace':400,'add':600,'subtract':200,'intersect':200,'xor':400,'invert':96*96-400}
  if mode in expected:assert abs(mass-expected[mode])<1,(mode,mass)
  if mode=='grow':assert mass>400
  if mode=='shrink':assert mass<400
  if mode=='feather':assert any(0<a<255 for a in values)
  if mode=='border':assert im.getpixel((20,20))[3]==0 and mass>0
  if mode=='smooth':assert mass>0
  results.append({'mode':mode,'alpha_mass':mass,'bounds':alpha.getbbox()})
 return results
def color():
 fresh('Color');fill();before=shot();info=q('color.info');profiles=q('color.profiles',model='RGBA',depth='U16');profile=profiles['profiles'][0];deny('color.convert',model='RGBA',depth='U16',profile=profile,confirm=True);r=q('checkpoint.create');q('color.convert',model='RGBA',depth='U16',profile=profile,checkpoint_id=r['id'],confirm=True);assert q('color.info')['depth']=='U16';deny('pixel.transaction.fill',name='Ink',x=0,y=0,width=1,height=1,color='#fff',confirm=True)
 reference_pixel=before.getpixel((15,15));converted_pixel=shot().getpixel((15,15));assert max(abs(a-b) for a,b in zip(reference_pixel,converted_pixel))<=4,(reference_pixel,converted_pixel)
 spaces=[]
 for model,depth in [('GRAYA','U8'),('RGBA','F32')]:
  ps=q('color.profiles',model=model,depth=depth)
  if not ps.get('profiles'):spaces.append({'model':model,'depth':depth,'unsupported':True});continue
  cp=q('checkpoint.create');spaces.append(q('color.convert',model=model,depth=depth,profile=ps['profiles'][0],checkpoint_id=cp['id'],confirm=True));deny('pixel.clear',name='Ink',x=0,y=0,width=1,height=1,confirm=True)
 return {'before':info,'conversions':spaces,'u16_profiles':profiles,'reference_pixel':reference_pixel,'converted_u16_pixel':converted_pixel}
def revision():
 fresh('Revision');fill();base=shot();base.save(out/'before.png');target=base.copy();target.paste((0,255,0,255),(40,40,48,48));target.save(out/'goal.png');node=next(n for n in q('layer.tree') if n['name']=='Ink');plan=propose(out/'before.png',out/'goal.png',node['id'],threshold=0);assert plan['rect']==[40,40,8,8]
 try:apply(c,plan,confirm=False)
 except Exception:pass
 else:raise AssertionError('missing confirmation accepted')
 result=apply(c,plan,confirm=True);assert result['terminal']['state']=='completed',result;eq(shot(),target);tree=q('layer.tree');assert any(n['id']==node['id'] and not n['visible'] for n in tree);assert result['goal_rgba_match'];original_path=q('preview.layer',id=node['id'],width=96,height=96,filename='evidence/original-'+seq+'.png')['path'];eq(Image.open(original_path).convert('RGBA'),base);q('document.save',path='revisions/reopened-'+seq+'.kra');q('document.open',path='revisions/reopened-'+seq+'.kra');eq(shot(),target);return result
def revision_guards():
 fresh('Revision guards');fill();base=shot();base.save(out/'guard-before.png');goal=base.copy();goal.putpixel((50,50),(0,255,0,255));goal.save(out/'guard-goal.png');node=next(n for n in q('layer.tree') if n['name']=='Ink');plan=propose(out/'guard-before.png',out/'guard-goal.png',node['id'],threshold=0)
 def refused(p=plan,confirm=True):
  try:apply(c,p,confirm=confirm)
  except Exception as e:
   if any(term in str(e).lower() for term in ("timed out","disconnected","winerror")):raise AssertionError("Transport failure is not a valid denial") from e
   return str(e)
  raise AssertionError('revision incorrectly accepted')
 errors=[refused(confirm=False)]
 original=(out/'guard-goal.png').read_bytes();(out/'guard-goal.png').write_bytes(original+b'changed');errors.append(refused());(out/'guard-goal.png').write_bytes(original)
 q('layer.create',name='Other');errors.append(refused());q('layer.delete',name='Other',confirm=True)
 q('layer.set',name='Ink',properties={'blending_mode':'multiply'});errors.append(refused());q('layer.set',name='Ink',properties={'blending_mode':'normal'})
 for properties,restore in [({'opacity':0.5},{'opacity':1.0}),({'locked':True},{'locked':False}),({'visible':False},{'visible':True})]:
  q('layer.set',name='Ink',properties=properties);errors.append(refused());q('layer.set',name='Ink',properties=restore)
 fill('#0000ff');errors.append(refused());q('pixel.fill',name='Ink',x=10,y=10,width=20,height=20,color='#ff0000',confirm=True)
 changed=dict(plan,rect=[0,0,1000,1000]);errors.append(refused(changed));changed=dict(plan,size=[97,96]);errors.append(refused(changed))
 j=q('job.submit',steps=[{'command':'document.info','parameters':{}}]*400);q('job.pause',id=j['id']);errors.append(refused());q('job.cancel',id=j['id'])
 for _ in range(100):
  if q('job.status',id=j['id'])['state']=='cancelled':break
  time.sleep(.01)
 ps=q('color.profiles',model='RGBA',depth='U16');cp=q('checkpoint.create');q('color.convert',model='RGBA',depth='U16',profile=ps['profiles'][0],checkpoint_id=cp['id'],confirm=True);errors.append(refused())
 before=q('layer.tree');unchanged=propose(out/'guard-before.png',out/'guard-before.png',node['id']);assert apply(c,unchanged,confirm=True)['mutated'] is False;assert q('layer.tree')==before
 return errors
def malicious_storage():
 import base64,zlib,subprocess,os
 fresh('Storage safety');r=fill();path=out/'.krita-agent-pixel-history'/(r['id']+'.json');original=path.read_bytes();record=json.loads(original)
 altered=dict(record);altered['before']=base64.b64encode(zlib.compress(b'X'*1600)).decode();path.write_text(json.dumps(altered));deny('pixel.transaction.undo',id=r['id'],confirm=True);path.write_bytes(original)
 altered=dict(record,rect=[0,0,1000,1000]);path.write_text(json.dumps(altered));deny('pixel.transaction.inspect',id=r['id']);path.write_bytes(original)
 prepared=dict(record,state='prepared');path.write_text(json.dumps(prepared));assert q('pixel.transaction.reconcile',id=r['id'],confirm=True)['state']=='applied';q('pixel.transaction.undo',id=r['id'],confirm=True);path.write_text(json.dumps(prepared));assert q('pixel.transaction.reconcile',id=r['id'],confirm=True)['state']=='undone';q('pixel.transaction.redo',id=r['id'],confirm=True)
 q('selection.rectangle',x=10,y=10,width=20,height=20);q('selection.copy');clip=q('clipboard.save',name='safe-'+seq+'.kclip');clipfile=Path(clip['path']);original_clip=clipfile.read_bytes();cliprecord=json.loads(original_clip)
 for change in [{'schema':999},{'width':16384,'height':16384},{'sha256':'0'*64},{'pixels_zlib_b64':base64.b64encode(zlib.compress(b'X'*100000)).decode()}]:
  clipfile.write_text(json.dumps(dict(cliprecord,**change)));deny('clipboard.load',name=clipfile.name)
 clipfile.write_bytes(original_clip);q('selection.clear');backup_cp=q('checkpoint.create')
 escaped=out.parent/('escape-'+seq);escaped.mkdir(exist_ok=True);tested=[]
 for directory,cmd,params in [('.krita-agent-checkpoints','checkpoint.list',{}),('.krita-agent-pixel-history','pixel.transaction.inspect',{'id':r['id']}),('clips','clipboard.inspect',{'name':clipfile.name}),('recovered','checkpoint.restore',{'id':backup_cp['id'],'confirm':True})]:
  link=out/directory;link.mkdir(exist_ok=True);backup=out/(directory+'-real');link.rename(backup)
  try:
   subprocess.run(['powershell','-NoProfile','-Command',"New-Item -ItemType Junction -Path '"+str(link)+"' -Target '"+str(escaped)+"'"],check=True,capture_output=True)
   assert link.is_junction();tested.append(deny(cmd,**params));assert not list(escaped.iterdir())
  finally:
   if link.is_junction():os.rmdir(link)
   backup.rename(link)
 return {'tampered_history_refused':True,'malicious_clips_refused':True,'junction_denials':tested}
def filter_configuration():
 fresh('Filter configuration');fill();q('filter.mask.create',name='Desaturate',filter='desaturate',parent_name='Ink',confirm=True);a=shot().getpixel((15,15));q('filter.configure',name='Desaturate',properties={'type':5},confirm=True);b=shot().getpixel((15,15));assert a!=b and b[:3]==(255,255,255),(a,b)
 q('layer.set',name='Desaturate',properties={'locked':True});deny('filter.configure',name='Desaturate',properties={'type':0},confirm=True);return {'default_pixel':a,'max_pixel':b}
def revision_failure_recovery():
 records=[]
 for phase in ['after_duplicate','after_patch','after_hide']:
  fresh('Revision failure '+phase);fill();before=shot();cp=q('checkpoint.create');raw=Path(cp['path']).read_bytes();target=before.copy();target.putpixel((40,40),(0,255,0,255));target.save(out/'failure-target.png')
  steps=[{'command':'layer.duplicate','parameters':{'name':'Ink','new_name':'Partial revision'}}]
  if phase!='after_duplicate':steps.append({'command':'pixel.transaction.patch','parameters':{'name':'Partial revision','x':40,'y':40,'width':1,'height':1,'path':'failure-target.png','confirm':True}})
  if phase=='after_hide':steps.append({'command':'layer.set','parameters':{'name':'Ink','properties':{'visible':False}}})
  steps.append({'command':'layer.inspect','parameters':{'name':'Deliberate missing failure'}})
  j=q('job.submit',steps=steps)
  for _ in range(100):
   state=q('job.status',id=j['id'])
   if state['state']=='failed':break
   time.sleep(.02)
  assert state['state']=='failed';q('checkpoint.restore',id=cp['id'],confirm=True);eq(shot(),before);assert Path(cp['path']).read_bytes()==raw;records.append({'phase':phase,'failed_job':state,'restored_pixels_equal':True})
 return records
case('runtime',lambda:q('capabilities'));case('pixel_transactions',pixels);case('checkpoint_integrity_restore',checkpoint);case('masks_pixels_kra',masks);case('filters_pixels_kra',filters);case('selection_native',selection);case('color_conversion',color);case('brush_metadata',lambda:q('brush.profile',name='b) Basic-5 Size'));case('reference_revision',revision);case('revision_safety_guards',revision_guards);case('malicious_storage',malicious_storage);case('filter_configuration_pixels',filter_configuration);case('revision_failure_recovery',revision_failure_recovery)
f=Path('docs/acceptance-evidence')/('round3-native-'+v['build']+'.json');f.write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps([r for r in rows if not r['ok']],indent=2));print('TOTAL',len(rows),'FAILED',sum(not r['ok'] for r in rows))
