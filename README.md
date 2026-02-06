# Gemini Company Intel

Collect strategic intelligence about any company using Google's Gemini AI with real-time Google Search grounding.

## What's Included

Three standalone tools for B2B intelligence gathering:

| Script | Purpose | Speed |
|--------|---------|-------|
| `discovery.py` | Fast strategic intel: executives, priorities, ownership | 10-20s |
| `revenue.py` | Revenue estimation from public sources | 5-15s |
| `deep_analysis.py` | Full YouTube/article content analysis | 30-60s per source |

## What It Does

**Discovery** (`discovery.py`) — Point it at a domain and get:
- Executive quotes from YouTube, podcasts, interviews
- Strategic priorities extracted from public statements
- Ownership changes (acquisitions, PE investments, mergers)
- Acquirer intelligence — automatically researches the acquiring company if detected
- Outreach angles — suggested talking points for B2B outreach

**Revenue Estimation** (`revenue.py`) — Research annual revenue:
- Searches SEC filings, analyst reports, data aggregators
- 4-tier source credibility scoring (SEC=Tier 1, Growjo=Tier 4)
- Detects public/private/subsidiary ownership
- Calculates confidence levels (HIGH → INSUFFICIENT)

**Deep Analysis** (`deep_analysis.py`) — Full content extraction:
- Processes YouTube videos using Gemini's native video understanding
- Extracts verbatim executive quotes with context
- Identifies strategic insights and pain points
- Generates specific outreach angles with evidence

## Quick Start

```bash
# Clone
git clone https://github.com/michaeljboscia/gemini-company-intel.git
cd gemini-company-intel

# Install
pip install -r requirements.txt

# Set your API key
export GEMINI_API_KEY="your-key-here"  # Get one at https://aistudio.google.com/app/apikey

# Run discovery
python src/discovery.py --domain dunnlumber.com --company-name "Dunn Lumber"

# Run revenue estimation
python src/revenue.py --domain example.com --company-name "Example Corp"

# Analyze a YouTube video
python src/deep_analysis.py --youtube-url "https://youtube.com/watch?v=XXX" --company-name "Example Corp"
```

---

## Discovery Usage

```bash
# Basic usage (JSON to stdout)
python src/discovery.py --domain example.com

# Specify company name
python src/discovery.py --domain example.com --company-name "Example Corp"

# Text output (human-readable report)
python src/discovery.py --domain example.com --format text

# Save to files
python src/discovery.py --domain example.com --output report --format both
# Creates: report.json and report.txt

# Skip acquirer research (faster)
python src/discovery.py --domain example.com --no-acquirer

# Quiet mode (just output, no progress)
python src/discovery.py --domain example.com --quiet
```

### Discovery Output Fields (JSON)

- `strategic_statements[]` — quotes with speaker, source, relevance score
- `key_executives[]` — names, titles, notable quotes
- `company_priorities[]` — identified strategic priorities
- `ownership_changes[]` — acquisitions, mergers, PE investments
- `acquisition_info` — deep intel on acquiring company (if applicable)

---

## Revenue Estimation Usage

```bash
# Basic usage (JSON to stdout)
python src/revenue.py --domain example.com

# Specify company name for better search
python src/revenue.py --domain example.com --company-name "Example Corp"

# Text report format
python src/revenue.py --domain example.com --format text

# Save to files
python src/revenue.py --domain example.com --output results --format both
# Creates: results.json and results.txt

# Quiet mode
python src/revenue.py --domain example.com --quiet
```

### Revenue Output Fields (JSON)

```json
{
  "company_name": "Example Corp",
  "domain": "example.com",
  "revenue_estimates": [
    {
      "amount_millions": 27.9,
      "amount_display": "$27.9M",
      "source_name": "Growjo",
      "source_url": "https://...",
      "source_tier": 4,
      "credibility_score": 45,
      "year": 2025
    }
  ],
  "employee_count": {"count": 175, "source": "RocketReach", "year": 2025},
  "ownership": {
    "type": "private",
    "parent_company_name": "",
    "parent_ticker": ""
  },
  "research_quality": {
    "sources_found": 3,
    "highest_tier_found": 4,
    "red_flags": []
  }
}
```

### Source Tier Reference

| Tier | Credibility | Examples |
|------|------------|----------|
| 1 | 90-100 | SEC filings, audited financials |
| 2 | 70-89 | CEO interviews, analyst reports |
| 3 | 50-69 | Industry publications, trade journals |
| 4 | 30-49 | Growjo, RocketReach, ZoomInfo, Owler |

### Confidence Levels

| Level | Criteria |
|-------|----------|
| HIGH | Best source ≥80 credibility, 2+ sources, ≤20% variance |
| MODERATE-HIGH | Best source ≥70, 2+ sources, ≤40% variance |
| MODERATE | Best source ≥50, 2+ sources |
| LOW | Data found but low quality |
| INSUFFICIENT | No revenue data found |

---

## Deep Analysis Usage

```bash
# Analyze a YouTube video directly
python src/deep_analysis.py --youtube-url "https://youtube.com/watch?v=XXX" --company-name "Example Corp"

# Analyze an article
python src/deep_analysis.py --article-url "https://example.com/news" --company-name "Example Corp"

# Process discovery.py output (analyzes high-relevance sources)
python src/discovery.py --domain example.com --output discovery_results --format json
python src/deep_analysis.py --input discovery_results.json --threshold 80

# Save deep analysis results
python src/deep_analysis.py --youtube-url "URL" --output analysis --format both
```

### Deep Analysis Output Fields (JSON)

```json
{
  "executives_found": [
    {"name": "John Smith", "title": "CEO", "key_quotes": ["quote1", "quote2"]}
  ],
  "strategic_insights": [
    {"topic": "expansion", "detail": "Planning 10 new locations", "confidence": "high"}
  ],
  "pain_points": ["inventory management", "legacy systems"],
  "outreach_angles": [
    {"angle": "Tech modernization opportunity", "evidence": "Quote about legacy systems"}
  ],
  "key_quotes": [
    {"speaker": "Jane Doe", "title": "CFO", "quote": "We're investing heavily in..."}
  ]
}
```

---

## Example Discovery Output

```
======================================================================
COMPANY INTELLIGENCE REPORT: Dunn Lumber
Domain: dunnlumber.com
======================================================================

## COMPANY OVERVIEW

Dunn Lumber is a family-owned building material supplier based in Seattle,
with nine locations. Founded in 1907, acquired by Spahn & Rose Lumber Co. in 2019.

## KEY EXECUTIVES (1)

  • Mike Dunn — CEO

## STRATEGIC PRIORITIES (5)

  1. Customer relationships
  2. Quality materials
  3. Expert advice

## OWNERSHIP CHANGES (1)

  • [2019-02-28] Acquisition: Spahn & Rose Lumber Co.

## ACQUIRER INTELLIGENCE: Spahn & Rose Lumber Co.

  Philosophy: Seeks partners that share their values and corporate culture...

  Other acquisitions by this company (6):
    • Dunn Lumber (2019-02-28)
    • Moeller & Walter Lumber (2020-02)
    • Metro Building Products (2021-08)
    • Still Lumber (2022-08-01)
    • City Lumber Co. (2023-09-12)

## STRATEGIC STATEMENTS (5)

  [1] Relevance: 95/100 | Source: Dunn Lumber's History - YouTube
      "At Dunn Lumber we believe trusting relationships are the key..."
      → Outreach angle: Emphasizes relationship-building...
```

---

## Pipeline: Discovery → Deep Analysis

For comprehensive intelligence, run discovery first, then deep-process the high-relevance sources:

```bash
# Step 1: Fast discovery (10-20 seconds)
python src/discovery.py --domain example.com --output step1_discovery --format json

# Step 2: Deep analysis of YouTube/articles found (30-60s per source)
python src/deep_analysis.py --input step1_discovery.json --output step2_deep --format both

# Result: Full executive quotes, strategic insights, pain points
```

---

## How It Works

1. **Discovery** — Gemini searches Google for public statements, YouTube videos, podcasts, press releases, SEC filings about the company

2. **Extraction** — Parses executive quotes, strategic priorities, ownership changes into structured JSON

3. **Acquisition Detection** — If the company was acquired, automatically runs a secondary search on the acquirer to understand their strategy

4. **Ranking** — Statements are scored by "outreach relevance" (0-100) based on how useful they are for B2B conversations

5. **Deep Analysis** (optional) — Uses Gemini's native video understanding to extract full content from YouTube videos and articles

---

## Requirements

- Python 3.8+
- Google AI Studio API key (free tier works)
- `google-genai` package

## API Key

Get your free API key at: https://aistudio.google.com/app/apikey

The free tier includes generous limits for Gemini 2.0 Flash.

## Cost

Using Gemini 2.0 Flash with Google Search grounding:

| Operation | Cost |
|-----------|------|
| Discovery (with acquirer) | ~$0.001-0.002 |
| Discovery (no acquirer) | ~$0.0005 |
| Revenue estimation | ~$0.001 |
| Deep analysis per source | ~$0.002-0.005 |

## License

MIT

## Credits

Built with Claude Code
