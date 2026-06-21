with open('app/infrastructure/rdagent/rdagent_factor_loop.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "return Path(rdagent.__file__).resolve().parent / \"scenarios\" / \"qlib\" / \"experiment\" / \"factor_template\""

new = '''    rdagent_file = getattr(rdagent, "__file__", None)
    if rdagent_file is None:
        raise FileNotFoundError("rdagent module has no __file__ - namespace package or missing installation")
    return Path(rdagent_file).resolve().parent / "scenarios" / "qlib" / "experiment" / "factor_template"'''

content = content.replace(old, new)

with open('app/infrastructure/rdagent/rdagent_factor_loop.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('app/infrastructure/rdagent/rdagent_factor_loop.py', doraise=True)
print('OK')
