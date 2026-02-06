#!/usr/bin/env python3
"""
Revenue Estimator

Uses Gemini with Google Search grounding to estimate company revenue from public sources.

Searches for:
- SEC filings and audited financials
- CEO/CFO interviews and analyst reports
- Industry publications and trade journals
- Data aggregators (Growjo, ZoomInfo, etc.)

Usage:
    python revenue.py --domain example.com --company-name "Example Corp"
    python revenue.py --domain example.com --output results.json

Requirements:
    pip install google-genai

Environment:
    GEMINI_API_KEY - Your Google AI Studio API key

Author: Built with Claude Code
License: MIT
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime
from typing import Dict, Any

from google import genai
from google.genai import types


# =============================================================================
# Configuration
# =============================================================================

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set")
    print("Get your API key at: https://aistudio.google.com/app/apikey")
    sys.exit(1)

GEMINI_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """You are a financial research analyst specializing in private company revenue estimation.

TASK: Research annual revenue for the company I provide. Use Google Search to find current data.

RESEARCH INSTRUCTIONS:
1. Search for the company's most recent annual revenue figures.
2. Prioritize sources in this order:
   - Tier 1 (90-100 credibility): SEC filings, audited financials, official company reports
   - Tier 2 (70-89): CEO/CFO interviews, analyst reports, verified funding announcements
   - Tier 3 (50-69): Industry publications, trade journals, financial news outlets
   - Tier 4 (30-49): Data aggregators (Growjo, RocketReach, ZoomInfo, Owler, LeadIQ, Zippia)

3. For EACH revenue estimate found, record:
   - Amount in millions (number)
   - Display format (e.g., "$27.9M")
   - Source name
   - Source URL
   - Source tier (1-4)
   - Credibility score (0-100)
   - Year of the data

4. Detect company ownership:
   - public: Publicly traded company
   - private: Privately held company
   - subsidiary_public: Subsidiary of a public company
   - subsidiary_private: Subsidiary of a private company
   - unknown: Cannot determine

5. CRITICAL RULES:
   - For subsidiaries: Report SUBSIDIARY revenue, NOT parent company total
   - Report what you find, even if sources conflict
   - Find employee count if available

6. Red flags to note:
   - all_aggregators: Only Tier 4 sources found
   - high_variance: Sources differ by >3x
   - stale_data: Most recent data is >3 years old
   - parent_revenue_only: Could only find parent company revenue
   - single_source: Only one source found

IMPORTANT: Return ONLY valid JSON (no markdown, no code blocks) matching this structure:
{
  "company_name": "string",
  "domain": "string",
  "revenue_estimates": [
    {
      "amount_millions": 27.9,
      "amount_display": "$27.9M",
      "source_name": "Growjo",
      "source_url": "https://...",
      "source_tier": 4,
      "credibility_score": 45,
      "year": 2025,
      "notes": ""
    }
  ],
  "employee_count": {"count": 175, "source": "RocketReach", "year": 2025},
  "ownership": {
    "type": "private",
    "parent_company_name": "",
    "parent_ticker": ""
  },
  "company_context": "2-3 sentence company summary",
  "research_quality": {
    "sources_found": 3,
    "highest_tier_found": 4,
    "red_flags": []
  }
}

Return ONLY the JSON object, nothing else.
"""


# =============================================================================
# Gemini Client
# =============================================================================

def create_client() -> genai.Client:
    """Create Gemini API client."""
    return genai.Client(api_key=GEMINI_API_KEY)


def extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from Gemini response."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try markdown code block
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

    return {
        "parse_error": True,
        "raw_text": text[:2000],
        "revenue_estimates": [],
        "ownership": {"type": "unknown"},
        "research_quality": {"sources_found": 0, "red_flags": ["json_parse_error"]}
    }


def research_revenue(client: genai.Client, domain: str, company_name: str) -> Dict[str, Any]:
    """Research company revenue using Gemini with Google Search."""

    user_prompt = f"Research annual revenue for: {company_name} (domain: {domain})"

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2
        )
    )

    result = extract_json(response.text)

    if "domain" not in result:
        result["domain"] = domain
    if "company_name" not in result:
        result["company_name"] = company_name

    return result


# =============================================================================
# Confidence Scoring
# =============================================================================

def calculate_confidence(data: Dict[str, Any]) -> str:
    """Calculate confidence level based on source quality."""

    estimates = data.get("revenue_estimates", [])
    quality = data.get("research_quality", {})

    if not estimates:
        return "INSUFFICIENT"

    best_credibility = max(e.get("credibility_score", 0) for e in estimates)
    source_count = len(estimates)

    # Calculate variance
    amounts = [e.get("amount_millions", 0) for e in estimates if e.get("amount_millions", 0) > 0]
    if len(amounts) >= 2:
        variance_pct = (max(amounts) - min(amounts)) / (sum(amounts) / len(amounts)) * 100
    else:
        variance_pct = 0

    red_flags = quality.get("red_flags", [])
    has_high_variance = variance_pct > 300 or "high_variance" in red_flags
    has_stale_data = "stale_data" in red_flags

    # 5-tier confidence
    if best_credibility >= 80 and source_count >= 2 and variance_pct <= 20:
        confidence = "HIGH"
    elif best_credibility >= 70 and source_count >= 2 and variance_pct <= 40:
        confidence = "MODERATE-HIGH"
    elif best_credibility >= 80 and source_count == 1:
        confidence = "MODERATE-HIGH"
    elif best_credibility >= 50 and source_count >= 2:
        confidence = "MODERATE"
    elif best_credibility >= 60 and source_count == 1:
        confidence = "MODERATE"
    else:
        confidence = "LOW"

    if has_high_variance and confidence in ["HIGH", "MODERATE-HIGH"]:
        confidence = "MODERATE"
    if has_stale_data and confidence != "INSUFFICIENT":
        levels = ["INSUFFICIENT", "LOW", "MODERATE", "MODERATE-HIGH", "HIGH"]
        idx = levels.index(confidence)
        confidence = levels[max(0, idx - 1)]

    return confidence


# =============================================================================
# Output Formatting
# =============================================================================

def format_text_report(data: Dict[str, Any], confidence: str) -> str:
    """Format results as human-readable text."""

    lines = []
    lines.append("=" * 70)
    lines.append(f"REVENUE ESTIMATE REPORT: {data.get('company_name', 'Unknown')}")
    lines.append(f"Domain: {data.get('domain', 'Unknown')}")
    lines.append(f"Collected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    # Company Context
    if data.get("company_context"):
        lines.append(f"\n## COMPANY OVERVIEW\n")
        lines.append(data["company_context"])

    # Ownership
    ownership = data.get("ownership", {})
    if ownership:
        lines.append(f"\n## OWNERSHIP\n")
        lines.append(f"  Type: {ownership.get('type', 'unknown').replace('_', ' ').title()}")
        if ownership.get("parent_company_name"):
            lines.append(f"  Parent: {ownership['parent_company_name']}")
            if ownership.get("parent_ticker"):
                lines.append(f"  Ticker: {ownership['parent_ticker']}")

    # Revenue Estimates
    estimates = data.get("revenue_estimates", [])
    if estimates:
        lines.append(f"\n## REVENUE ESTIMATES ({len(estimates)} sources)\n")
        sorted_est = sorted(estimates, key=lambda x: x.get("credibility_score", 0), reverse=True)
        for i, e in enumerate(sorted_est, 1):
            lines.append(f"  [{i}] {e.get('amount_display', 'N/A')} — {e.get('source_name', 'Unknown')}")
            lines.append(f"      Credibility: {e.get('credibility_score', 0)}/100 (Tier {e.get('source_tier', '?')})")
            lines.append(f"      Year: {e.get('year', 'Unknown')}")
            if e.get("source_url"):
                lines.append(f"      URL: {e['source_url'][:60]}...")
            lines.append("")
    else:
        lines.append(f"\n## REVENUE ESTIMATES\n")
        lines.append("  No reliable revenue data found")

    # Employee Count
    employee = data.get("employee_count", {})
    if employee and employee.get("count"):
        lines.append(f"\n## EMPLOYEE COUNT\n")
        lines.append(f"  {employee['count']} employees ({employee.get('source', 'Unknown')}, {employee.get('year', '')})")

    # Research Quality
    quality = data.get("research_quality", {})
    lines.append(f"\n## RESEARCH QUALITY\n")
    lines.append(f"  Sources found: {quality.get('sources_found', 0)}")
    lines.append(f"  Highest tier: {quality.get('highest_tier_found', 'N/A')}")
    lines.append(f"  Confidence: {confidence}")

    red_flags = quality.get("red_flags", [])
    if red_flags:
        lines.append(f"  Red flags: {', '.join(red_flags)}")

    # Recommendation
    lines.append(f"\n## RECOMMENDATION\n")
    if estimates:
        best = max(estimates, key=lambda x: x.get("credibility_score", 0))
        lines.append(f"  Use {best.get('amount_display')} from {best.get('source_name')}")
        lines.append(f"  Confidence: {confidence}")
    else:
        lines.append(f"  No reliable data available")

    lines.append("\n" + "=" * 70)

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Estimate company revenue using Gemini + Google Search"
    )
    parser.add_argument("--domain", required=True, help="Company domain")
    parser.add_argument("--company-name", help="Company name (inferred if not provided)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--format", "-f", choices=["json", "text", "both"], default="json")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    domain = args.domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
    company_name = args.company_name or domain.split('.')[0].title()

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"Revenue Estimator — {domain}")
        print(f"{'='*60}")
        print(f"\n[1/2] Researching revenue via Gemini...")

    client = create_client()

    try:
        data = research_revenue(client, domain, company_name)
        estimates = data.get("revenue_estimates", [])

        if not args.quiet:
            print(f"      Found {len(estimates)} revenue estimates")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not args.quiet:
        print(f"[2/2] Calculating confidence...")

    confidence = calculate_confidence(data)

    if not args.quiet:
        print(f"      Confidence: {confidence}")

    # Add metadata
    data["_metadata"] = {
        "collected_at": datetime.now().isoformat(),
        "confidence": confidence,
        "model": GEMINI_MODEL
    }

    # Format outputs
    text_output = format_text_report(data, confidence)
    json_output = json.dumps(data, indent=2)

    # Output
    if args.output:
        base = args.output.rsplit(".", 1)[0] if "." in args.output else args.output

        if args.format in ["json", "both"]:
            with open(f"{base}.json", "w") as f:
                f.write(json_output)
            if not args.quiet:
                print(f"\n✅ JSON saved to {base}.json")

        if args.format in ["text", "both"]:
            with open(f"{base}.txt", "w") as f:
                f.write(text_output)
            if not args.quiet:
                print(f"✅ Text saved to {base}.txt")
    else:
        if args.format == "json":
            print(json_output)
        elif args.format == "text":
            print(text_output)
        else:
            print(text_output)
            print("\n--- JSON ---\n")
            print(json_output)

    if not args.quiet and estimates:
        best = max(estimates, key=lambda x: x.get("credibility_score", 0))
        print(f"\n{'='*60}")
        print(f"Best estimate: {best.get('amount_display')} ({best.get('source_name')})")
        print(f"Confidence: {confidence}")
        print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
