from pathlib import Path
import ast
import io
import tokenize

path = Path('/home/ubuntu/grandnexus_core_candidate.py')
source = path.read_text(encoding='utf-8')
try:
    ast.parse(source, filename=str(path))
    print('ast=OK')
except SyntaxError as exc:
    print(f'ast=ERROR line={exc.lineno} offset={exc.offset} msg={exc.msg}')
    lines = source.splitlines()
    start = max(1, (exc.lineno or 1) - 6)
    end = min(len(lines), (exc.lineno or 1) + 6)
    for n in range(start, end + 1):
        print(f'{n}: {lines[n-1]}')
try:
    list(tokenize.generate_tokens(io.StringIO(source).readline))
    print('tokenize=OK')
except (tokenize.TokenError, IndentationError) as exc:
    print(f'tokenize=ERROR {type(exc).__name__}: {exc}')
