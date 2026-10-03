from pathlib import Path
import ast

root = Path('/home/ubuntu/grandnexus_rebuild')
source = (root / 'reference' / 'grandnexus_core_candidate.py').read_text(encoding='utf-8')
lines = source.splitlines(True)
tree = ast.parse(source)
all_classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
groups = {
    'cognition/reasoning/reasoning_core.py': ['ReasoningType', 'ConfidenceLevel', 'ReasoningStrategy', 'InferenceStep', 'ReasoningQuery', 'ReasoningResult', 'ReasoningCore'],
    'cognition/reasoning/neural_reasoner.py': ['EvidenceSourceType', 'ReasoningTask', 'NeuralEvidence', 'NeuralReasoningRequest', 'NeuralReasoningResult', 'NeuralReasoner'],
    'cognition/reasoning/hybrid_inference.py': ['InferenceType', 'HybridMode', 'SymbolicConstraint', 'InferenceQuery', 'InferenceStep', 'InferenceResult', 'HybridInferenceEngine'],
    'cognition/reasoning/planning.py': ['GoalState', 'TaskState', 'PlanningApproach', 'Condition', 'Effect', 'Task', 'Goal', 'Plan', 'PlanningModule'],
    'cognition/reasoning/uncertainty.py': ['UncertaintyType', 'UncertainBelief', 'BayesianNode', 'BayesianNetwork', 'UncertaintyManager'],
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
            text = ''.join(lines[node.lineno - 1:node.end_lineno])
            if not text.strip().startswith('from grandnexus.'):
                imports.append(text)
    destination = root / 'src' / 'grandnexus' / relpath
    destination.parent.mkdir(parents=True, exist_ok=True)
    body = ''.join(''.join(lines[n.lineno - 1:n.end_lineno]) + '\n\n' for n in selected)
    destination.write_text('from __future__ import annotations\n' + '\n'.join(imports) + '\n\n' + body, encoding='utf-8')
    print(destination)
