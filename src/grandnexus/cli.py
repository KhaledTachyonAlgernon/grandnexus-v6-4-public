"""Command-line entry point for the incremental GrandNexus recovery."""
import argparse
import json
import tempfile
from pathlib import Path

from .core.nexus_core import NexusCore
from .cognition.cognition_manager import CognitionManager, CognitiveTask
from .cognition.perception.perception_core import InputType, PerceptionResult
from .cognition.reasoning.reasoning_core import ReasoningQuery
from .memory.memory_manager import MemoryItem
from .memory.working import WorkingMemoryItem
from .pipeline import LightCognitivePipeline
from .advanced_reasoning import AdvancedReasoner
from .profiles import PROFILES


def smoke() -> None:
    """Validate the light, dependency-minimal object graph."""
    with tempfile.TemporaryDirectory() as tmp:
        core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / "nexus.db"))
        item = MemoryItem(content="smoke", memory_id="m1")
        working = WorkingMemoryItem(item_id="w1", content="smoke", source="cli")
        manager = CognitionManager(nexus_core=core)
        task = CognitiveTask(task_type="perception")
        result = PerceptionResult(input_type=InputType.TEXT, parsed_data="smoke")
        query = ReasoningQuery(question="smoke")
        assert item.content == working.content == result.parsed_data
        assert manager is not None and task.task_type == "perception" and query.question == "smoke"
    print("GrandNexus light smoke: OK")


def process(text: str, advanced: bool = False) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / "nexus.db"))
        reasoner = AdvancedReasoner() if advanced else None
        result = LightCognitivePipeline(core, advanced_reasoner=reasoner).process(text)
        print(json.dumps({
            "task_id": result.task_id,
            "input_type": result.perception.input_type.name,
            "concept_id": result.concept.concept_id,
            "reasoning": result.reasoning.conclusions,
            "trace": result.trace,
        }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="grandnexus")
    sub = parser.add_subparsers(dest="command", required=False)
    sub.add_parser("smoke")
    process_parser = sub.add_parser("process")
    process_parser.add_argument("--advanced", action="store_true")
    process_parser.add_argument("text")
    sub.add_parser("profiles")
    args = parser.parse_args()
    if args.command in (None, "smoke"):
        smoke()
    elif args.command == "process":
        process(args.text, advanced=args.advanced)
    elif args.command == "profiles":
        for name, profile in PROFILES.items():
            state = "available" if profile.available() else "missing: " + ", ".join(profile.missing())
            print(f"{name}: {state}")


if __name__ == "__main__":
    main()
