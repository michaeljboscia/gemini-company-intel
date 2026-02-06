# Gemini Company Intel

Collect strategic intelligence about any company using Google's Gemini AI with real-time Google Search grounding.

## What It Does

Point it at a domain and get:
- **Executive quotes** from YouTube, podcasts, interviews
- **Strategic priorities** extracted from public statements
- **Ownership changes** (acquisitions, PE investments, mergers)
- **Acquirer intelligence** — automatically researches the acquiring company if detected
- **Outreach angles** — suggested talking points for B2B outreach

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_REPO/gemini-company-intel.git
cd gemini-company-intel

# Install
pip install -r requirements.txt

# Set your API key
export GEMINI_API_KEY="your-key-here"  # Get one at https://aistudio.google.com/app/apikey

# Run
python src/discovery.py --domain dunnlumber.com --company-name "Dunn Lumber"
```

## Usage

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

## Output Formats

### JSON
Full structured data including:
- `strategic_statements[]` — quotes with speaker, source, relevance score
- `key_executives[]` — names, titles, notable quotes
- `company_priorities[]` — identified strategic priorities
- `ownership_changes[]` — acquisitions, mergers, PE investments
- `acquisition_info` — deep intel on acquiring company (if applicable)

### Text
Human-readable report with sections:
- Company Overview
- Key Executives
- Strategic Priorities
- Ownership Changes
- Acquirer Intelligence
- Strategic Statements (ranked by relevance)

## Example Output

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

## How It Works

1. **Discovery** — Gemini searches Google for public statements, YouTube videos, podcasts, press releases, SEC filings about the company

2. **Extraction** — Parses executive quotes, strategic priorities, ownership changes into structured JSON

3. **Acquisition Detection** — If the company was acquired, automatically runs a secondary search on the acquirer to understand their strategy

4. **Ranking** — Statements are scored by "outreach relevance" (0-100) based on how useful they are for B2B conversations

## Requirements

- Python 3.8+
- Google AI Studio API key (free tier works)
- `google-genai` package

## API Key

Get your free API key at: https://aistudio.google.com/app/apikey

The free tier includes generous limits for Gemini 2.0 Flash.

## Cost

Using Gemini 2.0 Flash with Google Search grounding:
- ~$0.001-0.002 per company (with acquirer research)
- ~$0.0005 per company (without acquirer research)

## License

MIT

## Credits

Built with Claude Code
