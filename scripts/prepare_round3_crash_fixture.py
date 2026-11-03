"""Prepare a disposable, explicitly gated crash-test plugin copy (never production code)."""
import shutil
from pathlib import Path
root=Path('.cache/round3-instrumented')
shutil.copytree('plugin',root/'plugin',dirs_exist_ok=True)
(root/'scripts').mkdir(parents=True,exist_ok=True)
shutil.copy2('scripts/install_plugin.py',root/'scripts/install_plugin.py')
p=root/'plugin/krita_agent_bridge/checkpoints.py'
s=p.read_text(encoding='utf-8')
s=s.replace('        ok = doc.saveAs(str(target))','        _acceptance_gate(bridge, "before_save")\n        ok = doc.saveAs(str(target))')
s=s.replace('    return {k: v for k, v in record.items()', '    _acceptance_gate(bridge, "after_save")\n    return {k: v for k, v in record.items()')
s+='''\n\ndef _acceptance_gate(bridge, phase):
    if os.environ.get("KRITA_ACCEPTANCE_CRASH_PHASE") == phase:
        import time
        (bridge.output_dir / "crash-event.json").write_text(json.dumps({"phase":phase,"pid":os.getpid()}))
        time.sleep(30)
'''
p.write_text(s,encoding='utf-8')
p=root/'plugin/krita_agent_bridge/__init__.py'
s=p.read_text(encoding='utf-8')
needle='                    node.paintLine(locations[i-1].toPoint(), locations[i].toPoint(), p0, p1)'
assert needle in s
s=s.replace(needle,needle+'''\n                    if i == 10 and os.environ.get("KRITA_ACCEPTANCE_CRASH_PHASE") == "during_stroke":
                        import time
                        self._doc().waitForDone()
                        (self.output_dir / "crash-event.json").write_text(json.dumps({"phase":"during_stroke","pid":os.getpid(),"paintLine_segments_completed":i}))
                        time.sleep(30)''')
p.write_text(s,encoding='utf-8')
print('Temporary crash fixture prepared; repository plugin unchanged')
