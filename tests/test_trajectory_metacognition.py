from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.trajectory_metacognition import TrajectoryMetacognition


def observe(observer, objective, before=(), after=()):
    observer.observe(objective, before, after)


def main():
    observer = TrajectoryMetacognition(window=12, min_pattern_repetitions=3, cooldown_cycles=2)
    for objective, before, after in (
        ('has:key', ('at:home',), ('at:home', 'has:key')),
        ('door:open', ('at:home', 'has:key'), ('at:home', 'has:key', 'door:open')),
        ('at:room', ('at:home', 'door:open'), ('at:room', 'door:open')),
    ):
        observe(observer, objective, before, after)
    informative = observer.assess(['has:map'], {'at:room'})
    assert informative.status == 'normal' and informative.novelty == 1.0

    for _ in range(3):
        for objective in ('door:closed', 'door:open', 'at:room', 'at:home'):
            observe(observer, objective, (), ())
    stagnating = observer.assess(['door:closed', 'at:room'], {'at:home', 'door:open'})
    assert stagnating.status == 'stagnating'
    assert stagnating.pattern_repetitions >= 3
    assert stagnating.novelty == 0.0
    observer.mark_reflective_pause()
    cooldown = observer.assess(['door:closed'], {'at:home', 'door:open'})
    assert cooldown.status == 'cooldown'
    observe(observer, 'door:closed')
    observe(observer, 'door:open')
    resumed = observer.assess(['door:closed'], {'at:home', 'door:open'})
    assert resumed.status == 'stagnating'
    print('trajectory_metacognition=OK')


if __name__ == '__main__':
    main()
