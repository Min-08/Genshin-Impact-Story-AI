from __future__ import annotations

import argparse
from pathlib import Path

from .dimbreath import crawl_dimbreath_textmaps
from .project_amber import crawl_project_amber
from .project_amber_deep import crawl_project_amber_deep
from .pipeline.project_amber_v2 import build_project_amber_v2


def main() -> None:
    parser = argparse.ArgumentParser(prog="project-amber-db-builder")
    parser.add_argument("--root", default=".", help="Project root directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    amber = subparsers.add_parser("crawl-project-amber", help="Fetch Project Amber API data")
    amber.add_argument("--languages", nargs="+", help="Language keys from config, e.g. ko zh-Hans ja en")
    amber.add_argument("--content-types", nargs="+", help="Project Amber content types")
    amber.add_argument("--limit", type=int, help="Limit list items per language/content type")
    amber.add_argument("--detail-limit", type=int, help="Limit fetched details per language/content type")
    amber.add_argument("--skip-details", action="store_true", help="Only fetch list endpoints")
    amber.add_argument(
        "--include-unreleased",
        action="store_true",
        default=None,
        help="Include entries marked as unreleased/future",
    )
    amber.add_argument("--force", action="store_true", help="Refetch cached files")
    amber.add_argument("--sleep", type=float, default=0.25, help="Delay between requests")

    amber_deep = subparsers.add_parser("crawl-project-amber-deep", help="Fetch Project Amber secondary text endpoints")
    amber_deep.add_argument("--languages", nargs="+", help="Language keys from config, e.g. ko zh-Hans ja en")
    amber_deep.add_argument("--content-types", nargs="+", help="Project Amber content types with deep text")
    amber_deep.add_argument("--limit", type=int, help="Limit detail records per language/content type")
    amber_deep.add_argument("--target-limit", type=int, help="Limit secondary targets per detail record")
    amber_deep.add_argument("--force", action="store_true", help="Refetch cached files")
    amber_deep.add_argument("--sleep", type=float, default=0.25, help="Delay between requests")

    textmap = subparsers.add_parser("crawl-dimbreath-textmap", help="Fetch Dimbreath TextMap files")
    textmap.add_argument("--languages", nargs="+", help="Language keys from config, e.g. ko zh-Hans ja en")
    textmap.add_argument("--force", action="store_true", help="Refetch cached files")
    textmap.add_argument("--sleep", type=float, default=0.5, help="Delay between requests")

    subparsers.add_parser("build-project-amber-v2", help="Build Project Amber v2 readable/canonical/search outputs")

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "crawl-project-amber":
        report = crawl_project_amber(
            root,
            languages=args.languages,
            content_types=args.content_types,
            limit=args.limit,
            detail_limit=args.detail_limit,
            skip_details=args.skip_details,
            include_unreleased=args.include_unreleased,
            force=args.force,
            sleep_seconds=args.sleep,
        )
    elif args.command == "crawl-project-amber-deep":
        report = crawl_project_amber_deep(
            root,
            languages=args.languages,
            content_types=args.content_types,
            limit=args.limit,
            target_limit=args.target_limit,
            force=args.force,
            sleep_seconds=args.sleep,
        )
    elif args.command == "crawl-dimbreath-textmap":
        report = crawl_dimbreath_textmaps(
            root,
            languages=args.languages,
            force=args.force,
            sleep_seconds=args.sleep,
        )
    elif args.command == "build-project-amber-v2":
        report = build_project_amber_v2(root)
    else:
        raise AssertionError(args.command)

    print(report)


if __name__ == "__main__":
    main()
