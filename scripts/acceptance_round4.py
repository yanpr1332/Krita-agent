"""Round4 real-build acceptance on disposable 4096px test documents."""
import sys,json,time,uuid,hashlib,traceback,zipfile,io,os
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image,ImageChops,ImageStat
from krita_agent.client import Client
from krita_agent import document_graph as dg,layered_revision as lr,scheduler,brush_profiles as bp,pyramid,projects,scene_v2,feedback_v2
v=json.loads(Path('.cache/round2/current.json').read_text());out=Path(v['out']);c=Client(v['token'],47721,timeout=60);rows=[];tag=uuid.uuid4().hex[:8]
def q(cmd,**p):return c.request(cmd,**p)
def case(name,fn):
 try:rows.append({'case':name,'ok':True,'result':fn()})
 except Exception as e:rows.append({'case':name,'ok':False,'error':str(e),'trace':traceback.format_exc()});print(name,str(e),flush=True)
 Path('docs/acceptance-evidence/round4-native-'+v['build']+'.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
def equal(a,b):assert a.size==b.size and all(hi==0 for lo,hi in ImageChops.difference(a,b).getextrema())
def export():
 r=q('document.export',path='acceptance/'+uuid.uuid4().hex+'.png');return Path(r['path'])
def wait(j):
 for _ in range(5000):
  state=q('job.status',id=j['id'])
  if state['state'] in ('completed','failed','cancelled'):assert state['state']=='completed',state;return state
  time.sleep(.04)
 raise AssertionError('deadline')
def fixture():
 q('canvas.create',width=4096,height=4096,name='Round4 integrated')
 for i in range(8):q('layer.create',name='Paint'+str(i))
 q('layer.set',name='Paint1',properties={'opacity':.5,'blending_mode':'multiply'});q('layer.set',name='Paint2',properties={'visible':False})
 group=q('layer.group',name='Group');q('layer.group',name='Nested',parent_id=group['id']);q('selection.rectangle',x=0,y=0,width=512,height=512);q('mask.create',kind='transparency',name='Alpha',parent_name='Paint3');q('selection.clear');assert q('selection.info')['selected'] is False;q('filter.mask.create',name='Invert',filter='invert',parent_name='Paint4',confirm=True)
 Image.new('RGBA',(8,8),(20,40,60,255)).save(out/'reference.png');q('reference.import',path='reference.png',name='Reference')
 g=q('document.graph');assert len({n['id'] for n in g['nodes']})==len(g['nodes']);assert sum(n['type']=='paintlayer' for n in g['nodes'])>=8;assert {'grouplayer','transparencymask','filtermask','filelayer'}<=set(n['type'] for n in g['nodes'])
 for n in g['nodes']:assert n['path'][-1]==n['sibling_index'] and n['color_model'] and len(n['bounds'])==4
 old=g;q('layer.rename',name='Paint7',new_name='Final Paint');q('layer.set',name='Final Paint',properties={'opacity':.75});assert dg.changed_nodes(old,q('document.graph'))

 for layer,preset,y in [('Paint0','b) Basic-5 Size',100),('Paint1','b) Basic-2 Opacity',200),('Paint3','c) Pencil-2',300)]:
  q('layer.select',name=layer);q('brush.configure',preset=preset,size=16,color='#305070',pressure_enabled=True);q('draw.line',x1=100,y1=y,x2=300,y2=y,pressure1=.2,pressure2=.9)
 q('document.save',path='original-'+tag+'.kra');p=export();return {'graph':q('document.graph'),'before':str(p),'nodes':len(g['nodes'])}
def calibration():
 result=[];directory=out/'brush-profiles';build=q('status')['krita_version']
 for preset,category in [('b) Basic-5 Size','ink'),('b) Basic-2 Opacity','paint'),('c) Pencil-2','sketch')]:
  task=bp.calibration_task(preset);s=wait(c.submit(task['steps']));p=Path(s['last_result']['path']);im=Image.open(p).convert('RGB');measures=[]
  for y in [65,155,245,335]:
   crop=im.crop((100,y-40,520,y+40));delta=ImageChops.difference(crop,Image.new('RGB',crop.size,'white'));mask=delta.convert('L').point(lambda x:255 if x>5 else 0);bounds=mask.getbbox();measures.append({'bbox':bounds,'difference':sum(ImageStat.Stat(delta).mean)})
  assert measures[-1]['difference']>measures[0]['difference'],measures
  widths=[m['bbox'][3]-m['bbox'][1] if m['bbox'] else 0 for m in measures];pressure_size=widths[-1]>widths[0]+2;pressure_opacity=not pressure_size and measures[-1]['difference']>measures[0]['difference']*1.2
  profile=bp.record_profile(directory,{'preset':preset,'build':build,'category':category,'pressure_size':pressure_size,'pressure_opacity':pressure_opacity,'confidence':.95},p)
  assert bp.choose(directory,build,category)['preset']==preset
  result.append({'preset':preset,'profile':profile,'measurements':measures})
 for b,confidence in [('wrong-build',.8),(build,.99)]:
  try:bp.choose(directory,b,'ink',confidence)
  except ValueError:pass
  else:raise AssertionError('mismatch accepted')
 return result
case('runtime',lambda:q('capabilities'));case('brush_calibration',calibration);case('integrated_fixture_graph',fixture)
if not rows[-1]['ok']:sys.exit(1)
original=rows[-1]['result'];before=Path(original['before']);g=original['graph'];graphfile=out/'graph.json';dg.save(g,graphfile)
def overlay():
 results=[]
 for i in range(2):
  base=before if i==0 else export();graph=q('document.graph');gf=out/f'graph-{i}.json';dg.save(graph,gf);im=Image.open(base).convert('RGBA');goal=im.copy();goal.paste((40,180,60,255),(600+i*600,600,632+i*600,632));target=out/f'goal-{i}.png';goal.save(target);plan=lr.create_plan(base,target,gf,out/f'plan-{i}.json')
  try:lr.apply(c,plan,confirm=False)
  except Exception:pass
  else:raise AssertionError('confirmation absent accepted')
  bad=json.loads(json.dumps(plan));bad['changes'][0]['rect'][0]+=1
  try:lr.apply(c,bad,confirm=True)
  except Exception:pass
  else:raise AssertionError('mutated plan accepted')
  started=time.perf_counter();r=lr.apply(c,plan,confirm=True);assert r['state']=='completed' and r['changed_tile_pixel_match'],r
  after=export();equal(Image.open(after).convert('RGBA'),goal)
  current=q('document.graph');orig=[n for n in current['nodes'] if n['id'] in {x['id'] for x in graph['nodes']}]
  for old,n in zip(graph['nodes'],orig):
   assert {k:v for k,v in old.items() if k not in ('path','sibling_index')}=={k:v for k,v in n.items() if k not in ('path','sibling_index')},(old,n)
  assert [n['id'] for n in orig]==[n['id'] for n in graph['nodes']]
  results.append({'revision':i,'seconds':time.perf_counter()-started,'result':r})
  q('document.open',path='layered-revisions/'+plan['id']+'.kra');equal(Image.open(export()).convert('RGBA'),goal)
 return results
case('two_approved_layered_revisions',overlay)
def tiled():
 base=Image.open(export()).convert('RGBA');stats=[]
 for y in range(0,4096,512):
  for x in range(0,4096,512):
   r=q('preview.tile',x=x,y=y,width=512,height=512);im=Image.open(r['path']).convert('RGBA');equal(im,base.crop((x,y,x+512,y+512)));assert r['origin']==[x,y];assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'];stats.append({'origin':[x,y],'sha256':r['sha256']})
 file=export();p=pyramid.build(file,out/('pyramid-'+tag));assert p['tile_count']==85,p;return {'tiles':stats,'pyramid':p}
case('4096_tiles_pyramid',tiled)
def longjob():
 q('selection.clear');assert q('selection.info')['selected'] is False;q('layer.create',name='1200 Strokes');q('brush.configure',preset='b) Basic-5 Size',size=3,color='#204080',opacity=1.0,pressure_enabled=True)
 steps=[{'command':'draw.line','parameters':{'x1':20+(i%100)*4,'y1':1500+(i//100)*4,'x2':22+(i%100)*4,'y2':1500+(i//100)*4}} for i in range(1200)]
 start=time.perf_counter();r=scheduler.run(c,{'steps':steps},out/'ledgers',batch_steps=119,poll_interval=.05);assert r['state']=='completed',r;ledger=scheduler.inspect_ledger(r['ledger']);assert all(x['checkpoint']['sha256'] for x in ledger['completed']);assert len({x['job_id'] for x in ledger['completed']})==len(ledger['completed'])
 with zipfile.ZipFile(ledger['completed'][-1]['checkpoint']['path']) as archive:rendered=Image.open(io.BytesIO(archive.read('mergedimage.png'))).convert('RGBA')
 # The 3px brush is antialiased. Check a near-opaque sample in each
 # non-overlapping stroke footprint and a white separator row.
 for i in range(1200):
  x,y=21+(i%100)*4,1500+(i//100)*4
  samples=[rendered.getpixel((x,row)) for row in (y-1,y)]
  assert any(pixel[3]==255 and max(abs(a-b) for a,b in zip(pixel[:3],(32,64,128)))<=8 for pixel in samples), (i,samples)
  assert rendered.getpixel((x,y+1))==(255,255,255,255), i
 return {'result':r,'seconds':time.perf_counter()-start,'ledger':ledger}
case('1200_native_steps_checkpoints',longjob)
print('TOTAL',len(rows),'FAILED',sum(not r['ok'] for r in rows),flush=True)
