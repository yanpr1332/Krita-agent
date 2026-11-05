"""Additional real-build Round4 rejection, ScenePlan and project assertions."""
from pathlib import Path
import json,uuid,sys,time,hashlib,zipfile,copy
ns={};exec(compile(Path('scripts/acceptance_round4.py').read_text(encoding='utf-8').split("case('runtime'")[0],'<round4 helpers>','exec'),ns)
ns['_evidence_prefix']='round4-supplement'
q,c,out,case=ns['q'],ns['c'],ns['out'],ns['case'];Image=ns['Image'];lr=ns['lr'];dg=ns['dg'];equal=ns['equal'];export=ns['export'];tag=ns['tag'];rows=ns['rows']
def case(name,fn):
 try:rows.append({'case':name,'ok':True,'result':fn()})
 except Exception as e:
  import traceback
  rows.append({'case':name,'ok':False,'error':str(e),'trace':traceback.format_exc()})
 Path('docs/acceptance-evidence/round4-supplement-'+ns['v']['build']+'.json').write_text(json.dumps(rows,indent=2))

def refuse(fn):
 try:fn()
 except Exception as e:
  assert 'timed out' not in str(e).lower();return str(e)
 raise AssertionError('unsafe input accepted')
def guards():
 q('layer.set',name='Paint0',properties={'locked':False});q('pixel.fill',name='Paint0',x=0,y=0,width=1,height=1,color='#ffffff',confirm=True);q('pixel.fill',name='Paint0',x=4095,y=4095,width=1,height=1,color='#ffffff',confirm=True);base=export();graph=q('document.graph');gf=out/('guards-'+tag+'.json');dg.save(graph,gf);im=Image.open(base).convert('RGBA');goal=im.copy();goal.paste((0,180,0,255),(700,700,708,708));target=out/('guards-goal-'+tag+'.png');goal.save(target);p=lr.create_plan(base,target,gf,out/('guards-plan-'+tag+'.json'));errors=[]
 destination = out / "layered-revisions" / (p["id"] + ".kra")
 destination.parent.mkdir(exist_ok=True)
 destination.write_bytes(b"existing revision")
 try:
  error = refuse(lambda: lr.apply(c, p, confirm=True))
  assert "already exists" in error and q("document.graph") == graph
  assert destination.read_bytes() == b"existing revision"
  errors.append(error)
 finally:
  destination.unlink()
 for key in ['source','target']:
  file=Path(p[key]['path']);old=file.read_bytes();file.write_bytes(old+b'changed');errors.append(refuse(lambda:lr.apply(c,p,confirm=True)));file.write_bytes(old)
 old=q('document.graph');q('layer.set',name='Paint1',properties={'opacity':.3});errors.append(refuse(lambda:lr.apply(c,p,confirm=True)));q('layer.set',name='Paint1',properties={'opacity':.5})
 q('pixel.fill',name='Paint0',x=701,y=701,width=1,height=1,color='#000000',confirm=True);errors.append(refuse(lambda:lr.apply(c,p,confirm=True)));q('pixel.fill',name='Paint0',x=701,y=701,width=1,height=1,color='#ffffff',confirm=True)
 for change in [{'id':'../../unsafe'},{'changes':p['changes']*129}]:errors.append(refuse(lambda:lr.apply(c,dict(p,**change),confirm=True)))
 transparent=goal.copy();transparent.putpixel((700,700),(0,0,0,0));transparent.save(out/'transparent-goal.png');errors.append(refuse(lambda:lr.plan_overlay(base,out/'transparent-goal.png',graph)))
 huge=im.copy();huge.paste((20,30,40,255),(0,0,1024,1024));huge.save(out/'huge-goal.png');errors.append(refuse(lambda:lr.plan_overlay(base,out/'huge-goal.png',graph,tile_size=1024)))
 return errors

def scenes_projects():
 roles=['background','lineart','base_color','shadow','highlight','texture','foreground','effects'];scene={'schema':'krita-agent-scene/2','document':{'width':512,'height':512,'name':'Scene v2 acceptance'},'layers':[{'name':'Role-'+role,'role':role,'brush':{'preset':'b) Basic-5 Size','size':8,'color':'#204060'},'elements':[{'kind':'rectangle','rect':[20+i*20,20+i*20,40,40]}],'preview':i==7} for i,role in enumerate(roles)]}
 plan=ns['scene_v2'].compile_plan(scene);assert plan['sha256']==ns['scene_v2'].compile_plan(scene)['sha256'];state=ns['wait'](c.submit(plan['steps']));assert len(q('layer.tree'))>=8;file=export();assert len(Image.open(file).convert('RGB').getcolors(512*512))>1
 bad=copy.deepcopy(scene);bad['layers'][0]['role']='shell';refuse(lambda:ns['scene_v2'].load_ai_candidate(bad))
 project=out/'project';ns['projects'].init(project,'Acceptance');q('document.save',path='project/art.kra');sf=project/'scene.json';sf.write_text(json.dumps(scene));ns['projects'].add(project,project/'art.kra','kra');ns['projects'].add(project,sf,'scene_plan');assert ns['projects'].audit(project)['all_valid'];sf.write_text('tampered');assert not ns['projects'].audit(project)['all_valid'];sf.write_text(json.dumps(scene));assert 'token' not in (project/'krita-agent-project.json').read_text().lower()
 return {'scene_sha256':plan['sha256'],'job':state,'project_audit':ns['projects'].audit(project)}
def long_strokes():
 from krita_agent.long_strokes import as_steps,segment_long_stroke
 import math
 q('canvas.create',width=1024,height=512,name='Stroke comparison');q('layer.create',name='Strokes');q('brush.configure',preset='b) Basic-5 Size',size=8,color='#203040')
 points=[{'x':10+i*1000/4096,'y':200+40*math.sin(i/100),'pressure':.6,'time_ms':i} for i in range(4097)]
 refuse(lambda:segment_long_stroke(points));steps,report=as_steps(points,64,'auto',True);assert len(steps)==66;assert all(a['parameters']['points'][-1]==b['parameters']['points'][0] for a,b in zip(steps,steps[1:]));start=time.perf_counter();ns['wait'](c.submit(steps));segmented=time.perf_counter()-start
 segmented_pixels=Image.open(export()).convert('RGBA');q('history.undo');after_one_undo=Image.open(export()).convert('RGBA');assert len(after_one_undo.convert('RGB').getcolors(1024*512))>1;q('history.redo');equal(Image.open(export()).convert('RGBA'),segmented_pixels)
 capabilities=q('capabilities')['symbols'];single=None
 if capabilities['Node.paintPolylineStroke']:
  q('layer.set',name='Strokes',properties={'visible':False});q('layer.create',name='Continuous');blank=Image.open(export()).convert('RGBA');start=time.perf_counter();q('draw.stroke',points=points[:2048],mode='continuous');q('document.export',path='stroke-continuous.png');single=time.perf_counter()-start;painted=Image.open(out/'stroke-continuous.png').convert('RGBA');q('history.undo');equal(Image.open(export()).convert('RGBA'),blank);q('history.redo');equal(Image.open(export()).convert('RGBA'),painted)
 return {'samples':4097,'segments':66,'seconds':segmented,'continuous_2048_seconds':single,'continuous_supported':capabilities['Node.paintPolylineStroke']}
def graph_payloads():
 import xml.etree.ElementTree as ET
 def payloads(path):
  with zipfile.ZipFile(path) as z:
   doc=ET.fromstring(z.read('maindoc.xml'));image=next(x for x in doc.iter() if x.tag.endswith('IMAGE'));result={}
   for node in doc.iter():
    if not node.get('uuid') or not node.get('filename'):continue
    prefix=image.get('name')+'/layers/'+node.get('filename')
    data={name[len(prefix):]:hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist() if name==prefix or name.startswith(prefix+'.')}
    result[node.get('uuid')]=data
   return result
 native=json.loads(Path('docs/acceptance-evidence/round4-native-'+ns['v']['build']+'.json').read_text());revisions=next(x['result'] for x in native if x['case']=='two_approved_layered_revisions');counts=[]
 for rev in revisions:
  old=payloads(rev['result']['checkpoint']['path']);new=payloads(rev['result']['job']['last_result']['path']);assert all(new.get(k)==value for k,value in old.items());counts.append(len(old))
 before=q('document.graph');name='graph-reopen-'+tag+'.kra';q('document.save',path=name);q('document.open',path=name);after=q('document.graph');binding=dg.rebind(before,after);assert all(x['new_id'] is None for x in binding['mapping'] if x['status']!='candidate');assert any(x['status']=='candidate' for x in binding['mapping'])
 return {'byte_equal_original_node_counts':counts,'rebind_nodes':len(binding['mapping'])}
def guarded_overlay():return {'graph_and_bytes':graph_payloads(),'denials':guards()}
case('overlay_stale_and_budget_rejections',guarded_overlay);case('long_stroke_execution',long_strokes);case('scene_v2_project_audit',scenes_projects)
Path('docs/acceptance-evidence/round4-supplement-'+ns['v']['build']+'.json').write_text(json.dumps(rows,indent=2));print([(r['case'],r['ok'],r.get('error')) for r in rows])
