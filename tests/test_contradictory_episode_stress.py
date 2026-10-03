from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.episodic_context import LocalEpisodicContext
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction, SimulationResult


def add(ctx, rid, initial, final, success=True):
    ctx.record(rid, ['target'], initial, SimulationResult(success, frozenset(final), ('action',), None, 'simulation completed'), success)


def main():
    ctx = LocalEpisodicContext()
    add(ctx, 'open-old', {'at:home'}, {'at:home', 'door:open'})
    add(ctx, 'closed-now', {'at:home', 'door:open'}, {'at:home', 'door:closed'})
    add(ctx, 'open-lab', {'at:lab'}, {'at:lab', 'door:open'})
    add(ctx, 'map-only', {'at:home'}, {'at:home', 'has:map'})

    recalled_open = ctx.recall(['gate'], required_effects=['door:open'], current_state=['at:home', 'door:closed'])
    recalled_both = ctx.recall(['gate'], required_effects=['door:open', 'door:closed'], current_state=['at:home', 'door:closed'])
    lab_context = ctx.recall(['gate'], required_effects=['door:open'], current_state=['at:lab'])

    graph = SemanticGraph(Path(tempfile.mkdtemp()) / 'graph.db')
    agent = graph.add_node('agent', node_id='agent')
    home = graph.add_node('home', node_id='home')
    graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('test',), 'v1')
    loop = IntegratedCognitiveLoop(graph, [
        SimAction('pass_open_gate', frozenset({'door:open'}), frozenset({'gate:open'})),
    ], Path(tempfile.mkdtemp()) / 'learn.db', enable_world_state=False)
    loop.episodic_context = ctx
    decision = loop.run('agent', ['gate:open'], request_id='stress-plan')

    ambiguous = LocalEpisodicContext()
    add(ambiguous, 'ambiguous-open', {'at:home'}, {'at:home', 'door:open'})
    add(ambiguous, 'ambiguous-closed', {'at:home'}, {'at:home', 'door:closed'})
    ambiguous_loop = IntegratedCognitiveLoop(graph, [
        SimAction('pass_open_gate', frozenset({'door:open'}), frozenset({'gate:open'})),
    ], Path(tempfile.mkdtemp()) / 'ambiguous-learn.db', enable_world_state=False)
    ambiguous_loop.episodic_context = ambiguous
    ambiguous_decision = ambiguous_loop.run('agent', ['gate:open'], request_id='ambiguous-plan')

    result = {
        'open_with_closed_current': sorted(recalled_open.recalled_state),
        'open_and_closed_requested': sorted(recalled_both.recalled_state),
        'lab_context': sorted(lab_context.recalled_state),
        'planner_decision': {'accepted': decision.accepted, 'reason': decision.reason, 'executed': decision.simulation.executed if decision.simulation else ()},
        'ambiguous_decision': {'accepted': ambiguous_decision.accepted, 'reason': ambiguous_decision.reason},
    }
    print(result)
    assert 'door:open' not in recalled_open.recalled_state
    assert 'door:open' in recalled_open.suppressed_effects
    assert 'door:open' in lab_context.recalled_state
    assert not decision.accepted
    assert not ambiguous_decision.accepted
    assert 'episodic state conflict' in ambiguous_decision.reason
    print('contradictory_episode_stress=OK')


if __name__ == '__main__':
    main()
