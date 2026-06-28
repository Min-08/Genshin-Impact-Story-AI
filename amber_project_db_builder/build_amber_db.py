from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="One-click Project Amber crawler and DB builder.")
    parser.add_argument("--languages", nargs="+", help="Language keys: ko zh-Hans ja en. Defaults to all.")
    parser.add_argument("--content-types", nargs="+", help="Project Amber content types. Defaults to all configured types.")
    parser.add_argument("--workers", type=int, default=12, help="Parallel workers for detail/deep/extras crawling.")
    parser.add_argument("--sleep", type=float, default=0.15, help="Delay for list crawling.")
    parser.add_argument("--force", action="store_true", help="Refetch existing raw files.")
    parser.add_argument("--include-unreleased", action="store_true", help="Include unreleased/future Project Amber entries.")
    parser.add_argument("--no-textmap", action="store_true", help="Skip Dimbreath TextMap crawl.")
    parser.add_argument("--skip-crawl", action="store_true", help="Build from existing data/raw without crawling.")
    parser.add_argument("--skip-build", action="store_true", help="Only crawl raw data.")
    parser.add_argument("--skip-audit", action="store_true", help="Skip JSONL/SQLite audit after build.")
    parser.add_argument("--eval", action="store_true", help="Run the small search evaluation set after build.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing.")
    args = parser.parse_args()

    commands = build_commands(args)
    if args.dry_run:
        for command in commands:
            print(format_command(command))
        return 0

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    for command in commands:
        print(f"\n$ {format_command(command)}", flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True)

    print("\nDone.")
    print("SQLite DB: data/processed/search_v2/project_amber_search.sqlite3")
    print("Canonical JSONL: data/canonical/project_amber_v2/")
    print("Readable JSON: data/processed/project_amber_readable_v2/")
    return 0


def build_commands(args: argparse.Namespace) -> list[list[str]]:
    commands: list[list[str]] = []
    if not args.skip_crawl:
        list_args = base_crawl_args(args)
        commands.append([sys.executable, "scripts/crawl_project_amber.py", "--skip-details", *list_args])

        commands.append([sys.executable, "scripts/fill_project_amber_details_parallel.py", *detail_parallel_args(args)])
        commands.append([sys.executable, "scripts/fill_project_amber_deep_parallel.py", *deep_parallel_args(args)])
        commands.append([sys.executable, "scripts/crawl_project_amber_extras.py", *extras_parallel_args(args)])

        if not args.no_textmap:
            commands.append([sys.executable, "scripts/crawl_dimbreath_textmap.py", *textmap_args(args)])

    if not args.skip_build:
        commands.append([sys.executable, "scripts/build_project_amber_v2.py"])
        if not args.skip_audit:
            commands.append([sys.executable, "scripts/audit_project_amber_v2.py", "--fail-on-issues"])
        if args.eval:
            commands.append([sys.executable, "scripts/eval_project_amber_v2.py"])
    return commands


def base_crawl_args(args: argparse.Namespace) -> list[str]:
    result: list[str] = []
    add_common_filters(result, args)
    if args.force:
        result.append("--force")
    if args.include_unreleased:
        result.append("--include-unreleased")
    result.extend(["--sleep", str(args.sleep)])
    return result


def detail_parallel_args(args: argparse.Namespace) -> list[str]:
    result: list[str] = []
    add_common_filters(result, args)
    if args.force:
        result.append("--force")
    if args.include_unreleased:
        result.append("--include-unreleased")
    result.extend(["--workers", str(args.workers)])
    return result


def deep_parallel_args(args: argparse.Namespace) -> list[str]:
    result: list[str] = []
    add_common_filters(result, args)
    if args.force:
        result.append("--force")
    result.extend(["--workers", str(args.workers)])
    return result


def extras_parallel_args(args: argparse.Namespace) -> list[str]:
    result: list[str] = []
    add_common_filters(result, args)
    if args.force:
        result.append("--force")
    result.extend(["--workers", str(args.workers)])
    return result


def textmap_args(args: argparse.Namespace) -> list[str]:
    result: list[str] = []
    if args.languages:
        result.extend(["--languages", *args.languages])
    if args.force:
        result.append("--force")
    result.extend(["--sleep", str(max(args.sleep, 0.5))])
    return result


def add_common_filters(result: list[str], args: argparse.Namespace) -> None:
    if args.languages:
        result.extend(["--languages", *args.languages])
    if args.content_types:
        result.extend(["--content-types", *args.content_types])


def format_command(command: list[str]) -> str:
    return " ".join(quote(part) for part in command)


def quote(part: str) -> str:
    if not part:
        return '""'
    if any(char.isspace() for char in part):
        return f'"{part}"'
    return part


if __name__ == "__main__":
    raise SystemExit(main())
