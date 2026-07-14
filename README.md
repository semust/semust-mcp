# Semust MCP Server

[![Version 1.4.0](https://img.shields.io/badge/version-1.4.0-blue.svg)](CHANGELOG.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Ask Claude about your SEO and advertising data in plain language.** This MCP server connects Claude Desktop (and Cursor) to your [Semust](https://semust.com) account — keywords, pages, traffic trends, SEO reports, Google Analytics, Google Ads, Yandex Metrica, Bing Webmaster, and more.

> "Show me my top keywords for the last month"
>
> "Which pages are losing traffic?"
>
> "How is my organic traffic compared to last month?"
>
> "Which landing pages convert best?"
>
> "How are my Google Ads campaigns performing?"

---

## How It Works

```
You ask Claude a question
        |
Claude Desktop (on your machine)
        |
   MCP Server (on your machine) ---- Your API key stays here, never sent to Claude
        |
   Semust API (semust.com)
        |
   Your Google Search Console, Analytics & Ads data
        |
   Results sent back to Claude
        |
Claude answers with SEO insights
```

Your API key **never leaves your machine**. Claude only sees the SEO data, not your credentials.

---

## What You Can Ask

Once set up, just talk to Claude naturally:

**Traffic & Performance**
- "How is my site performing this month?"
- "Show me daily traffic for the last 30 days"
- "Is my traffic growing or declining?"

**Keywords**
- "What are my top 20 keywords?"
- "Which keywords are on page 2? Those are my quick wins"
- "Find long-tail keyword opportunities"

**Google Analytics**
- "Where does my traffic come from?"
- "How is organic vs paid traffic performing?"
- "Which landing pages convert best?"
- "Show me mobile vs desktop breakdown"
- "Which pages have the worst engagement?"

**Rank Tracker**
- "Where do I rank for my keywords?"
- "Which keywords gained or lost positions?"
- "How many keywords are on page 1?"

**AI Rank Tracker**
- "Am I appearing in Google's AI Overviews?"
- "Which competitors are cited in AI answers?"

**Indexing Monitor**
- "Are all my pages indexed?"
- "What's my indexing health score?"

**Yandex Metrica**
- "How is my Yandex traffic?"
- "What are people searching on Yandex?"
- "Show me traffic sources from Yandex"

**Bing Webmaster**
- "How are my pages doing on Bing?"
- "Show me Bing crawl issues"
- "What are my Bing backlinks?"

**Google Ads**
- "How are my campaigns performing?"
- "How much am I spending and what's my ROAS?"
- "What search terms trigger my ads?"
- "Show me ad performance by country"
- "Which conversion types am I getting?"

**Content Analysis**
- "Which pages are losing traffic? I need to refresh them"
- "Show me my worst performing content"
- "Do I have keyword cannibalization issues?"

**Reports**
- "Generate a monthly SEO report for May 2026"
- "Which keywords gained or lost traffic this month?"
- "Find low CTR keywords I should optimize"
- "Give me a complete SEO + analytics report"

**Content Ideas**
- "What questions are people asking that lead to my site?"
- "Show me long-tail keywords with 4+ words"

---

## Quick Start

### Step 1: Get Your API Key

Log in to [Semust](https://semust.com) > Settings > API Key > Copy.

Make sure you have at least one project with **Google Search Console connected**.

### Step 2: Download & Install

**Option A: Download ZIP** (easiest)

[Download ZIP](https://github.com/semust/semust-mcp/archive/refs/heads/main.zip) > Extract to a folder you'll remember.

**Option B: Git Clone**
```bash
git clone https://github.com/semust/semust-mcp.git
```

Then install dependencies:
```bash
cd semust-mcp
pip install -r requirements.txt
```

### Step 3: Configure Claude Desktop

Find your Claude Desktop config file:

<details>
<summary><b>Windows (Microsoft Store version)</b></summary>

Open File Explorer and paste this in the address bar:
```
%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\
```
Open `claude_desktop_config.json`
</details>

<details>
<summary><b>Windows (Direct install)</b></summary>

Open File Explorer and paste this in the address bar:
```
%APPDATA%\Claude\
```
Open `claude_desktop_config.json`
</details>

<details>
<summary><b>Mac</b></summary>

```
~/Library/Application Support/Claude/claude_desktop_config.json
```
</details>

Add `mcpServers` to the file. If the file already has content, **merge** this into the existing JSON:

```json
{
  "mcpServers": {
    "semust": {
      "command": "python",
      "args": ["C:\\full\\path\\to\\semust-mcp\\semust_mcp.py"],
      "env": {
        "SEMUST_API_KEY": "your-api-key-here",
        "SEMUST_BASE_URL": "https://api.semust.com/v1/mcp"
      },
      "alwaysAllow": [
        "list_projects",
        "get_keywords", "get_pages", "get_performance",
        "report_cannibalization", "report_monthly_summary", "report_long_tail",
        "report_winner_loser", "report_questions", "report_content_decay",
        "report_striking_distance", "report_low_ctr", "report_thin_content",
        "ga_get_overview", "ga_get_traffic_sources", "ga_get_pages",
        "ga_get_geo", "ga_get_devices", "ga_get_key_events",
        "ga_report_traffic_trends", "ga_report_landing_page_performance",
        "ga_report_channel_comparison", "ga_report_engagement_analysis",
        "gads_get_campaigns", "gads_get_daily_metrics", "gads_get_geo",
        "gads_get_devices", "gads_get_search_terms",
        "gads_report_performance_overview", "gads_report_spend_analysis",
        "gads_report_conversion_breakdown",
        "rank_get_keywords", "rank_get_overview", "rank_get_history",
        "rank_report_gainers_losers", "rank_report_distribution",
        "ai_rank_get_overview", "ai_rank_get_keywords", "ai_rank_get_domains",
        "indexing_get_status", "indexing_get_history",
        "ym_get_overview", "ym_get_traffic", "ym_get_pages",
        "ym_get_geo", "ym_get_devices", "ym_get_search_phrases",
        "bing_get_query_stats", "bing_get_page_stats", "bing_get_crawl_stats",
        "bing_get_crawl_issues", "bing_get_rank_traffic", "bing_get_link_counts",
        "bing_get_keyword_stats", "bing_get_url_traffic", "bing_get_url_links"
      ]
    }
  }
}
```

> **Important**: Replace the path with the actual location of `semust_mcp.py` on your machine.
>
> **Windows**: Use double backslashes: `C:\\Users\\you\\semust-mcp\\semust_mcp.py`
>
> **If `python` doesn't work**: Use the full Python path instead, e.g.: `C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`
>
> **`alwaysAllow`**: This list lets Claude use Semust tools without asking for permission each time. All tools are read-only and safe to auto-approve. Remove this field if you prefer to approve each tool call manually.

**Quit Claude Desktop completely** (right-click system tray icon > Quit) and reopen it.

### Step 4: Verify

In a new Claude chat, look for the **tools icon** (hammer/wrench) near the text input. Click it — you should see "semust-mcp" with 56 tools.

Type: **"Show me my projects"** — Claude should list your Semust projects.

---

## Security

| What | Where | Who can see it |
|------|-------|---------------|
| Your API key | `.env` file or Claude Desktop config on **your machine** | Only you |
| MCP server | Runs as a local process on **your machine** | Only you |
| SEO data (keywords, pages, etc.) | Sent from Semust API to Claude via MCP | You and Claude |
| Your API key | **Never** sent to Claude or Anthropic | No one else |

- The MCP server runs **locally on your computer** — it is not a cloud service
- Your Semust API key is used only for direct requests from your machine to `api.semust.com`
- Claude sees the SEO data responses but **never** your API key or authentication credentials
- The `.env` file is in `.gitignore` — it won't be accidentally committed to git
- The server refuses to start if `SEMUST_BASE_URL` is `http://` (non-localhost) — your key is never sent in plaintext
- **Protect your Claude Desktop config file** — anyone with read access to it can read your API key
- SEO data passed to Claude is treated as user-trusted content; if your Search Console contains spam queries with embedded instructions, the model may act on them — this is inherent to all MCP tools that surface third-party data

---

## Available Tools (56)

### Projects
| Tool | Description |
|------|-------------|
| `list_projects` | List all projects with integration status — **always runs first** |

### Search Console — Data
| Tool | Description |
|------|-------------|
| `get_keywords` | Top keywords by clicks with growth metrics |
| `get_pages` | Top pages by clicks with growth metrics |
| `get_performance` | Daily traffic overview with before/after comparison |

### Search Console — Reports
| Tool | Description |
|------|-------------|
| `report_cannibalization` | Pages competing for the same keyword |
| `report_monthly_summary` | Full monthly SEO report with YoY comparison |
| `report_long_tail` | Long-tail keyword opportunities (3+ words) |
| `report_winner_loser` | Keywords gaining or losing traffic |
| `report_questions` | Question-type queries (FAQ/content ideas) |
| `report_content_decay` | Pages losing traffic over time |
| `report_striking_distance` | Keywords on page 2-3 (quick wins) |
| `report_low_ctr` | Low CTR items with click improvement potential |
| `report_thin_content` | Underperforming content for audit |

### Google Analytics — Data
| Tool | Description |
|------|-------------|
| `ga_get_overview` | Core metrics (users, sessions, bounce rate) with comparison |
| `ga_get_traffic_sources` | Traffic by channel, source, medium, campaign, referrer |
| `ga_get_pages` | Top pages, entry pages, exit pages |
| `ga_get_geo` | Visitors by country, region, or city |
| `ga_get_devices` | Device category, browser, or OS breakdown |
| `ga_get_key_events` | Key events (conversions) with counts |

### Google Analytics — Reports
| Tool | Description |
|------|-------------|
| `ga_report_traffic_trends` | Daily metrics with growth analysis and patterns |
| `ga_report_landing_page_performance` | Landing page conversion rates (organic) |
| `ga_report_channel_comparison` | Channel comparison with previous period |
| `ga_report_engagement_analysis` | Page engagement quality tiers |

### Google Ads — Data
| Tool | Description |
|------|-------------|
| `gads_get_campaigns` | Campaign performance with metrics and sorting |
| `gads_get_daily_metrics` | Daily impressions, clicks, cost, conversions |
| `gads_get_geo` | Performance by country/geography |
| `gads_get_devices` | Device breakdown (mobile, desktop, tablet) |
| `gads_get_search_terms` | Search terms triggering ads (Search campaigns) |

### Google Ads — Reports
| Tool | Description |
|------|-------------|
| `gads_report_performance_overview` | Account overview with rankings and type breakdown |
| `gads_report_spend_analysis` | Spend trends and per-campaign cost breakdown |
| `gads_report_conversion_breakdown` | Conversion actions with counts and values |

### Rank Tracker
| Tool | Description |
|------|-------------|
| `rank_get_keywords` | Keyword rankings with position and changes |
| `rank_get_overview` | Distribution, visibility score, yesterday's changes |
| `rank_get_history` | Daily average position history |
| `rank_report_gainers_losers` | Keywords that gained/lost rankings |
| `rank_report_distribution` | Position distribution breakdown |

### AI Rank Tracker
| Tool | Description |
|------|-------------|
| `ai_rank_get_overview` | AI Overview visibility summary and score |
| `ai_rank_get_keywords` | Per-keyword AI Overview presence and positions |
| `ai_rank_get_domains` | Top domains cited in AI Overviews |

### Indexing Monitor
| Tool | Description |
|------|-------------|
| `indexing_get_status` | Health score, indexed/not-indexed, coverage, warnings |
| `indexing_get_history` | Daily indexing counts over time |

### Yandex Metrica
| Tool | Description |
|------|-------------|
| `ym_get_overview` | Comprehensive analytics: visitors, pageviews, bounce rate, daily trends |
| `ym_get_traffic` | Traffic source breakdown (sources, search engines, social) |
| `ym_get_pages` | Page performance (top, landing, exit, titles) |
| `ym_get_geo` | Geographic visitor data (countries, regions, cities) |
| `ym_get_devices` | Device/browser/OS breakdown |
| `ym_get_search_phrases` | Yandex search keywords driving visits |

### Bing Webmaster
| Tool | Description |
|------|-------------|
| `bing_get_query_stats` | Search query statistics with clicks, impressions, CTR, position |
| `bing_get_page_stats` | Page-level search performance |
| `bing_get_crawl_stats` | Crawl statistics over time |
| `bing_get_crawl_issues` | Crawl errors and issues |
| `bing_get_rank_traffic` | Daily impressions and clicks trend |
| `bing_get_link_counts` | Inbound link counts per URL |
| `bing_get_keyword_stats` | Keyword volume data (requires keyword param) |
| `bing_get_url_traffic` | Per-URL traffic data (requires url param) |
| `bing_get_url_links` | Inbound links for a specific URL (requires url param) |

---

## Cursor Setup

Add the same MCP server in Cursor: **Settings > MCP Servers > Add Server** (stdio type).

Use the same command, args, and env values from the Claude Desktop config above.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tools icon not showing | Quit Claude Desktop fully from system tray, reopen |
| `python` not recognized | Use full Python path in config (see Step 3) |
| "Invalid API key" (401) | Double-check your key in [Semust Settings](https://semust.com) |
| "User not active" (403) | You need a paid plan — [semust.com/fiyatlar](https://semust.com/fiyatlar) |
| "Search Console not connected" | Connect GSC in Semust > Project Settings > Integrations |
| "Google Analytics not connected" | Connect GA4 in Semust > Project Settings > Integrations |
| "Google Ads not connected" | Connect Google Ads in Semust > Project Settings > Integrations |
| "Yandex Metrica not connected" | Connect Yandex Metrica in Semust > Project Settings > Integrations |
| "Bing Webmaster not connected" | Connect Bing Webmaster in Semust > Project Settings > Integrations |
| Claude asks permission for every tool | Add `alwaysAllow` to your config (see Step 3 above) |
| No data / empty results | GSC data has a 2-day delay — Claude handles this automatically |
| Config file not found | Make sure Claude Desktop is installed and has been opened at least once |

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- [Claude Desktop](https://claude.ai/download) or [Cursor](https://cursor.sh)
- A [Semust](https://semust.com) account with an active subscription
- Google Search Console, Google Analytics, Google Ads, Yandex Metrica, and/or Bing Webmaster connected to at least one project

## License

MIT — see [LICENSE](LICENSE)
