"""Native IPC regression, only against the disposable authenticated session."""
import sys,json,socket,uuid,subprocess
from pathlib import Path
sys.path.insert(0,'src')
from krita_agent.client import Client,BridgeError
v=json.loads(Path('.cache/round2/current.json').read_text());c=Client(v['token'],47721);results=[]
for client,cmd in [(Client('invalid-round3-test-token',47721),'status'),(c,'exec')]:
 try:client.request(cmd)
 except BridgeError as e:results.append({'case':'auth' if cmd=='status' else 'allowlist','ok':True,'error':str(e)})
 else:raise AssertionError('unexpected permission')
c.request('canvas.create',width=64,height=64,name='IPC regression')
key=uuid.uuid4().hex
payload={'id':key,'token':v['token'],'command':'layer.create','parameters':{'name':'Deduplicated'}}
def raw(payload):
 with socket.create_connection(('127.0.0.1',47721),timeout=5) as s:
  s.sendall((json.dumps(payload)+'\n').encode());data=b''
  while b'\n' not in data:data+=s.recv(4096)
  return json.loads(data.split(b'\n')[0])
a,b=raw(payload),raw(payload);assert a==b and a['ok'];assert sum(n['name']=='Deduplicated' for n in c.request('layer.tree'))==1;results.append({'case':'duplicate_request','ok':True})
addresses={r[4][0] for r in socket.getaddrinfo(socket.gethostname(),47721,socket.AF_INET)}
for address in addresses:
 if address.startswith('127.'):continue
 try:connection=socket.create_connection((address,47721),timeout=.3)
 except OSError:results.append({'case':'nonloopback_refused','ok':True})
 else:connection.close();raise AssertionError('nonloopback listener')
listener=subprocess.run(['powershell','-NoProfile','-Command','Get-NetTCPConnection -LocalPort 47721 -State Listen | Select-Object LocalAddress,OwningProcess | ConvertTo-Json'],capture_output=True,text=True,check=True)
r=json.loads(listener.stdout);assert r['LocalAddress']=='127.0.0.1' and r['OwningProcess']==v['pid'];results.append({'case':'listener_owner_loopback','ok':True})
Path('docs/acceptance-evidence/round3-ipc-'+v['build']+'.json').write_text(json.dumps(results,indent=2));print('IPC auth/allowlist/dedup/loopback passed')
