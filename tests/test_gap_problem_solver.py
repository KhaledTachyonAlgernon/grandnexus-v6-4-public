import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from grandnexus.gap_problem_solver import GapProblemSolver
from grandnexus.symbolic_planner import SimAction


def main():
    actions = [
        SimAction('survey_beacon', frozenset({'at:room', 'beacon:visible'}), frozenset({'beacon:surveyed'})),
        SimAction('inspect_archive', frozenset({'at:room', 'archive:unlocked'}), frozenset({'archive:inspected'})),
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'})),
    ]
    solver = GapProblemSolver(actions)

    analysis = solver.analyze({'at:room'}, {'door:open', 'at:room'}, (), ('door:open', 'at:room'))
    assert analysis.status == 'hypotheses_available'
    assert len(analysis.hypotheses) == 2
    assert analysis.hypotheses[0].category == 'missing_precondition'
    missing = {fact for item in analysis.hypotheses for fact in item.missing_facts}
    assert {'beacon:visible', 'archive:unlocked'} <= missing
    assert all('verify whether' in item.verification_question for item in analysis.hypotheses)

    conflict = solver.analyze({'at:room'}, set(), (('door:closed', 'door:open'),), ('door:open',))
    assert conflict.status == 'blocked_by_conflict'
    assert conflict.hypotheses == ()

    no_gap = solver.analyze({'at:room', 'beacon:visible', 'archive:unlocked'}, {'beacon:surveyed', 'archive:inspected'}, (), ('door:open',))
    assert no_gap.status == 'no_symbolic_gap'
    assert no_gap.hypotheses == ()
    print({'hypotheses': len(analysis.hypotheses), 'conflict': conflict.status, 'no_gap': no_gap.status})


if __name__ == '__main__':
    main()
