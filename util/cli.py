#!/usr/bin/env python3
import argparse
import asyncio
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="notashelf",
        description="Consolidated CLI for NotAShelf utilities"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch-blog-feed
    fetch_blog_feed_parser = subparsers.add_parser(
        "fetch-blog-feed", help="Update README with latest blog posts"
    )
    fetch_blog_feed_parser.add_argument(
        "output_file", type=str, help="Path to the output markdown file"
    )

    # gen-images
    gen_images_parser = subparsers.add_parser(
        "gen-images", help="Generate SVG badges for GitHub stats"
    )

    # gen-random-workflow
    gen_random_workflow_parser = subparsers.add_parser(
        "gen-random-workflow", help="Randomize cron schedule in workflow"
    )
    gen_random_workflow_parser.add_argument(
        "--workflow", type=str, default=".github/workflows/rating-chart.yml",
        help="Path to workflow YAML"
    )

    # gen-table
    gen_table_parser = subparsers.add_parser(
        "gen-table", help="Generate markdown table from JSON"
    )
    gen_table_parser.add_argument(
        "file_path", type=str, help="Path to the JSON file"
    )

    # github-stats
    github_stats_parser = subparsers.add_parser(
        "github-stats", help="Show GitHub stats (debug/dev)"
    )

    # rating-chart
    rating_chart_parser = subparsers.add_parser(
        "rating-chart", help="Print chess.com ASCII rating chart"
    )

    args = parser.parse_args()

    if args.command == "fetch-blog-feed":
        from .fetch_blog_feed import update_readme
        update_readme(args.output_file)
    elif args.command == "gen-images":
        asyncio.run(_run_gen_images())
    elif args.command == "gen-random-workflow":
        _run_gen_random_workflow(args.workflow)
    elif args.command == "gen-table":
        from .gen_table import generate_markdown_table
        table = generate_markdown_table(Path(args.file_path))
        print(table)
    elif args.command == "github-stats":
        asyncio.run(_run_github_stats())
    elif args.command == "rating-chart":
        from .rating_chart import main as rating_main
        plot = rating_main()
        if plot:
            print("Rating Chart:")
            print(plot)
        else:
            print("No data available or an error occurred.")
    else:
        parser.print_help()
        sys.exit(1)

async def _run_gen_images():
    from .gen_images import main as gen_images_main
    await gen_images_main()

def _run_gen_random_workflow(workflow_path):
    import random
    cron_line = '"0 */{prevNo} * * *"'
    with open(workflow_path) as f:
        wf = f.read()
    randNo = random.randint(1, 8)
    newCron = cron_line.format(prevNo=randNo)
    for prevNum in range(1, 9):
        prevCron = cron_line.format(prevNo=prevNum)
        if prevCron in wf:
            wf = wf.replace(prevCron, newCron)
            break
    print(wf.rstrip())

async def _run_github_stats():
    from .github_stats import main as github_stats_main
    await github_stats_main()

if __name__ == "__main__":
    main()
