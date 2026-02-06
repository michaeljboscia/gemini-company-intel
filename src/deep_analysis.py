#!/usr/bin/env python3
"""
Deep Analysis Pipeline

Takes discovery results and performs deep content analysis on high-relevance
sources using Gemini's native YouTube and document understanding.

Architecture:
  Stage 1 (discovery.py): Fast discovery via Gemini + Google Search → finds URLs + snippets
  Stage 2 (deep_analysis.py): Full content analysis of YouTube, podcasts, articles

Usage:
    # Process a YouTube video directly
    python deep_analysis.py --youtube-url "https://youtube.com/watch?v=XXX" --company-name "Example Corp"

    # Process discovery results JSON file
    python deep_analysis.py --input discovery_results.json

    # Process with custom output
    python deep_analysis.py --youtube-url "URL" --output results.json

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
from typing import Dict, List, Any, Optional

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

# Minimum relevance score to process in Stage 2
MIN_RELEVANCE_THRESHOLD = 80


# =============================================================================
# Gemini Client
# =============================================================================

def create_client() -> genai.Client:
    """Create Gemini API client."""
    return genai.Client(api_key=GEMINI_API_KEY)


# =============================================================================
# YouTube Deep Processing
# =============================================================================

YOUTUBE_STRATEGIC_PROMPT = """Analyze this video for strategic business intelligence.

Extract:
1. **Executive Statements**: Any quotes from CEO, founders, or executives about:
   - Business strategy and priorities
   - Future plans and expansion
   - Technology investments
   - Competitive positioning
   - Company culture and values

2. **Business Intelligence**:
   - Recent acquisitions, mergers, or PE involvement
   - Revenue/growth indicators mentioned
   - Key partnerships announced
   - Market positioning statements
   - Challenges or pain points discussed

3. **Outreach Angles**: What pain points or priorities does this reveal that could be relevant for B2B outreach?

IMPORTANT: Return ONLY valid JSON (no markdown, no code blocks) matching this structure:
{
  "executives_found": [
    {"name": "Name", "title": "Title", "key_quotes": ["quote1", "quote2"]}
  ],
  "strategic_insights": [
    {"topic": "expansion", "detail": "Planning 10 new stores", "confidence": "high"}
  ],
  "business_events": [
    {"event": "PE acquisition", "detail": "Acquired by Z Capital in 2023", "date": "2023"}
  ],
  "pain_points": ["inventory management", "scaling technology"],
  "outreach_angles": [
    {"angle": "Their tech stack needs modernizing", "evidence": "Quote about legacy systems"}
  ],
  "video_summary": "2-3 sentence executive summary"
}

Return ONLY the JSON object, nothing else.
"""


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
        "executives_found": [],
        "strategic_insights": []
    }


def process_youtube(client: genai.Client, url: str, company_name: str = "") -> Dict[str, Any]:
    """Process a YouTube video for deep strategic intelligence using Gemini's native video understanding."""

    print(f"      Processing YouTube: {url[:60]}...")

    try:
        # Use Gemini's native YouTube understanding
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=YOUTUBE_STRATEGIC_PROMPT),
                        types.Part(
                            file_data=types.FileData(
                                file_uri=url,
                                mime_type="video/*"
                            )
                        )
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=4000
            )
        )

        result = extract_json(response.text)
        result["source_url"] = url
        result["source_type"] = "youtube"

        return result

    except Exception as e:
        print(f"      YouTube processing error: {e}")
        return {
            "error": str(e),
            "source_url": url,
            "source_type": "youtube"
        }


# =============================================================================
# Article/News Deep Processing
# =============================================================================

NEWS_STRATEGIC_PROMPT = """Analyze this news article or press release for strategic business intelligence about {company_name}.

Extract:
1. Key announcements or news
2. Executive quotes (with attribution)
3. Strategic implications
4. Any metrics or numbers mentioned
5. Competitive context

IMPORTANT: Return ONLY valid JSON (no markdown, no code blocks) matching this structure:
{{
  "headline_summary": "One sentence summary",
  "key_announcements": ["announcement1", "announcement2"],
  "executive_quotes": [
    {{"speaker": "Name", "title": "Title", "quote": "The quote"}}
  ],
  "metrics_mentioned": [{{"metric": "revenue", "value": "$50M", "context": "annual"}}],
  "strategic_implications": ["implication1", "implication2"],
  "outreach_relevance": 85
}}

Return ONLY the JSON object, nothing else.
"""


def process_article(client: genai.Client, url: str, company_name: str) -> Dict[str, Any]:
    """Process a news article or press release for strategic intel."""

    print(f"      Processing article: {url[:50]}...")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=NEWS_STRATEGIC_PROMPT.format(company_name=company_name) + f"\n\nURL: {url}",
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2000,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

        result = extract_json(response.text)
        result["source_url"] = url
        result["source_type"] = "article"

        return result

    except Exception as e:
        print(f"      Article processing error: {e}")
        return {
            "error": str(e),
            "source_url": url,
            "source_type": "article"
        }


# =============================================================================
# Discovery Results Processing
# =============================================================================

def load_discovery_results(filepath: str) -> Dict[str, Any]:
    """Load Stage 1 discovery results from JSON file."""

    with open(filepath, 'r') as f:
        return json.load(f)


def get_high_relevance_sources(discovery_data: Dict[str, Any], threshold: int = MIN_RELEVANCE_THRESHOLD) -> List[Dict]:
    """Extract high-relevance sources from discovery results."""

    sources = []
    statements = discovery_data.get("strategic_statements", [])

    for stmt in statements:
        relevance = stmt.get("outreach_relevance", 0)
        source_url = stmt.get("source_url", "")
        source_type = stmt.get("source_type", "")

        if relevance >= threshold and source_url:
            sources.append({
                "url": source_url,
                "type": source_type,
                "relevance": relevance,
                "source_name": stmt.get("source_name", ""),
                "snippet": stmt.get("statement", "")[:200]
            })

    return sources


# =============================================================================
# Results Merging
# =============================================================================

def merge_deep_intel(company_name: str, domain: str, youtube_results: List[Dict], article_results: List[Dict]) -> Dict[str, Any]:
    """Merge all deep processing results into unified intel."""

    merged = {
        "company_name": company_name,
        "domain": domain,
        "processed_at": datetime.now().isoformat(),
        "youtube_intel": youtube_results,
        "article_intel": article_results,
        "executives_found": [],
        "strategic_insights": [],
        "outreach_angles": [],
        "key_quotes": [],
        "pain_points": []
    }

    # Extract from YouTube results
    for yt in youtube_results:
        if "executives_found" in yt:
            merged["executives_found"].extend(yt["executives_found"])
        if "strategic_insights" in yt:
            merged["strategic_insights"].extend(yt["strategic_insights"])
        if "outreach_angles" in yt:
            merged["outreach_angles"].extend(yt["outreach_angles"])
        if "pain_points" in yt:
            merged["pain_points"].extend(yt["pain_points"])

    # Extract quotes from articles
    for art in article_results:
        if "executive_quotes" in art:
            merged["key_quotes"].extend(art["executive_quotes"])

    # Deduplicate pain points
    merged["pain_points"] = list(set(merged["pain_points"]))

    return merged


# =============================================================================
# Output Formatting
# =============================================================================

def format_text_report(data: Dict[str, Any]) -> str:
    """Format deep analysis results as human-readable text."""

    lines = []
    lines.append("=" * 70)
    lines.append(f"DEEP ANALYSIS REPORT: {data.get('company_name', 'Unknown')}")
    lines.append(f"Domain: {data.get('domain', 'Unknown')}")
    lines.append(f"Processed: {data.get('processed_at', datetime.now().isoformat())}")
    lines.append("=" * 70)

    # Executives Found
    executives = data.get("executives_found", [])
    if executives:
        lines.append(f"\n## EXECUTIVES FOUND ({len(executives)})\n")
        for exec in executives:
            lines.append(f"  • {exec.get('name', 'Unknown')} — {exec.get('title', 'Unknown')}")
            quotes = exec.get("key_quotes", [])
            for q in quotes[:2]:  # Show first 2 quotes
                lines.append(f"    \"{q[:100]}...\"" if len(q) > 100 else f"    \"{q}\"")
            lines.append("")
    else:
        lines.append("\n## EXECUTIVES FOUND\n")
        lines.append("  No executives identified")

    # Strategic Insights
    insights = data.get("strategic_insights", [])
    if insights:
        lines.append(f"\n## STRATEGIC INSIGHTS ({len(insights)})\n")
        for i, ins in enumerate(insights, 1):
            topic = ins.get("topic", "general")
            detail = ins.get("detail", "")
            confidence = ins.get("confidence", "medium")
            lines.append(f"  [{i}] {topic.upper()} ({confidence})")
            lines.append(f"      {detail}")
            lines.append("")
    else:
        lines.append("\n## STRATEGIC INSIGHTS\n")
        lines.append("  No strategic insights extracted")

    # Pain Points
    pain_points = data.get("pain_points", [])
    if pain_points:
        lines.append(f"\n## PAIN POINTS IDENTIFIED ({len(pain_points)})\n")
        for pp in pain_points:
            lines.append(f"  • {pp}")
    else:
        lines.append("\n## PAIN POINTS IDENTIFIED\n")
        lines.append("  None identified")

    # Outreach Angles
    angles = data.get("outreach_angles", [])
    if angles:
        lines.append(f"\n## OUTREACH ANGLES ({len(angles)})\n")
        for i, angle in enumerate(angles, 1):
            lines.append(f"  [{i}] {angle.get('angle', '')}")
            if angle.get("evidence"):
                lines.append(f"      Evidence: {angle['evidence'][:100]}...")
            lines.append("")
    else:
        lines.append("\n## OUTREACH ANGLES\n")
        lines.append("  No specific outreach angles identified")

    # Key Quotes
    quotes = data.get("key_quotes", [])
    if quotes:
        lines.append(f"\n## KEY EXECUTIVE QUOTES ({len(quotes)})\n")
        for q in quotes:
            speaker = q.get("speaker", "Unknown")
            title = q.get("title", "")
            quote = q.get("quote", "")
            lines.append(f"  \"{quote[:150]}...\"" if len(quote) > 150 else f"  \"{quote}\"")
            lines.append(f"    — {speaker}" + (f", {title}" if title else ""))
            lines.append("")

    # Sources Summary
    yt_count = len(data.get("youtube_intel", []))
    art_count = len(data.get("article_intel", []))
    lines.append(f"\n## SOURCES PROCESSED\n")
    lines.append(f"  YouTube videos: {yt_count}")
    lines.append(f"  Articles/News: {art_count}")

    lines.append("\n" + "=" * 70)

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deep content analysis using Gemini"
    )
    parser.add_argument("--youtube-url", help="Process a specific YouTube URL directly")
    parser.add_argument("--article-url", help="Process a specific article URL directly")
    parser.add_argument("--input", "-i", help="Input JSON file from discovery.py")
    parser.add_argument("--company-name", help="Company name for context")
    parser.add_argument("--domain", help="Company domain")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--format", "-f", choices=["json", "text", "both"], default="json")
    parser.add_argument("--threshold", "-t", type=int, default=MIN_RELEVANCE_THRESHOLD,
                        help=f"Minimum relevance score to process (default: {MIN_RELEVANCE_THRESHOLD})")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    if not args.youtube_url and not args.article_url and not args.input:
        parser.error("One of --youtube-url, --article-url, or --input is required")

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"Deep Analysis Pipeline")
        print(f"{'='*60}")

    client = create_client()
    youtube_results = []
    article_results = []

    # Direct YouTube processing
    if args.youtube_url:
        if not args.quiet:
            print(f"\n[1/2] Processing YouTube video...")
        result = process_youtube(client, args.youtube_url, args.company_name or "")
        youtube_results.append(result)

        if not args.quiet:
            print(f"[2/2] Complete!")
            if result.get("executives_found"):
                print(f"      Executives found: {len(result['executives_found'])}")
            if result.get("strategic_insights"):
                print(f"      Strategic insights: {len(result['strategic_insights'])}")

    # Direct article processing
    elif args.article_url:
        if not args.quiet:
            print(f"\n[1/2] Processing article...")
        result = process_article(client, args.article_url, args.company_name or "Unknown")
        article_results.append(result)

        if not args.quiet:
            print(f"[2/2] Complete!")

    # Process discovery results file
    elif args.input:
        if not args.quiet:
            print(f"\n[1/4] Loading discovery results from {args.input}...")

        try:
            discovery_data = load_discovery_results(args.input)
        except Exception as e:
            print(f"Error loading input file: {e}")
            sys.exit(1)

        company_name = args.company_name or discovery_data.get("company_name", "Unknown")
        domain = args.domain or discovery_data.get("domain", "unknown.com")

        sources = get_high_relevance_sources(discovery_data, args.threshold)

        if not sources:
            print(f"      No sources found above {args.threshold}% relevance")
            sys.exit(0)

        if not args.quiet:
            print(f"      Found {len(sources)} sources above {args.threshold}% relevance")

        # Categorize sources
        yt_sources = [s for s in sources if s["type"] == "youtube"]
        art_sources = [s for s in sources if s["type"] in ["news", "press_release", "interview", "article"]]

        if not args.quiet:
            print(f"      YouTube: {len(yt_sources)}, Articles: {len(art_sources)}")

        # Process YouTube
        if yt_sources:
            if not args.quiet:
                print(f"\n[2/4] Deep processing {len(yt_sources)} YouTube sources...")
            for src in yt_sources:
                result = process_youtube(client, src["url"], company_name)
                result["original_relevance"] = src["relevance"]
                result["source_name"] = src.get("source_name", "")
                youtube_results.append(result)
        else:
            if not args.quiet:
                print(f"\n[2/4] No YouTube sources to process")

        # Process articles
        if art_sources:
            if not args.quiet:
                print(f"\n[3/4] Deep processing {len(art_sources)} articles...")
            for src in art_sources[:5]:  # Limit to 5 articles
                result = process_article(client, src["url"], company_name)
                result["original_relevance"] = src["relevance"]
                article_results.append(result)
        else:
            if not args.quiet:
                print(f"\n[3/4] No articles to process")

        if not args.quiet:
            print(f"\n[4/4] Merging results...")

    # Merge all results
    company_name = args.company_name or "Unknown"
    domain = args.domain or "unknown.com"
    deep_intel = merge_deep_intel(company_name, domain, youtube_results, article_results)

    # Add metadata
    deep_intel["_metadata"] = {
        "processed_at": datetime.now().isoformat(),
        "model": GEMINI_MODEL,
        "youtube_count": len(youtube_results),
        "article_count": len(article_results)
    }

    # Format outputs
    text_output = format_text_report(deep_intel)
    json_output = json.dumps(deep_intel, indent=2)

    # Output
    if args.output:
        base = args.output.rsplit(".", 1)[0] if "." in args.output else args.output

        if args.format in ["json", "both"]:
            with open(f"{base}.json", "w") as f:
                f.write(json_output)
            if not args.quiet:
                print(f"\n JSON saved to {base}.json")

        if args.format in ["text", "both"]:
            with open(f"{base}.txt", "w") as f:
                f.write(text_output)
            if not args.quiet:
                print(f" Text saved to {base}.txt")
    else:
        if args.format == "json":
            print(json_output)
        elif args.format == "text":
            print(text_output)
        else:
            print(text_output)
            print("\n--- JSON ---\n")
            print(json_output)

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"Deep Analysis Summary")
        print(f"   Executives found: {len(deep_intel.get('executives_found', []))}")
        print(f"   Strategic insights: {len(deep_intel.get('strategic_insights', []))}")
        print(f"   Pain points: {len(deep_intel.get('pain_points', []))}")
        print(f"   Outreach angles: {len(deep_intel.get('outreach_angles', []))}")
        print(f"   Key quotes: {len(deep_intel.get('key_quotes', []))}")
        print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
