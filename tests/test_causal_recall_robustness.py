from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.episodic_context import LocalEpisodicContext
from grandnexus.symbolic_planner import SimulationResult


def record(ctx, request_id, initial, final, success=True):
    return ctx.record(
        request_id,
        ['target'],
        initial,
        SimulationResult(success, frozenset(final), ('action',) if success else (), None if success else 'failed'),
        success,
    )


def main():
    ctx = LocalEpisodicContext()
    record(ctx, 'valid', {'at:home'}, {'at:home', 'has:key'})
    record(ctx, 'wrong-context', {'at:lab'}, {'at:lab', 'has:key'})
    record(ctx, 'irrelevant', {'at:home'}, {'at:home', 'has:map'})
    record(ctx, 'failed', {'at:home'}, {'at:home'}, False)

    valid = ctx.recall(['open:door'], required_effects=['has:key'], current_state=['at:home'])
    incompatible = ctx.recall(['open:door'], required_effects=['has:key'], current_state=['at:garage'])
    unrelated = ctx.recall(['open:door'], required_effects=['has:map'], current_state=['at:home'])
    assert 'has:key' in valid.recalled_state
    assert 'has:key' not in incompatible.recalled_state
    assert 'has:key' not in unrelated.recalled_state

    valid_episode = ctx.memory.episodes['episode:valid']
    valid_episode.decay_activation(1.0, valid_episode.last_access_time + 10_000_000)
    evaporated = ctx.recall(['open:door'], required_effects=['has:key'], current_state=['at:home'])
    assert 'has:key' not in evaporated.recalled_state

    record(ctx, 'contradictory-open', {'at:home'}, {'at:home', 'door:open'})
    record(ctx, 'contradictory-closed', {'at:home'}, {'at:home', 'door:closed'})
    concurrent = ctx.recall(['door state'], required_effects=['door:open', 'door:closed'], current_state=['at:home'])
    # Both provenances remain stored, but neither incompatible effect becomes active without a reliable order.
    assert 'door:open' not in concurrent.recalled_state and 'door:closed' not in concurrent.recalled_state
    assert ('door:closed', 'door:open') in concurrent.conflicts
    print({'valid': valid.recalled_state, 'incompatible': incompatible.recalled_state, 'unrelated': unrelated.recalled_state, 'after_evaporation': evaporated.recalled_state, 'contradictory': concurrent.recalled_state})
    print('causal_recall_robustness=OK')


if __name__ == '__main__':
    main()
