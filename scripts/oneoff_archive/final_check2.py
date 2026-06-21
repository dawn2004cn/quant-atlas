import py_compile, pathlib

files = [
    "app/bootstrap_components/services.py",
    "app/bootstrap_components/service_wiring.py",
    "app/bootstrap_components/wiring_ai.py",
    "app/bootstrap_components/wiring_market.py",
    "app/bootstrap_components/wiring_system.py",
    "app/bootstrap_components/wiring_trading.py",
    "app/bootstrap_components/injector.py",
    "app/bootstrap_components/module_wiring.py",
    "app/core/registry.py",
]
for m in ["ai_agent","collaboration","data","execution","market_data","mesh","misc","perception","portfolio","portfolio_risk","research","strategy","system","user"]:
    files.append(f"app/modules/{m}/module.py")

ok = True
for f in files:
    p = pathlib.Path(f)
    try:
        py_compile.compile(str(p), doraise=True)
        print(f"  OK  {f.split(chr(92))[-1]}")
    except py_compile.PyCompileError as e:
        print(f"FAIL  {f}")
        print(f"      {e}")
        ok = False

if ok:
    print(f"All {len(files)} files compile OK")
