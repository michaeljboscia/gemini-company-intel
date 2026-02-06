#!/usr/bin/env python3
"""
Company Intelligence Discovery

Uses Gemini with Google Search grounding to collect public intelligence about companies:
- Executive quotes and interviews
- YouTube videos and podcasts
- Press releases and news
- Acquisitions and ownership changes
- Strategic priorities

Usage:
    python discovery.py --domain example.com --company-name "Example Inc"
    python discovery.py --domain example.com --output results.json

Requirements:
    pip install google-genai

Environment:
    GEMINI_API_KEY - Your Google AI Studio API key

Author: Binary Anvil
License: MIT
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types

# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set")
    print("Get your API key at: https://aistudio.google.com/app/apikey")
    sys.exit(1)

GEMINI_MODEL = "gemini-2.0-flash"

# Strategic themes to look for
RELEVANT_THEMES = [
    "mobile_commerce",
    "customer_experience",
    "digital_transformation",
    "site_performance",
    "ecommerce_platform",
    "international_expansion",
    "personalization",
    "conversion_optimization",
    "technology_modernization",
    "headless_commerce",
    "omnichannel",
    "sustainability",
    "ai_ml_adoption"
]

# =============================================================================
# PROMPTS
# =============================================================================

DISCOVERY_PROMPT = """Search for public statements, interviews, and media appearances about {company_name} ({domain}).

Find information from these sources (prioritize in this order):
1. YouTube videos - company channel, executive interviews, product demos, webinars
2. Podcast appearances - executives or founders on business/industry podcasts
3. Press releases and company announcements
4. Executive interviews in trade publications or business media
5. Conference talks, keynotes, or panel discussions
6. Partnership and product announcements
7. SEC filings or annual reports (if public company)
8. News articles about strategic moves, funding, or growth

IMPORTANT - Also search for ownership changes:
- Has this company been acquired, merged, or received PE/VC investment?
- If so, who acquired them and when?
- What is the acquirer's domain/website?
- Any statements from either party about the acquisition?

For YouTube and podcast content, note the episode/video title and key quotes.

Return your findings as JSON in this exact format:
```json
{{
  "company_name": "{company_name}",
  "domain": "{domain}",
  "strategic_statements": [
    {{
      "statement": "The exact quote or statement",
      "speaker": "Name if known, otherwise null",
      "speaker_title": "Their title if known",
      "source_name": "Publication, podcast name, or YouTube channel",
      "source_type": "youtube|podcast|press_release|interview|news|sec_filing|conference",
      "source_url": "URL if available",
      "date": "YYYY-MM-DD if known",
      "strategic_themes": ["theme1", "theme2"],
      "outreach_relevance": 85,
      "outreach_angle": "Why this matters for B2B outreach"
    }}
  ],
  "company_priorities": ["priority1", "priority2", "priority3"],
  "key_executives": [
    {{
      "name": "Name",
      "title": "Title",
      "notable_quote": "Their best quote if found"
    }}
  ],
  "ownership_changes": [
    {{
      "event_type": "acquisition|merger|pe_investment|vc_funding|ipo|spin_off",
      "counterparty_name": "Name of acquirer, investor, or merged company",
      "counterparty_domain": "Their website domain if known",
      "date": "YYYY-MM-DD",
      "amount": "Deal value if disclosed",
      "details": "Brief description of the transaction"
    }}
  ],
  "company_context": "2-3 sentence company summary",
  "collection_notes": "Notes about data availability"
}}
```

Strategic themes to look for: {themes}

Return ONLY the JSON object."""


ACQUIRER_PROMPT = """Search for strategic intelligence about {acquirer_name} ({acquirer_domain}).

Focus on:
1. Their acquisition strategy - what other companies have they acquired?
2. Leadership team and their statements about growth/acquisition philosophy
3. Post-acquisition integration approach - how do they manage acquired companies?
4. Any public statements about their acquisition of {acquired_company} ({acquisition_date})
5. News and developments since the acquisition date ({acquisition_date} to present)

Return your findings as JSON:
```json
{{
  "acquirer_name": "{acquirer_name}",
  "acquirer_domain": "{acquirer_domain}",
  "key_executives": [
    {{"name": "Name", "title": "Title", "notable_quote": "Quote about strategy"}}
  ],
  "acquisition_philosophy": "Their stated approach to acquisitions",
  "other_acquisitions": [
    {{"company": "Name", "date": "YYYY-MM-DD", "details": "Brief"}}
  ],
  "post_acquisition_statements": [
    {{"statement": "Quote about {acquired_company}", "speaker": "Name", "date": "YYYY-MM-DD"}}
  ],
  "recent_developments": [
    {{"date": "YYYY-MM-DD", "headline": "Brief description", "relevance": "Why this matters"}}
  ],
  "strategic_priorities": ["priority1", "priority2"],
  "outreach_implications": "How this affects outreach to the acquired company"
}}
```

Return ONLY the JSON object."""


# =============================================================================
# GEMINI CLIENT
# =============================================================================

def create_client():
    """Initialize Gemini client."""
    return genai.Client(api_key=GEMINI_API_KEY)


def extract_json(text: str) -> dict:
    """Extract JSON from Gemini's response."""
    # Try code blocks first
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try raw JSON
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"error": "JSON parsing failed", "raw_response": text[:500]}


# =============================================================================
# INTELLIGENCE COLLECTION
# =============================================================================

def collect_company_intel(client, domain: str, company_name: str) -> dict:
    """Collect strategic intelligence about a company."""

    prompt = DISCOVERY_PROMPT.format(
        company_name=company_name,
        domain=domain,
        themes=", ".join(RELEVANT_THEMES)
    )

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        return extract_json(response.text)

    except Exception as e:
        return {
            "error": str(e),
            "strategic_statements": [],
            "company_priorities": [],
            "key_executives": [],
            "ownership_changes": [],
            "company_context": "",
            "collection_notes": f"API error: {e}"
        }


def collect_acquirer_intel(client, acquirer_name: str, acquirer_domain: str,
                           acquired_company: str, acquisition_date: str) -> dict:
    """Collect intelligence about an acquiring company."""

    prompt = ACQUIRER_PROMPT.format(
        acquirer_name=acquirer_name,
        acquirer_domain=acquirer_domain or "unknown",
        acquired_company=acquired_company,
        acquisition_date=acquisition_date or "unknown date"
    )

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        return extract_json(response.text)

    except Exception as e:
        return {"error": str(e)}


def process_acquisitions(client, intel: dict, company_name: str) -> Optional[dict]:
    """Detect acquisitions and collect acquirer intelligence."""

    ownership_changes = intel.get("ownership_changes", [])
    if not ownership_changes:
        return None

    # Find acquisitions
    acquisitions = [
        oc for oc in ownership_changes
        if oc.get("event_type") in ["acquisition", "merger", "pe_investment"]
    ]

    if not acquisitions:
        return None

    primary = acquisitions[0]
    acquirer_name = primary.get("counterparty_name", "")

    if not acquirer_name:
        return {"detected": True, "acquirer_intel": None, "note": "Acquirer name not found"}

    print(f"\n[ACQUISITION DETECTED] {company_name} acquired by {acquirer_name}")
    print(f"    Date: {primary.get('date', 'Unknown')}")
    print(f"    Running secondary collection on acquirer...")

    acquirer_intel = collect_acquirer_intel(
        client=client,
        acquirer_name=acquirer_name,
        acquirer_domain=primary.get("counterparty_domain", ""),
        acquired_company=company_name,
        acquisition_date=primary.get("date", "")
    )

    return {
        "detected": True,
        "acquirer_name": acquirer_name,
        "acquirer_domain": primary.get("counterparty_domain"),
        "acquisition_date": primary.get("date"),
        "details": primary.get("details"),
        "acquirer_intel": acquirer_intel
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Collect strategic intelligence about a company using Gemini + Google Search"
    )
    parser.add_argument("--domain", required=True, help="Company domain (e.g., example.com)")
    parser.add_argument("--company-name", help="Company name (inferred from domain if not provided)")
    parser.add_argument("--output", "-o", help="Output file (extension determines format, or use --format)")
    parser.add_argument("--format", "-f", choices=["json", "text", "both"], default="json", help="Output format")
    parser.add_argument("--no-acquirer", action="store_true", help="Skip acquirer intelligence collection")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    # Normalize domain
    domain = args.domain.lower()
    domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
    company_name = args.company_name or domain.split(".")[0].title()

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"Company Intelligence Discovery — {domain}")
        print(f"{'='*60}")

    start_time = time.time()

    # Collect company intelligence
    if not args.quiet:
        print(f"\n[1/2] Collecting company intelligence...")

    client = create_client()
    intel = collect_company_intel(client, domain, company_name)

    statement_count = len(intel.get("strategic_statements", []))
    exec_count = len(intel.get("key_executives", []))

    if not args.quiet:
        print(f"    Found {statement_count} strategic statements")
        print(f"    Found {exec_count} executives")

    # Check for acquisitions
    acquisition_info = None
    if not args.no_acquirer:
        if not args.quiet:
            print(f"\n[2/2] Checking for acquisitions...")
        acquisition_info = process_acquisitions(client, intel, company_name)

        if acquisition_info and acquisition_info.get("detected"):
            intel["acquisition_info"] = acquisition_info
            if not args.quiet and acquisition_info.get("acquirer_intel"):
                acq = acquisition_info["acquirer_intel"]
                print(f"    Acquirer executives: {len(acq.get('key_executives', []))}")
                print(f"    Other acquisitions: {len(acq.get('other_acquisitions', []))}")
        elif not args.quiet:
            print(f"    No acquisitions detected")

    # Add metadata
    intel["_metadata"] = {
        "collected_at": datetime.now().isoformat(),
        "domain": domain,
        "company_name": company_name,
        "collection_time_seconds": round(time.time() - start_time, 1)
    }

    # Format output
    elapsed = time.time() - start_time

    def format_text(intel: dict) -> str:
        """Format intelligence as readable text."""
        lines = []
        lines.append(f"{'='*70}")
        lines.append(f"COMPANY INTELLIGENCE REPORT: {intel.get('company_name', domain)}")
        lines.append(f"Domain: {domain}")
        lines.append(f"Collected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"{'='*70}")

        # Company Context
        if intel.get("company_context"):
            lines.append(f"\n## COMPANY OVERVIEW\n")
            lines.append(intel["company_context"])

        # Key Executives
        execs = intel.get("key_executives", [])
        if execs:
            lines.append(f"\n## KEY EXECUTIVES ({len(execs)})\n")
            for ex in execs:
                lines.append(f"  • {ex.get('name', 'Unknown')} — {ex.get('title', 'Unknown title')}")
                if ex.get("notable_quote"):
                    lines.append(f"    \"{ex['notable_quote'][:100]}...\"")

        # Company Priorities
        priorities = intel.get("company_priorities", [])
        if priorities:
            lines.append(f"\n## STRATEGIC PRIORITIES ({len(priorities)})\n")
            for i, p in enumerate(priorities, 1):
                lines.append(f"  {i}. {p}")

        # Ownership Changes
        changes = intel.get("ownership_changes", [])
        if changes:
            lines.append(f"\n## OWNERSHIP CHANGES ({len(changes)})\n")
            for ch in changes:
                date = ch.get("date", "Unknown date")
                event = ch.get("event_type", "unknown").replace("_", " ").title()
                counterparty = ch.get("counterparty_name", "Unknown")
                lines.append(f"  • [{date}] {event}: {counterparty}")
                if ch.get("details"):
                    lines.append(f"    {ch['details'][:100]}")

        # Acquirer Intelligence
        acq_info = intel.get("acquisition_info")
        if acq_info and acq_info.get("acquirer_intel"):
            acq = acq_info["acquirer_intel"]
            lines.append(f"\n## ACQUIRER INTELLIGENCE: {acq_info.get('acquirer_name')}\n")

            if acq.get("acquisition_philosophy"):
                lines.append(f"  Philosophy: {acq['acquisition_philosophy'][:150]}...")

            other_acq = acq.get("other_acquisitions", [])
            if other_acq:
                lines.append(f"\n  Other acquisitions by this company ({len(other_acq)}):")
                for oa in other_acq[:5]:
                    lines.append(f"    • {oa.get('company', 'Unknown')} ({oa.get('date', 'Unknown')})")

            acq_execs = acq.get("key_executives", [])
            if acq_execs:
                lines.append(f"\n  Acquirer executives:")
                for ex in acq_execs[:3]:
                    lines.append(f"    • {ex.get('name', 'Unknown')} — {ex.get('title', '')}")

        # Strategic Statements
        statements = intel.get("strategic_statements", [])
        if statements:
            lines.append(f"\n## STRATEGIC STATEMENTS ({len(statements)})\n")
            sorted_stmts = sorted(statements, key=lambda x: x.get("outreach_relevance", 0), reverse=True)
            for i, st in enumerate(sorted_stmts[:10], 1):
                speaker = st.get("speaker") or "Unknown"
                title = st.get("speaker_title") or ""
                source = st.get("source_name", "Unknown source")
                stype = st.get("source_type", "")
                relevance = st.get("outreach_relevance", 0)

                lines.append(f"  [{i}] Relevance: {relevance}/100 | Source: {source} ({stype})")
                if speaker != "Unknown":
                    lines.append(f"      Speaker: {speaker}, {title}")
                lines.append(f"      \"{st.get('statement', '')[:200]}\"")
                if st.get("outreach_angle"):
                    lines.append(f"      → Outreach angle: {st['outreach_angle'][:100]}")
                lines.append("")

        # Footer
        lines.append(f"{'='*70}")
        lines.append(f"Collection completed in {elapsed:.1f} seconds")
        lines.append(f"{'='*70}")

        return "\n".join(lines)

    # Output based on format
    text_output = format_text(intel)
    json_output = json.dumps(intel, indent=2)

    if args.output:
        base_name = args.output.rsplit(".", 1)[0] if "." in args.output else args.output

        if args.format == "json":
            with open(f"{base_name}.json", "w") as f:
                f.write(json_output)
            if not args.quiet:
                print(f"\n✅ JSON saved to {base_name}.json")

        elif args.format == "text":
            with open(f"{base_name}.txt", "w") as f:
                f.write(text_output)
            if not args.quiet:
                print(f"\n✅ Text saved to {base_name}.txt")

        elif args.format == "both":
            with open(f"{base_name}.json", "w") as f:
                f.write(json_output)
            with open(f"{base_name}.txt", "w") as f:
                f.write(text_output)
            if not args.quiet:
                print(f"\n✅ Saved to {base_name}.json and {base_name}.txt")

    else:
        # Print to stdout
        if args.format == "json":
            print(json_output)
        elif args.format == "text":
            print(text_output)
        elif args.format == "both":
            print(text_output)
            print("\n--- JSON ---\n")
            print(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
