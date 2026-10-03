from pathlib import Path
import ast

root = Path('/home/ubuntu/grandnexus_rebuild')
source = (root / 'reference' / 'grandnexus_core_candidate.py').read_text(encoding='utf-8')
lines = source.splitlines(True)
tree = ast.parse(source)
all_classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
groups = {
    'cognition/perception/perception_core.py': ['InputType', 'PerceptionFilter', 'PerceptionResult', 'PerceptionCore'],
    'cognition/perception/symbolic_parser.py': ['SymbolicType', 'SymbolicAST', 'ParseResult', 'SymbolicParser'],
    'cognition/perception/code_analyzer.py': ['CodeLanguage', 'CodeNodeType', 'CodeMetrics', 'CodeNode', 'CodeAnalysisResult', 'CodeAnalyzer'],
    'cognition/perception/pattern_recognizer.py': ['PatternType', 'Pattern', 'PatternMatch', 'PatternSearchConfig', 'PatternRecognizer', 'PatternDetectorBase', 'SequentialPatternDetector', 'TemporalPatternDetector', 'StructuralPatternDetector', 'LinguisticPatternDetector', 'SymbolicPatternDetector'],
}
for relpath, wanted in groups.items():
    selected, seen = [], set()
    for node in all_classes:
        if node.name in wanted and node.name not in seen:
            selected.append(node); seen.add(node.name)
    selected.sort(key=lambda n: n.lineno)
    first = min(n.lineno for n in selected)
    imports = []
    for node in tree.body:
        if getattr(node, 'lineno', first) >= first:
            break
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(''.join(lines[node.lineno - 1:node.end_lineno]))
    destination = root / 'src' / 'grandnexus' / relpath
    destination.parent.mkdir(parents=True, exist_ok=True)
    body = ''.join(''.join(lines[n.lineno - 1:n.end_lineno]) + '\n\n' for n in selected)
    destination.write_text('from __future__ import annotations\n' + '\n'.join(imports) + '\n\n' + body, encoding='utf-8')
    print(destination)
