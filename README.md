# Semust MCP Server

[![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Ask Claude about your SEO data in plain language.** This MCP server connects Claude Desktop (and Cursor) to your [Semust](https://semust.com) account — keywords, pages, traffic trends, SEO reports, and more.

> "Show me my top keywords for the last month"
>
> "Which pages are losing traffic?"
>
> "Find quick win keywords close to page 1"

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
   Your Google Search Console data
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

**Keywords**
- "What are my top 20 keywords?"
- "Which keywords are on page 2? Those are my quick wins"
- "Find long-tail keyword opportunities"

**Content Analysis**
- "Which pages are losing traffic? I need to refresh them"
- "Show me my worst performing content"
- "Do I have keyword cannibalization issues?"

**Reports**
- "Generate a monthly SEO report for May 2026"
- "Which keywords gained or lost traffic this month?"
- "Find low CTR keywords I should optimize"

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
      }
    }
  }
}
```

> **Important**: Replace the path with the actual location of `semust_mcp.py` on your machine.
>
> **Windows**: Use double backslashes: `C:\\Users\\you\\semust-mcp\\semust_mcp.py`
>
> **If `python` doesn't work**: Use the full Python path instead, e.g.: `C:\\Users\\you\\AppData\\Local\\Programs\\Python\\Python312\\python.exe`

**Quit Claude Desktop completely** (right-click system tray icon > Quit) and reopen it.

### Step 4: Verify

In a new Claude chat, look for the **tools icon** (hammer/wrench) near the text input. Click it — you should see "semust-mcp" with 13 tools.

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

## Available Tools (13)

### Data
| Tool | Description |
|------|-------------|
| `list_projects` | List all projects with integration status — **always runs first** |
| `get_keywords` | Top keywords by clicks with growth metrics |
| `get_pages` | Top pages by clicks with growth metrics |
| `get_performance` | Daily traffic overview with before/after comparison |

### SEO Reports
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
| No data / empty results | GSC data has a 2-day delay — Claude handles this automatically |
| Config file not found | Make sure Claude Desktop is installed and has been opened at least once |

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- [Claude Desktop](https://claude.ai/download) or [Cursor](https://cursor.sh)
- A [Semust](https://semust.com) account with an active subscription
- Google Search Console connected to at least one project

## License

MIT — see [LICENSE](LICENSE)
