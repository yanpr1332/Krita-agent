"""Final filter undo and independent storage checks on a disposable session."""
from pathlib import Path
import json
ns={}
source=Path('scripts/acceptance_round3.py').read_text(encoding='utf-8')
exec(compile(source.split("case('runtime'")[0],'<round3 helpers>','exec'),ns)
def filter_undo():
 q,shot,eq=ns['q'],ns['shot'],ns['eq'];ns['fresh']('Filter native undo');ns['fill']();before=shot();q('filter.mask.create',name='Undo filter',filter='invert',parent_name='Ink',confirm=True);filtered=shot();assert filtered.getpixel((15,15))[:3]==(0,255,255);q('history.undo');eq(shot(),before);q('history.redo');eq(shot(),filtered)
 q('selection.rectangle',x=10,y=10,width=5,height=5);q('mask.create',kind='selection',name='Stored local selection',parent_name='Ink');q('selection.clear');name='supplement-'+ns['seq']+'.kra';q('document.save',path=name);q('document.open',path=name);assert any(n['name']=='Stored local selection' and n['type']=='selectionmask' for n in q('layer.tree'));eq(shot(),filtered)
 return {'undo_redo_pixel_equal':True,'selection_mask_retained':True}
ns['case']('filter_native_undo_selection_mask',filter_undo)
ns['case']('storage_safety_final',ns['malicious_storage'])
ns['case']('revision_guard_final',ns['revision_guards'])
rows=ns['rows'];Path('docs/acceptance-evidence/round3-supplement-'+ns['v']['build']+'.json').write_text(json.dumps(rows,indent=2));print(rows);assert all(r['ok'] for r in rows)
