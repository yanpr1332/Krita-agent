"""Serial final Round4 guards on disposable recovered integrated artwork."""
import sys,json,uuid,copy,socket,shutil,time
from pathlib import Path
sys.path[:0]=['src','.cache/test-deps']
from PIL import Image
from krita_agent.client import Client
from krita_agent import document_graph as dg,layered_revision as lr
v=json.loads(Path('.cache/round2/current.json').read_text());out=Path(v['out']);c=Client(v['token'],47721,timeout=60);rows=[];tag=uuid.uuid4().hex
q=c.request
def refused(fn):
 try:fn()
 except Exception as e:
  assert 'timed out' not in str(e).lower();return str(e)
 raise AssertionError('unsafe operation accepted')
g=q('document.graph');assert g['document']['width']==4096
before=Path(q('document.export',path='checks/'+tag+'.png')['path']);goal=Image.open(before).convert('RGBA');goal.paste((80,180,30,255),(3200,3200,3208,3208));target=out/('goal-check-'+tag+'.png');goal.save(target);gf=out/('graph-check-'+tag+'.json');dg.save(g,gf);plan=lr.create_plan(before,target,gf,out/('plan-check-'+tag+'.json'));node=next(n for n in g['nodes'] if n['name']=='Paint0');old_index=node['sibling_index'];q('layer.reorder',id=node['id'],index=0 if old_index else 1);error=refused(lambda:lr.apply(c,plan,confirm=True));assert 'tree changed' in error.lower();q('layer.reorder',id=node['id'],index=old_index)
rows.append({'case':'independent_layer_order_staleness','ok':True,'error':error})
outside=out.parent/('outside-goal-'+tag+'.png');shutil.copyfile(target,outside);bad=lr.create_plan(before,outside,gf,out/('outside-plan-'+tag+'.json'));error=refused(lambda:lr.apply(c,bad,confirm=True));assert 'authorized input' in error;rows.append({'case':'unauthorized_goal_path','ok':True,'error':error})
wrong=copy.deepcopy(g);wrong['document']['width']+=1;refused(lambda:lr.plan_overlay(before,target,wrong));wrong=copy.deepcopy(g);wrong['document']['depth']='U16';refused(lambda:lr.plan_overlay(before,target,wrong));same=lr.create_plan(before,before,gf,out/('same-plan-'+tag+'.json'));assert lr.apply(c,same,confirm=True)['mutated'] is False
backup=q('checkpoint.create');profiles=q('color.profiles',model='RGBA',depth='U16');q('color.convert',model='RGBA',depth='U16',profile=profiles['profiles'][0],checkpoint_id=backup['id'],confirm=True);refused(lambda:q('revision.overlay.begin',checkpoint_id=backup['id'],confirm=True));refused(lambda:q('pixel.fill',name='Paint0',x=0,y=0,width=1,height=1,color='#ffffff',confirm=True));q('checkpoint.restore',id=backup['id'],confirm=True);rows.append({'case':'image_graph_depth_and_no_change_guards','ok':True})
refused(lambda:c.request('status',padding='x'*(1024*1024)));refused(lambda:c.submit([{'command':'document.info','parameters':{}}]*401))
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
try:Client('invalid-endpoint-test',port,timeout=.3).request('status')
except Exception:pass
else:raise AssertionError('expected unavailable endpoint')
assert q('status')['connected'];rows.append({'case':'wire_budget_wrong_port_reconnect','ok':True})
if v['build']=='stable':
 q('canvas.create',width=32,height=32,name='Graph cap fixture')
 for i in range(512):q('layer.create',name='Limit-'+str(i))
 error=refused(lambda:q('document.graph'));assert '512' in error;rows.append({'case':'native_graph_512_node_cap','ok':True,'error':error})
Path('docs/acceptance-evidence/round4-final-guards-'+v['build']+'.json').write_text(json.dumps(rows,indent=2));print([(r['case'],r['ok']) for r in rows])
