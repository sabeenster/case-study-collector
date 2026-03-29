"""Entry point for Case Study Collector."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("casestudy").setLevel(logging.INFO)

console = Console()


def cmd_serve(args):
    """Start the web UI."""
    import uvicorn
    console.print(Panel(
        f"[bold]Case Study Collector[/bold]\n"
        f"http://localhost:{args.port}",
        style="blue",
    ))
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=True)


def cmd_brands(args):
    """List all brands."""
    from app.config import AppConfig
    from app import db

    config = AppConfig.load()
    config.ensure_dirs()
    db.init_db(config.db_path)

    brands = db.get_brands(config.db_path)
    if not brands:
        console.print("[dim]No brands yet. Use the web UI to add brands.[/dim]")
        return

    for brand in brands:
        console.print(Panel(
            f"[bold]{brand['name']}[/bold]\n"
            f"Industry: {brand.get('industry', '-')}\n"
            f"Onboarded: {brand.get('onboarded_at', '-')}\n"
            f"Snapshots: {brand['snapshot_count']}\n"
            f"Last snapshot: {brand.get('last_snapshot') or '-'}",
            style="blue",
        ))


def cmd_generate(args):
    """Generate a case study for a brand."""
    from app.config import AppConfig
    from app import db
    from app.generator import generate_case_study_sync

    config = AppConfig.load()
    config.ensure_dirs()
    db.init_db(config.db_path)

    # Find brand by name
    brands = db.get_brands(config.db_path)
    brand = next((b for b in brands if b["name"].lower() == args.brand.lower()), None)
    if not brand:
        console.print(f"[red]Brand '{args.brand}' not found.[/red]")
        console.print("Available brands:")
        for b in brands:
            console.print(f"  - {b['name']}")
        return

    brand_data = db.get_brand_full(config.db_path, brand["id"])

    console.print(f"[dim]Generating case study for {brand['name']}...[/dim]")
    case_study = generate_case_study_sync(brand_data, config)

    console.print(Panel(case_study, title=f"Case Study: {brand['name']}", style="green"))


def cmd_email(args):
    """Generate and email a case study."""
    from app.config import AppConfig
    from app import db
    from app.generator import generate_case_study_sync
    from app.notify import send_case_study_email

    config = AppConfig.load()
    config.ensure_dirs()
    db.init_db(config.db_path)

    brands = db.get_brands(config.db_path)
    brand = next((b for b in brands if b["name"].lower() == args.brand.lower()), None)
    if not brand:
        console.print(f"[red]Brand '{args.brand}' not found.[/red]")
        return

    brand_data = db.get_brand_full(config.db_path, brand["id"])

    console.print(f"[dim]Generating case study for {brand['name']}...[/dim]")
    case_study = generate_case_study_sync(brand_data, config)

    console.print(Panel(case_study, title=f"Case Study: {brand['name']}", style="green"))

    send_case_study_email(brand["name"], case_study, config)


def main():
    parser = argparse.ArgumentParser(description="Case Study Collector")
    sub = parser.add_subparsers(dest="command")

    # serve
    p_serve = sub.add_parser("serve", help="Start web UI")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--host", default="0.0.0.0")

    # brands
    sub.add_parser("brands", help="List all brands")

    # generate-case-study
    p_gen = sub.add_parser("generate-case-study", help="Generate case study")
    p_gen.add_argument("--brand", required=True, help="Brand name")

    # email-case-study
    p_email = sub.add_parser("email-case-study", help="Generate and email case study")
    p_email.add_argument("--brand", required=True, help="Brand name")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "brands":
        cmd_brands(args)
    elif args.command == "generate-case-study":
        cmd_generate(args)
    elif args.command == "email-case-study":
        cmd_email(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
