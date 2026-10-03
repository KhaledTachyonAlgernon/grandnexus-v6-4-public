import json
from collections import Counter
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'free_simulated_autonomy.json'
data = json.loads(path.read_text())
rows = data['cycles']
windows = {}
for name, start, end in (
    ('battery', 23, 29),
    ('unknown_location', 48, 58),
    ('restart', 59, 64),
    ('conflict', 78, 87),
):
    windows[name] = [
        {
            'cycle': row['cycle'],
            'status': row['status'],
            'objective': row['objective'],
            'accepted': row['accepted'],
            'success': row['success'],
            'executed': row['executed'],
            'reason': row['reason'],
            'revision_before': row['state_revision_before'],
            'revision_after': row['state_revision_after'],
        }
        for row in rows if start <= row['cycle'] <= end
    ]
transitions = Counter((rows[i - 1]['objective'], rows[i]['objective']) for i in range(1, len(rows)))
output = {
    'windows': windows,
    'top_transition_pairs': [
        {'from': pair[0], 'to': pair[1], 'count': count}
        for pair, count in transitions.most_common(10)
    ],
    'unique_objectives': len({row['objective'] for row in rows if row['objective']}),
    'cycles_with_new_effect_once': sum(1 for objective, count in Counter(row['objective'] for row in rows if row['objective']).items() if count == 1),
    'pending_proposal_cycles': [row['cycle'] for row in rows if row['learning_proposal_id']],
}
(Path(__file__).resolve().parents[1] / 'free_simulated_autonomy_analysis.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(output, ensure_ascii=False, indent=2))
