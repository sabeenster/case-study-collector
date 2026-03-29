"""Case study narrative generation via Claude API."""

from __future__ import annotations

import asyncio
import logging

import anthropic

from app.config import AppConfig

logger = logging.getLogger("casestudy.generator")

SYSTEM_PROMPT = """You are a case study writer for Agentway, a company that deploys AI-powered customer support agents for e-commerce brands.

Your job is to take raw data — metrics snapshots, text entries, observations, and quotes — and turn them into a compelling, professional case study narrative.

Style guidelines:
- Write in third person about the brand
- Lead with the business challenge, not the technology
- Use specific numbers and percentages from the metrics
- Include before/after comparisons where data exists
- Keep it concise and scannable (use headers)
- Sound professional but not corporate — Agentway's brand is smart and direct
- If quote entries exist, weave them in naturally
- Calculate improvements where baseline and later metrics exist (e.g., "resolution time dropped from 12 hours to 27 seconds")
- If data is thin, note what sections need more information rather than making things up

Output structure:
1. **Title** — compelling one-liner
2. **Executive Summary** — 2-3 sentences
3. **The Challenge** — what the brand was dealing with before
4. **The Solution** — what Agentway deployed and how
5. **The Results** — metrics-driven outcomes with specific numbers
6. **Key Takeaway** — one memorable insight or quote
7. **[Data Gaps]** — if any sections are thin, note what additional data would strengthen the case study

Do NOT fabricate metrics, quotes, or details. Only use what's provided in the data."""


async def generate_case_study(brand_data: dict, config: AppConfig) -> str:
    """Generate a case study narrative from brand data."""
    if not config.anthropic_api_key:
        return "Error: ANTHROPIC_API_KEY not set. Please configure it to generate case studies."

    prompt = _format_brand_data(brand_data)

    client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
    message = await client.messages.create(
        model=config.generation.model,
        max_tokens=config.generation.max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def generate_case_study_sync(brand_data: dict, config: AppConfig) -> str:
    """Synchronous wrapper for CLI usage."""
    return asyncio.run(generate_case_study(brand_data, config))


def _format_brand_data(brand: dict) -> str:
    """Format brand data into a structured prompt for Claude."""
    lines = []
    lines.append(f"# Brand: {brand['name']}")
    if brand.get("industry"):
        lines.append(f"Industry: {brand['industry']}")
    if brand.get("onboarded_at"):
        lines.append(f"Onboarded: {brand['onboarded_at']}")
    if brand.get("notes"):
        lines.append(f"Context: {brand['notes']}")
    lines.append("")

    # Snapshots with metrics
    snapshots = brand.get("snapshots", [])
    if snapshots:
        # Show chronologically (oldest first) for narrative flow
        for snap in reversed(snapshots):
            lines.append(f"## Snapshot: {snap['label']} ({snap['snapshot_date']})")
            if snap.get("notes"):
                lines.append(f"Notes: {snap['notes']}")

            metrics = snap.get("metrics", [])
            if metrics:
                lines.append("\nMetrics:")
                current_category = ""
                for m in metrics:
                    if m["category"] != current_category:
                        current_category = m["category"]
                        if current_category:
                            lines.append(f"\n  [{current_category}]")
                    val = m["value"]
                    if m.get("unit"):
                        val += f" {m['unit']}"
                    change = ""
                    if m.get("change_pct"):
                        change = f" ({m['change_pct']}"
                        if m.get("change_vs"):
                            change += f" vs {m['change_vs']}"
                        change += ")"
                    lines.append(f"  - {m['name']}: {val}{change}")

            screenshots = snap.get("screenshots", [])
            if screenshots:
                lines.append(f"\n  [{len(screenshots)} screenshot(s) attached]")
            lines.append("")
    else:
        lines.append("No metric snapshots recorded yet.\n")

    # Text entries
    entries = brand.get("entries", [])
    if entries:
        lines.append("## Text Entries & Observations")
        for entry in entries:
            cat = f"[{entry['category']}] " if entry.get("category") else ""
            source = f" — {entry['source']}" if entry.get("source") else ""
            lines.append(f"- {cat}{entry['content']}{source} ({entry['entry_date']})")
        lines.append("")

    if not snapshots and not entries:
        lines.append("Very little data collected so far. Please list what information would be most valuable to collect for a compelling case study.")

    lines.append("Generate a case study from this data. If data is insufficient for any section, clearly note what's missing.")
    return "\n".join(lines)
