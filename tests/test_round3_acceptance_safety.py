"""Additional Round3 acceptance safety and failure-injection regressions."""
import ast,json,base64,zlib,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import pytest
from krita_agent.revisions import apply,propose
from krita_agent.protocol import TaskError
from krita_agent.upstream3 import registry_record,registry_list

def functions(file,namespace):
 path=Path(__file__).parents[1]/'plugin/krita_agent_bridge'/file
 tree=ast.parse(path.read_text(encoding='utf-8'))
 definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
 exec(compile(ast.fix_missing_locations(ast.Module(body=definitions,type_ignores=[])),str(path),'exec'),namespace)
 return namespace

def test_no_change_revision_does_not_contact_bridge():
 client=Mock();assert apply(client,{'status':'no_change'},confirm=True)['mutated'] is False;client.request.assert_not_called()

@pytest.mark.parametrize('rect',[[-1,0,1,1],[0,0,800,800],[8,8,4,4]])
def test_invalid_revision_roi_refused_before_contact(rect):
 client=Mock()
 with pytest.raises(TaskError):apply(client,{'schema':'krita-agent-revision/1','status':'patch_required','id':'a'*32,'rect':rect,'size':[10,10]},confirm=True)
 client.request.assert_not_called()

def test_clipboard_rejects_bomb_trailing_and_truncated_streams():
 ns=functions('clipboard_store.py',dict(base64=base64,zlib=zlib));decode=ns['_decode']
 for packed in [zlib.compress(b'a'*10000),zlib.compress(b'abcd')+b'tail',zlib.compress(b'abcd')[:-1]]:
  with pytest.raises(ValueError):decode(base64.b64encode(packed).decode(),4)

def test_registry_atomic_failure_preserves_existing(tmp_path):
 evidence=tmp_path/'e.txt';evidence.write_text('actual test evidence');store=tmp_path/'registry.json'
 registry_record(store,'A','a','source_seen',evidence);before=store.read_bytes()
 with patch.object(Path,'replace',side_effect=OSError('injected disk failure')):
  with pytest.raises(OSError):registry_record(store,'B','b','present_in_build',evidence)
 assert store.read_bytes()==before and len(registry_list(store)['entries'])==1

def test_checkpoint_boundary_cannot_point_to_non_checkpoint():
 ns=functions('checkpoints.py',{'_fingerprint':lambda x:'hash'})
 ns['_fingerprint']=lambda x:'hash'
 bridge=SimpleNamespace(jobs={'job':{'state':'interrupted','steps':[{'command':'draw.line'},{'command':'document.info'}]}})
 with pytest.raises(ValueError,match='boundary'):ns['_steps'](bridge,{'job_id':'job','steps_sha256':'hash','after_step':1})

def test_pixel_history_rejects_tampered_payload_before_any_native_write(tmp_path):
 import uuid
 key=uuid.uuid4().hex;path=tmp_path/(key+'.json');raw=bytes(4)
 record={'schema':1,'id':key,'document':['Test','',16,16,'RGBA','U8'],'rect':[0,0,1,1],'before':base64.b64encode(zlib.compress(b'bad!')).decode(),'after':base64.b64encode(zlib.compress(raw)).decode(),'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(raw).hexdigest()}
 path.write_text(json.dumps(record))
 ns=functions('pixel_history.py',dict(uuid=uuid,word=lambda x,*a:x,json=json,base64=base64,zlib=zlib,hashlib=hashlib,MAX_PIXELS=500000));ns['_storage']=lambda bridge:tmp_path
 with pytest.raises(ValueError,match='integrity'):ns['_read'](None,key)
@pytest.mark.parametrize('state,changed,command', [('running',False,'document.info'),('interrupted',True,'document.info'),('interrupted',False,'canvas.create')])
def test_checkpoint_refuses_live_changed_or_forbidden_suffix(state,changed,command):
 ns=functions('checkpoints.py',{'BASIC_RESUME_DENY':{'canvas.create'}});ns['_fingerprint']=lambda x:'changed' if changed else 'hash'
 bridge=SimpleNamespace(jobs={'job':{'state':state,'steps':[{'command':'checkpoint.create'},{'command':command}]}})
 with pytest.raises(ValueError):ns['_steps'](bridge,{'job_id':'job','steps_sha256':'hash','after_step':1})

def test_atomic_replace_retries_only_transient_permission_errors():
 ns=functions('atomic_io.py',{'time':Mock()});source=Mock();source.replace.side_effect=[PermissionError('locked'),PermissionError('locked'),'done']
 assert ns['atomic_replace'](source,'target')=='done';assert source.replace.call_count==3;assert ns['time'].sleep.call_count==2

def test_atomic_replace_has_bounded_failure():
 ns=functions('atomic_io.py',{'time':Mock()});source=Mock();source.replace.side_effect=PermissionError('permanent')
 with pytest.raises(PermissionError):ns['atomic_replace'](source,'target')
 assert source.replace.call_count==8 and ns['time'].sleep.call_count==7
