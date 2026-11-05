import sys,json,time,subprocess,statistics
from pathlib import Path
sys.path.insert(0,'src');from krita_agent.client import Client
v=json.loads(Path('.cache/round2/current.json').read_text());c=Client(v['token'],47721,timeout=60);samples=[]
for _ in range(8):
 start=time.perf_counter();status=c.request('status');samples.append((time.perf_counter()-start)*1000)
memory=subprocess.run(['powershell','-NoProfile','-Command','Get-Process -Id '+str(v['pid'])+' | Select-Object Id,WorkingSet64,PeakWorkingSet64,CPU | ConvertTo-Json'],check=True,capture_output=True,text=True)
record={'build':v['build'],'document':c.request('document.info'),'rpc_status_ms':samples,'mean_status_ms':statistics.mean(samples),'memory_at_sample':json.loads(memory.stdout),'storage_bytes_at_sample':sum(p.stat().st_size for p in Path(v['out']).rglob('*') if p.is_file()),'scope':'Single-session observations; memory sampled during acceptance, not a statistical benchmark'}
Path('docs/acceptance-evidence/round4-metrics-'+v['build']+'.json').write_text(json.dumps(record,indent=2));print(record['document'],record['mean_status_ms'])
