import importlib

modules = [
    'grandnexus.memory.memory_manager',
    'grandnexus.memory.episodic',
    'grandnexus.memory.semantic',
    'grandnexus.memory.working',
]
for name in modules:
    try:
        importlib.import_module(name)
    except Exception as exc:
        print(f'{name}=ERROR {type(exc).__name__}: {exc}')
    else:
        print(f'{name}=OK')
