"""Transparent physical and executable-line comparison, not a complexity score."""
import ast
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
old=root/'verification/baseline_v4/main.py'
new=root/'main.py'
def count(file):
    source=file.read_text()
    lines=source.splitlines()
    executable=set()
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node,ast.stmt) and hasattr(node,'lineno'):
            executable.add(node.lineno)
    return {'physical_lines':len(lines),'nonempty_noncomment_lines':sum(bool(l.strip()) and not l.lstrip().startswith('#') for l in lines),'statement_start_lines':len(executable)}
a,b=count(old),count(new)
print(json.dumps({'baseline':a,'current':b,'change_percent':{key:round((b[key]/a[key]-1)*100,2) for key in a},'warning':'Line count is not a measurement of repetitive-code reduction. A fair 30% duplication claim requires a defined duplication metric and functionally equivalent baselines.'},indent=2))
