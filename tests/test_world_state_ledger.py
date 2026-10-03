from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction
from grandnexus.world_state_ledger import WorldStateLedger


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ledger_path = root / 'world.db'
        ledger = WorldStateLedger(ledger_path)
        r1 = ledger.apply_transition('agent', {'at:home', 'door:open'}, (), 'test', 'episode:1')
        assert ledger.snapshot('agent').facts == frozenset({'at:home', 'door:open'})
        r2 = ledger.apply_transition('agent', {'door:closed'}, {'door:open'}, 'test', 'episode:2')
        snap = ledger.snapshot('agent')
        assert 'door:closed' in snap.facts and 'door:open' not in snap.facts and not snap.conflicts
        ledger.close()

        restored = WorldStateLedger(ledger_path)
        snap2 = restored.snapshot('agent')
        assert snap2.facts == snap.facts and snap2.revision == r2
        restored.rollback_to('agent', r1)
        rolled = restored.snapshot('agent')
        assert 'door:open' in rolled.facts and 'door:closed' not in rolled.facts
        restored.apply_transition('agent', {'door:closed'}, (), 'ambiguous', 'episode:3')
        conflicted = restored.snapshot('agent')
        assert not {'door:open', 'door:closed'} & set(conflicted.facts)
        assert ('door:closed', 'door:open') in conflicted.conflicts
        restored.close()

        graph = SemanticGraph(root / 'graph.db')
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('test',), 'v1')
        loop_db = root / 'loop_world.db'
        loop = IntegratedCognitiveLoop(graph, [
            SimAction('find_token', frozenset({'at:home'}), frozenset({'has:token'})),
            SimAction('open_gate', frozenset({'has:token'}), frozenset({'gate:open'})),
        ], root / 'learning.db', world_state_db=loop_db)
        first = loop.run('agent', ['has:token'], request_id='ledger-1')
        assert first.accepted
        loop.world_state.close()

        restarted = IntegratedCognitiveLoop(graph, [
            SimAction('open_gate', frozenset({'has:token'}), frozenset({'gate:open'})),
        ], root / 'learning-restarted.db', world_state_db=loop_db)
        second = restarted.run('agent', ['gate:open'], request_id='ledger-2')
        assert second.accepted and second.simulation and second.simulation.executed == ('open_gate',)
        assert 'gate:open' in restarted.world_state.snapshot('agent').facts
        print('world_state_ledger=OK')


if __name__ == '__main__':
    main()
