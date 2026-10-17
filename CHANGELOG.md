# Changelog

## [1.4.1] - 2026-10-18

### Fixed
- **Server failed to start on a fresh install.** `requirements.txt` asks for `mcp>=1.0.0`, and
  since the release of mcp 2.x that resolves to a version where `FastMCP` was renamed to
  `MCPServer` — so the import raised `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`
  and the server never came up. The import now falls back to `MCPServer`, so the same file runs
  on both mcp 1.x and 2.x. Verified against mcp 1.30.0 and 2.3.0: 56 tools register on both.

### Added
- Claude Code setup instructions in the README (`claude mcp add`, scopes, `.env` handling)

---

## [1.4.0] - 2026-07-10

### Added — Yandex Metrica Tools (6)
- `ym_get_overview` — Comprehensive analytics: visitors, pageviews, bounce rate, daily trends, top sources/pages/geo/devices/search phrases
- `ym_get_traffic` — Traffic source breakdown (sources, search engines, social)
- `ym_get_pages` — Page performance (top, landing, exit, titles)
- `ym_get_geo` — Geographic visitor data (countries, regions, cities)
- `ym_get_devices` — Device/browser/OS breakdown
- `ym_get_search_phrases` — Yandex search keywords driving visits

### Added — Bing Webmaster Tools (9)
- `bing_get_query_stats` — Search query statistics with clicks, impressions, CTR, position
- `bing_get_page_stats` — Page-level search performance
- `bing_get_crawl_stats` — Crawl statistics over time (crawled pages, errors, indexed, links)
- `bing_get_crawl_issues` — Crawl errors and issues
- `bing_get_rank_traffic` — Daily impressions and clicks trend
- `bing_get_link_counts` — Inbound link counts per URL
- `bing_get_keyword_stats` — Keyword volume data (broad + exact match)
- `bing_get_url_traffic` — Per-URL traffic data
- `bing_get_url_links` — Inbound links for a specific URL

### Updated
- Integration status in `list_projects` now includes `bing_webmaster` and `yandex_metrica`
- System instructions with Yandex Metrica and Bing Webmaster tool guides
- Cross-platform chaining: Google + Bing + Yandex comprehensive workflows
- Error handling for new integration connection states
- Proactive suggestions for Yandex and Bing follow-up queries

---

## [1.3.0] - 2026-07-01

### Added — Rank Tracker Tools (5)
- `rank_get_keywords` — Keyword rankings with position, changes, search volume
- `rank_get_overview` — Ranking distribution, visibility score, yesterday's changes
- `rank_get_history` — Daily average position history
- `rank_report_gainers_losers` — Keywords that gained/lost rankings
- `rank_report_distribution` — Position distribution breakdown (Top 3/10/20/30/100)

### Added — AI Rank Tracker Tools (3)
- `ai_rank_get_overview` — AI Overview visibility summary and score
- `ai_rank_get_keywords` — Per-keyword AI Overview presence and positions
- `ai_rank_get_domains` — Top domains cited in AI Overviews (competitor analysis)

### Added — Indexing Monitor Tools (2)
- `indexing_get_status` — Health score, indexed/not-indexed counts, coverage groups, warnings
- `indexing_get_history` — Daily indexing counts over time

### Updated
- System instructions with rank tracker, AI rank, and indexing tool guides
- Cross-platform chaining: rankings + GSC + GA + Ads comprehensive workflows
- Rank tracker knowledge, AI visibility knowledge, indexing knowledge sections

---

## [1.2.0] - 2026-07-01

### Added — Google Ads Tools (8)

**Data Tools:**
- `gads_get_campaigns` — Campaign performance with metrics, filtering, and sorting
- `gads_get_daily_metrics` — Daily impressions, clicks, cost, conversions time series
- `gads_get_geo` — Geographic performance by country
- `gads_get_devices` — Device breakdown (mobile, desktop, tablet)
- `gads_get_search_terms` — Search terms triggering ads (Search campaigns)

**Report Tools:**
- `gads_report_performance_overview` — Account overview with top campaigns and type breakdown
- `gads_report_spend_analysis` — Spend trends, daily spend, per-campaign cost breakdown
- `gads_report_conversion_breakdown` — Conversion actions with counts and values

### Updated
- System instructions with Ads tool guide, Google Ads benchmarks, cross-platform chaining (GSC + GA + Ads)
- Proactive suggestions for ads optimization workflows

### Integrations
- Google Ads (full support)

---

## [1.1.0] - 2026-07-01

### Added — Google Analytics Tools (10)

**Data Tools:**
- `ga_get_overview` — Core analytics metrics with optional period comparison
- `ga_get_traffic_sources` — Traffic by channel, source, medium, campaign, or referrer
- `ga_get_pages` — Top pages, entry pages, or exit pages
- `ga_get_geo` — Geographic breakdown by country, region, or city
- `ga_get_devices` — Device category, browser, or OS breakdown
- `ga_get_key_events` — Key events (conversions) with counts

**Report Tools:**
- `ga_report_traffic_trends` — Daily metrics with growth analysis, peak/trough detection
- `ga_report_landing_page_performance` — Landing page conversion rates (organic search)
- `ga_report_channel_comparison` — Channel-by-channel comparison with previous period
- `ga_report_engagement_analysis` — Page engagement quality tiers (high/medium/low)

### Updated
- System instructions with GA tool selection guide, cross-platform chaining (GSC + GA), analytics benchmarks
- list_projects integration status now actionable for Google Analytics tools

### Integrations
- Google Analytics (full support)

---

## [1.0.0] - 2026-06-03

### Tools (13)
- `list_projects` — List projects with integration status
- `get_keywords` — Keyword performance from Google Search Console
- `get_pages` — Page performance from Google Search Console
- `get_performance` — Daily traffic overview with summary
- `report_cannibalization` — Keyword cannibalization detection
- `report_monthly_summary` — End-of-month SEO report
- `report_long_tail` — Long-tail keyword opportunities
- `report_winner_loser` — Traffic winners and losers
- `report_questions` — Question-type search queries
- `report_content_decay` — Declining content detection
- `report_striking_distance` — Page 2-3 quick wins
- `report_low_ctr` — Low CTR optimization opportunities
- `report_thin_content` — Underperforming content audit

### Integrations
- Google Search Console (full support)

### Planned
- Meta Ads tools
- Rank Tracker tools
