#!/usr/bin/env python3
"""Build readable, self-verifying single-file GrandNexus transport bundles.

The output is intentionally a Python script whose embedded source remains visible
as comment-prefixed lines. It can verify hashes and reconstruct the original
modular file tree without treating the runtime architecture as a monolith.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT.parent

CORE_MODULES = (
    "src/grandnexus/__init__.py",
    "src/grandnexus/advanced_planner.py",
    "src/grandnexus/autonomy_level1.py",
    "src/grandnexus/branch_contracts.py",
    "src/grandnexus/drive_module.py",
    "src/grandnexus/drive_policy.py",
    "src/grandnexus/episodic_context.py",
    "src/grandnexus/failure_events.py",
    "src/grandnexus/gap_problem_solver.py",
    "src/grandnexus/graph_planner.py",
    "src/grandnexus/integrated_loop.py",
    "src/grandnexus/learning_controller.py",
    "src/grandnexus/learning_experiment.py",
    "src/grandnexus/metacognition_loop.py",
    "src/grandnexus/observability.py",
    "src/grandnexus/semantic_graph.py",
    "src/grandnexus/semantic_knowledge.py",
    "src/grandnexus/shadow_cycle.py",
    "src/grandnexus/source_reputation.py",
    "src/grandnexus/symbolic_planner.py",
    "src/grandnexus/trajectory_metacognition.py",
    "src/grandnexus/verification_experiment_proposer.py",
    "src/grandnexus/world_state_ledger.py",
    "src/grandnexus/memory/__init__.py",
    "src/grandnexus/memory/episodic.py",
)

FOCUSED_TESTS = (
    "tests/test_verification_experiment_proposer.py",
    "tests/test_verification_experiment_autonomy_integration.py",
    "tests/run_verification_experiment_multienv.py",
    "tests/test_gap_problem_solver.py",
    "tests/test_trajectory_metacognition.py",
    "tests/test_trajectory_autonomy_integration.py",
    "tests/test_autonomy_level1.py",
    "tests/test_world_state_ledger.py",
    "tests/test_episodic_integration.py",
    "tests/test_causal_recall_robustness.py",
    "tests/test_contradictory_episode_stress.py",
    "tests/test_core_autonomy.py",
    "tests/test_failure_and_contradiction_campaign.py",
    "tests/test_shadow_memory.py",
)

REVIEW_DOCUMENTS = (
    "ONE_FILE_AI_HANDOFF_GUIDE.md",
    "GRANDNEXUS_CORE_IDENTITY_CONTRACT.md",
    "ROADMAP_NOTATION_V6_4.md",
    "WORLD_STATE_LEDGER_REPORT.md",
    "TRAJECTORY_METACOGNITION_REPORT.md",
    "GAP_PROBLEM_SOLVER_REPORT.md",
    "VERIFICATION_EXPERIMENT_PROPOSER_REPORT.md",
    "FREE_SIMULATED_AUTONOMY_REPORT.md",
    "FAILURE_CONTRADICTION_AUTONOMY_REPORT.md",
)

REVIEW_OBSERVATIONS = (
    "trajectory_multienv_observation.json",
    "verification_experiment_multienv_observation.json",
)

RUNTIME_HEADER = '''#!/usr/bin/env python3
"""{title}.

This is a readable, single-file TRANSPORT BUNDLE rather than a runtime monolith.
The modular files follow `# BUNDLE-DATA-START`; every `# BUNDLE-FILE` section
records its original relative path, SHA-256 digest, and byte length. Every source
line is prefixed with `#|` only so this carrier remains valid Python.

Use `--overview`, `--list`, `--verify`, `--print PATH`, or `--extract DIRECTORY`.
"""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

BUNDLE_TITLE = {title!r}
BUNDLE_PROFILE = {profile!r}
BUNDLE_COMMIT = {commit!r}
BUNDLE_FILE_COUNT = {file_count}
BUNDLE_SOURCE_BYTES = {source_bytes}
BUNDLE_SHA256 = {bundle_sha!r}


@dataclass(frozen=True)
class BundleFile:
    path: str
    sha256: str
    byte_length: int
    content: str


def _bundle_path() -> Path:
    return Path(__file__).resolve()


def _iter_files() -> Iterator[BundleFile]:
    in_data = False
    current_path = None
    current_sha = None
    current_size = None
    content_lines: list[str] = []
    with _bundle_path().open('r', encoding='utf-8', newline='') as handle:
        for line in handle:
            if not in_data:
                if line == '# BUNDLE-DATA-START\\n':
                    in_data = True
                continue
            if line.startswith('# BUNDLE-FILE '):
                if current_path is not None:
                    raise ValueError(f'unclosed bundle file: {{current_path}}')
                _, _, path, sha256, byte_length = line.rstrip('\\n').split(' ', 4)
                current_path, current_sha, current_size = path, sha256, int(byte_length)
                content_lines = []
                continue
            if line == '# BUNDLE-END\\n':
                if current_path is None:
                    raise ValueError('bundle ended without an active file')
                content = ''.join(content_lines)
                encoded = content.encode('utf-8')
                if len(encoded) > current_size:
                    if encoded[current_size:] != b'\\n':
                        raise ValueError('embedded content exceeds its declared byte length')
                    content = encoded[:current_size].decode('utf-8')
                yield BundleFile(current_path, current_sha, current_size, content)
                current_path = current_sha = current_size = None
                content_lines = []
                continue
            if current_path is None:
                raise ValueError('content found outside a bundle file section')
            if not line.startswith('#|'):
                raise ValueError(f'non-prefixed content in {{current_path}}')
            content_lines.append(line[2:])
    if not in_data:
        raise ValueError('bundle data marker was not found')
    if current_path is not None:
        raise ValueError(f'unclosed bundle file at end of bundle: {{current_path}}')


def _validate_path(relative_path: str) -> PurePosixPath:
    candidate = PurePosixPath(relative_path)
    if candidate.is_absolute() or '..' in candidate.parts or not candidate.parts:
        raise ValueError(f'unsafe bundle path: {{relative_path}}')
    return candidate


def verify() -> tuple[int, int]:
    count = 0
    source_bytes = 0
    for item in _iter_files():
        _validate_path(item.path)
        encoded = item.content.encode('utf-8')
        actual = hashlib.sha256(encoded).hexdigest()
        if actual != item.sha256:
            raise ValueError(f'hash mismatch: {{item.path}}')
        if len(encoded) != item.byte_length:
            raise ValueError(f'length mismatch: {{item.path}}')
        count += 1
        source_bytes += len(encoded)
    if count != BUNDLE_FILE_COUNT or source_bytes != BUNDLE_SOURCE_BYTES:
        raise ValueError('bundle manifest totals do not match embedded content')
    return count, source_bytes


def extract(destination: str, overwrite: bool = False) -> tuple[int, int]:
    target_root = Path(destination).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    count, source_bytes = verify()
    for item in _iter_files():
        target = target_root.joinpath(*_validate_path(item.path).parts)
        if target.exists() and not overwrite:
            raise FileExistsError(f'refusing to overwrite {{target}}; use --overwrite')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding='utf-8', newline='')
    return count, source_bytes


def overview() -> str:
    return (
        f'{{BUNDLE_TITLE}}\\n'
        f'profile={{BUNDLE_PROFILE}}; commit={{BUNDLE_COMMIT}}\\n'
        f'embedded files={{BUNDLE_FILE_COUNT}}; source bytes={{BUNDLE_SOURCE_BYTES}}\\n\\n'
        'This is a transport carrier, not a GrandNexus runtime monolith.\\n'
        'Read # BUNDLE-FILE sections as the original modular files.\\n'
        'Use --verify before extraction; use --extract DESTINATION to restore them.\\n'
        'For AI review, inspect ONE_FILE_AI_HANDOFF_GUIDE.md first when present.'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='Inspect or extract this GrandNexus transport bundle.')
    parser.add_argument('--overview', action='store_true', help='print bundle identity and reading instructions')
    parser.add_argument('--list', action='store_true', help='list original embedded paths')
    parser.add_argument('--verify', action='store_true', help='verify all paths, byte lengths, and SHA-256 digests')
    parser.add_argument('--print', dest='print_path', metavar='PATH', help='print one original embedded file')
    parser.add_argument('--extract', metavar='DIRECTORY', help='recreate the modular tree under DIRECTORY')
    parser.add_argument('--overwrite', action='store_true', help='allow --extract to overwrite existing files')
    args = parser.parse_args()
    if not any((args.overview, args.list, args.verify, args.print_path, args.extract)):
        parser.print_help()
        return
    if args.overview:
        print(overview())
    if args.list:
        for item in _iter_files():
            print(f'{{item.path}}\\t{{item.byte_length}} bytes\\t{{item.sha256}}')
    if args.verify:
        count, source_bytes = verify()
        print(f'OK: {{count}} embedded files, {{source_bytes}} source bytes verified')
    if args.print_path:
        for item in _iter_files():
            if item.path == args.print_path:
                print(item.content, end='')
                break
        else:
            raise FileNotFoundError(f'embedded path not found: {{args.print_path}}')
    if args.extract:
        count, source_bytes = extract(args.extract, overwrite=args.overwrite)
        print(f'Extracted {{count}} files ({{source_bytes}} source bytes) to {{Path(args.extract).resolve()}}')


if __name__ == '__main__':
    main()

# BUNDLE-DATA-START
'''


def git_output(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def tracked_files() -> tuple[str, ...]:
    return tuple(line for line in git_output("ls-files").splitlines() if line)


def review_files() -> tuple[str, ...]:
    selected = ("pyproject.toml", *REVIEW_DOCUMENTS, *CORE_MODULES, *FOCUSED_TESTS, *REVIEW_OBSERVATIONS)
    tracked = set(tracked_files())
    missing = sorted(path for path in selected if path not in tracked)
    if missing:
        raise FileNotFoundError(f"review profile references untracked or missing files: {missing}")
    return tuple(sorted(set(selected)))


def read_text(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"non-UTF-8 file cannot enter readable transport bundle: {path}") from exc


def bundle_sha(entries: list[tuple[str, str]]) -> str:
    digest = hashlib.sha256()
    for path, content in entries:
        encoded = content.encode("utf-8")
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(encoded).digest())
        digest.update(b"\n")
    return digest.hexdigest()


def render(profile: str, paths: tuple[str, ...]) -> str:
    commit = git_output("rev-parse", "HEAD")
    entries = [(path, read_text(path)) for path in paths]
    source_bytes = sum(len(content.encode("utf-8")) for _, content in entries)
    title = "GrandNexus v6.4 Full Transport Bundle" if profile == "full_transport" else "GrandNexus v6.4 AI Review Bundle"
    output = RUNTIME_HEADER.format(
        title=title,
        profile=profile,
        commit=commit,
        file_count=len(entries),
        source_bytes=source_bytes,
        bundle_sha=bundle_sha(entries),
    )
    for path, content in entries:
        encoded = content.encode("utf-8")
        output += f"# BUNDLE-FILE {path} {hashlib.sha256(encoded).hexdigest()} {len(encoded)}\n"
        if content:
            for line in content.splitlines(keepends=True):
                output += f"#|{line}"
            if not content.endswith(("\n", "\r")):
                output += "\n"
        output += "# BUNDLE-END\n"
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate readable one-file GrandNexus transport bundles.")
    parser.add_argument("--profile", choices=("ai_review", "full_transport"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = review_files() if args.profile == "ai_review" else tracked_files()
    rendered = render(args.profile, paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="")
    print(f"Wrote {args.output} with {len(paths)} embedded files and {len(rendered.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
