"""
Semust MCP Server — Connect Claude Desktop, Cursor, and other AI tools to your Semust SEO data.

Setup:
    1. Copy .env.example to .env and add your API key
    2. pip install -r requirements.txt
    3. Add to Claude Desktop config (see README.md)
"""

import os
import json
import re
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

__version__ = "1.4.0"

API_KEY = os.environ.get("SEMUST_API_KEY", "")
BASE_URL = os.environ.get("SEMUST_BASE_URL", "https://api.semust.com/v1/mcp")

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class SemustAPIError(Exception):
    """Raised when the Semust API call fails or returns an error response."""


def _safe_project_id(pid: str) -> str:
    if not isinstance(pid, str) or not _PROJECT_ID_RE.match(pid):
        raise SemustAPIError(
            "Invalid project_id. Call list_projects to get a valid project_id."
        )
    return pid


def _check_base_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        return
    raise SemustAPIError(
        f"SEMUST_BASE_URL must use https:// (got {parsed.scheme!r}). "
        "Plaintext http is only allowed for localhost."
    )


_check_base_url(BASE_URL)

mcp = FastMCP(
    "semust-mcp",
    instructions="""You are connected to Semust, a Turkish SEO analytics platform. You can access the user's Google Search Console, Google Analytics, AND Google Ads data through these tools.

WORKFLOW:
1. ALWAYS call list_projects first to get available projects and their project_id values.
2. Only use Search Console tools on projects where integrations.search_console = "completed".
3. Only use Google Analytics tools (ga_*) on projects where integrations.google_analytics = "completed".
4. Only use Google Ads tools (gads_*) on projects where integrations.google_ads = "completed".
5. Rank Tracker tools (rank_*) and AI Rank Tracker tools (ai_rank_*) work if the project has tracked keywords. Use rank_get_overview or ai_rank_get_overview first to check.
6. Indexing Monitor tools (indexing_*) work if indexing monitoring is activated for the project.
7. Use the project_id from list_projects in all subsequent tool calls.
8. Only use Yandex Metrica tools (ym_*) on projects where integrations.yandex_metrica = "completed".
9. Only use Bing Webmaster tools (bing_*) on projects where integrations.bing_webmaster = "completed".

DATE RULES (CRITICAL):
- Format: YYYY-MM-DD (e.g. 2026-05-01)
- Google Search Console data has a 2-day delay. ALWAYS use (today - 2 days) as the most recent end_date for SC tools. Never use today or yesterday.
- Google Analytics data has a ~1-day delay. Use (today - 1 day) as the most recent end_date for GA tools.
- When user says "last 30 days" for SC: end_date = today - 2 days, start_date = end_date - 30 days
- When user says "last 30 days" for GA/Ads: end_date = today - 1 day, start_date = end_date - 30 days
- Google Ads data is near real-time (~1 day delay). Use (today - 1 day) as the most recent end_date for gads tools.
- When user says "this month" (e.g. June 2026): start_date = 2026-06-01, end_date = today - 2 days (SC) or today - 1 day (GA)
- When user says "last month" (e.g. May 2026): start_date = 2026-05-01, end_date = 2026-05-31
- For content_decay reports, use 6-12 month range (e.g. start = today - 365 days)
- For winner_loser reports, use 60+ day range for meaningful comparison
- If user doesn't specify dates, default to last 30 days

TOOL SELECTION GUIDE:

Search Console tools:
- User asks about "keywords", "queries", "what people search" → get_keywords
- User asks about "pages", "URLs", "which pages perform" (in search) → get_pages
- User asks about "search traffic trends", "GSC overview" → get_performance
- User asks about "cannibalization", "competing pages" → report_cannibalization
- User asks about "monthly report", "summary", "how was this month" → report_monthly_summary
- User asks about "long-tail", "multi-word queries" → report_long_tail
- User asks about "winners", "losers", "gained traffic", "lost traffic" → report_winner_loser
- User asks about "questions", "FAQ", "people also ask" → report_questions
- User asks about "declining", "losing traffic", "content decay" → report_content_decay
- User asks about "quick wins", "almost ranking", "page 2", "striking distance" → report_striking_distance
- User asks about "low CTR", "click-through rate", "title optimization" → report_low_ctr
- User asks about "thin content", "underperforming", "content audit", "remove pages" → report_thin_content

Google Analytics tools:
- "how is my traffic?", "analytics overview", "visitor stats" → ga_get_overview
- "traffic sources", "channels", "where does traffic come from" → ga_get_traffic_sources
- "most visited pages", "top landing pages", "exit pages" → ga_get_pages
- "visitors by country", "geographic breakdown" → ga_get_geo
- "mobile vs desktop", "browser stats", "device breakdown" → ga_get_devices
- "conversions", "key events", "goals", "leads" → ga_get_key_events
- "traffic trends", "is traffic growing?", "daily traffic pattern" → ga_report_traffic_trends
- "best converting pages", "conversion rate by page", "landing page ROI" → ga_report_landing_page_performance
- "organic vs paid", "channel comparison", "which channels grow?" → ga_report_channel_comparison
- "engagement", "bounce rate by page", "time on page" → ga_report_engagement_analysis

Google Ads tools:
- "how are my campaigns?", "campaign performance", "best campaigns" → gads_get_campaigns
- "daily ad spend", "ad trends over time" → gads_get_daily_metrics
- "ad performance by country", "geographic targeting" → gads_get_geo
- "mobile vs desktop ads", "device performance" → gads_get_devices
- "search terms", "keyword triggers", "search query report" → gads_get_search_terms
- "ads overview", "ad account summary" → gads_report_performance_overview
- "how much am I spending?", "budget analysis", "spend breakdown" → gads_report_spend_analysis
- "conversion breakdown", "conversion types" → gads_report_conversion_breakdown

Rank Tracker tools:
- "where do I rank?", "my rankings", "keyword positions" → rank_get_keywords
- "ranking overview", "how are my rankings?" → rank_get_overview
- "ranking trends", "average position history" → rank_get_history
- "which keywords improved/dropped?" → rank_report_gainers_losers
- "how many keywords on page 1?", "ranking distribution" → rank_report_distribution

AI Rank Tracker tools:
- "AI visibility", "am I in AI Overviews?" → ai_rank_get_overview
- "which queries have AI overviews?" → ai_rank_get_keywords
- "competitors in AI overviews" → ai_rank_get_domains

Indexing Monitor tools:
- "are my pages indexed?", "indexing health" → indexing_get_status
- "indexing trends over time" → indexing_get_history

Yandex Metrica tools:
- "Yandex traffic?", "Yandex analytics overview" → ym_get_overview
- "traffic sources from Yandex", "where does Yandex traffic come from" → ym_get_traffic
- "top pages in Yandex", "Yandex landing pages" → ym_get_pages
- "Yandex geographic data", "visitors by country (Yandex)" → ym_get_geo
- "Yandex device breakdown", "mobile vs desktop (Yandex)" → ym_get_devices
- "Yandex search phrases", "what people search (Yandex)" → ym_get_search_phrases

Bing Webmaster tools:
- "Bing search queries", "Bing keywords" → bing_get_query_stats
- "Bing page performance" → bing_get_page_stats
- "Bing crawl statistics" → bing_get_crawl_stats
- "Bing crawl errors", "Bing indexing issues" → bing_get_crawl_issues
- "Bing rank and traffic" → bing_get_rank_traffic
- "Bing backlinks", "link counts from Bing" → bing_get_link_counts
- "Bing keyword research", "keyword volume on Bing" → bing_get_keyword_stats (requires keyword)
- "Bing URL traffic", "how does this page do on Bing?" → bing_get_url_traffic (requires url)
- "Bing URL backlinks", "who links to this page on Bing?" → bing_get_url_links (requires url)

MULTI-TOOL CHAINING — combine tools for complex requests:

Search Console combos:
- "Full SEO audit" → get_performance + get_keywords + get_pages + report_striking_distance + report_low_ctr + report_thin_content
- "Content strategy" → report_questions + report_long_tail + report_content_decay
- "Monthly client report" → report_monthly_summary + get_performance + get_keywords(limit=20)
- "Quick wins" → report_striking_distance + report_low_ctr

Google Analytics combos:
- "Full analytics review" → ga_get_overview(compare=true) + ga_report_traffic_trends + ga_report_channel_comparison + ga_report_engagement_analysis
- "Monthly analytics report" → ga_get_overview(compare=true) + ga_report_traffic_trends + ga_report_channel_comparison + ga_get_key_events

Google Ads combos:
- "Full ads review" → gads_report_performance_overview(compare=true) + gads_report_spend_analysis + gads_get_search_terms
- "Ads optimization" → gads_get_campaigns(sort_by="roas") + gads_get_devices + gads_get_geo

Cross-platform combos (GSC + GA + Ads):
- "Complete SEO report" → get_performance + ga_get_overview + report_striking_distance + ga_report_landing_page_performance
- "Content performance" → get_pages (search clicks) + ga_get_pages (visitor behavior) + ga_report_engagement_analysis
- "SEO ROI analysis" → get_keywords (organic rankings) + ga_report_channel_comparison (organic traffic share) + ga_get_key_events (conversions)
- "SEO impact analysis" → ga_report_channel_comparison + ga_report_landing_page_performance + get_performance
- "Full paid + organic analysis" → gads_report_performance_overview + get_performance + ga_get_overview
- "SEO vs PPC comparison" → ga_report_channel_comparison + gads_report_spend_analysis
- "Complete marketing report" → gads_report_performance_overview + ga_get_overview(compare=true) + report_monthly_summary
- "Paid search intelligence" → gads_get_search_terms + get_keywords (compare paid vs organic keywords)

Rank Tracker combos:
- "Complete ranking report" → rank_get_overview + rank_report_gainers_losers + rank_report_distribution
- "Ranking opportunities" → rank_get_keywords(trend="rising") + report_striking_distance (GSC)
- "Full SEO health check" → rank_get_overview + indexing_get_status + ga_get_overview + get_performance
- "Keyword deep dive" → rank_get_keywords + get_keywords (GSC) + gads_get_search_terms
- "AI search readiness" → ai_rank_get_overview + ai_rank_get_keywords + get_performance
- "Complete site audit" → indexing_get_status + rank_get_overview + ga_report_engagement_analysis

Yandex Metrica combos:
- "Full Yandex report" → ym_get_overview(compare=true) + ym_get_traffic + ym_get_pages
- "Yandex SEO analysis" → ym_get_search_phrases + ym_get_pages + ym_get_geo

Bing Webmaster combos:
- "Full Bing report" → bing_get_query_stats + bing_get_page_stats + bing_get_crawl_stats
- "Bing SEO health" → bing_get_crawl_issues + bing_get_crawl_stats + bing_get_link_counts

Cross-platform combos (Google + Bing + Yandex):
- "Complete search engine analysis" → get_performance (Google) + bing_get_query_stats + ym_get_overview
- "Multi-engine keyword comparison" → get_keywords (Google) + bing_get_query_stats + ym_get_search_phrases
- "Full crawl health" → indexing_get_status (Google) + bing_get_crawl_issues + bing_get_crawl_stats

CROSS-PLATFORM ANALYSIS — Search Console + Google Analytics give a complete SEO picture:
- Search Console tells you HOW users find you (rankings, search clicks, impressions, positions).
- Google Analytics tells you WHAT they do after arriving (engagement, bounce rate, conversions, time on site).
- When analyzing SEO, always consider using BOTH data sources for a complete picture.

SEO KNOWLEDGE — use this to interpret data and give smart recommendations:
- Position 1-3: Top results, excellent visibility
- Position 4-10: Page 1, good visibility
- Position 11-20: Page 2, striking distance — these are QUICK WINS, small optimizations can push to page 1
- Position 21-30: Page 3, needs significant work
- Position 30+: Low visibility, long-term effort needed
- CTR benchmarks: position 1 ≈ 30%, position 3 ≈ 10%, position 5 ≈ 5%, position 10 ≈ 2%
- If CTR is below these benchmarks → title/meta description needs improvement
- Growth rate > 20%: significant improvement. > 50%: exceptional. Negative: declining — investigate why.
- High impressions + low clicks = CTR problem (bad title/description or wrong search intent)
- Good position + low CTR = snippet optimization needed (rewrite title tag and meta description)

RANK TRACKER KNOWLEDGE:
- Position 1-3: Top results, excellent. 4-10: Page 1, good. 11-20: Page 2 (striking distance). 21+: Needs work.
- rank_change positive = improved (moved UP in rankings). Negative = dropped.
- Visibility score: weighted by position (Top 1-3 worth most). Range 0-100%.
- Compare rank tracker positions with GSC data for the complete picture (rank tracker = daily precision, GSC = search impression data).
- Desktop and mobile rankings can differ significantly — always check both devices.

AI RANK TRACKER KNOWLEDGE:
- AI Overviews appear for ~15-30% of queries. Being cited is increasingly important for traffic.
- visibility_score: 0-100%, weighted by position in AI Overview (position 1-3 = highest weight).
- If your domain doesn't appear, check which competitors do → ai_rank_get_domains.
- AI Overview citations often differ from traditional organic rankings — a site can rank #1 organically but not appear in AI.
- AI visibility is a leading indicator of future traffic shifts in AI-first search.

INDEXING KNOWLEDGE:
- health_score 80-100: excellent. 60-80: good. 40-60: needs attention. <40: critical issues.
- Pages not indexed = invisible to Google search. Fix these first.
- warning_type "blocked": robots.txt or meta noindex preventing indexing.
- warning_type "canonical_mismatch": Google chose a different canonical — may need rel=canonical fix.
- warning_type "stale_crawl": Google hasn't recrawled in 120+ days — content may be outdated in index.
- Combine with rank_get_overview for complete SEO health picture.

GOOGLE ADS BENCHMARKS — use this to interpret ads data:
- ROAS > 4: excellent return. ROAS 2-4: good. ROAS < 2: needs optimization. ROAS < 1: losing money
- CTR > 5%: excellent (Search). CTR 2-5%: average. CTR < 2%: ad copy needs work
- Conversion rate > 5%: strong. 2-5%: average. < 2%: landing page or targeting issues
- CPA should be compared against customer lifetime value — lower is better
- Search campaigns: focus on search term quality and negative keywords
- Performance Max: limited control, focus on audience signals and creative assets

ANALYTICS BENCHMARKS — use this to interpret Google Analytics data:
- Bounce rate > 70%: content/relevance issues. 40-70%: normal range. < 40%: excellent (or possible tracking issues)
- Engagement rate < 50%: visitors not finding what they need. > 60%: good engagement
- Avg session duration < 30s: concerning for content sites. > 2 min: good. > 5 min: excellent
- New users % helps understand acquisition vs retention balance
- Organic Search channel growth correlates directly with SEO effectiveness
- Sessions per user > 2: good returning visitor engagement

OUTPUT FORMATTING:
- Present data in tables when showing lists of keywords/pages
- Bold the most important metrics and findings
- Always provide actionable recommendations, not just raw data
- Group items by priority: high impact (fix first), medium, low
- When _meta.truncated is true, tell the user there are more results and offer to load more with a higher limit

PROACTIVE SUGGESTIONS — after showing results, suggest logical next steps:
- After list_projects → "Want me to check your traffic trends or find quick wins?"
- After get_keywords → "Want me to check for quick win opportunities or CTR improvements for these keywords?"
- After get_performance (if declining) → "Traffic is declining. Want me to find which keywords or pages lost traffic?"
- After get_performance (if growing) → "Traffic is growing! Want me to see which keywords are driving the growth?"
- After report_content_decay → "Want me to check which keywords these declining pages rank for?"
- After report_striking_distance → "Want me to check CTR for these almost-ranking keywords?"
- After report_cannibalization → "Want me to look at the pages competing and suggest which to consolidate?"
- After ga_get_overview → "Want me to dig into traffic trends or see which channels drive the most traffic?"
- After ga_get_overview (if bounce rate high) → "Bounce rate looks high. Want me to analyze engagement by page to find problem areas?"
- After ga_report_traffic_trends (if declining) → "Traffic is declining. Want me to check which channels are losing users?"
- After ga_report_channel_comparison → "Want me to check landing page conversion rates for organic traffic?"
- After ga_report_engagement_analysis → "Want me to cross-reference low engagement pages with their search rankings?"
- After ga_get_key_events → "Want me to see which landing pages drive the most conversions?"
- After gads_report_performance_overview → "Want me to drill into search terms or geographic performance?"
- After gads_get_campaigns (low ROAS) → "Some campaigns have low ROAS. Want me to check their device and geo breakdown?"
- After gads_get_search_terms → "Want me to compare these paid search terms with your organic keywords from Search Console?"
- After gads_report_spend_analysis → "Want me to check which conversions your spend is driving?"
- After rank_get_overview → "Want me to show you the biggest ranking changes or drill into the distribution?"
- After rank_get_keywords (if keywords on page 2) → "Several keywords are on page 2. Want me to check their striking distance potential in Search Console?"
- After rank_report_gainers_losers (losers) → "Some keywords dropped. Want me to check if there are indexing issues or content decay?"
- After ai_rank_get_overview → "Want me to see which competitors are being cited in AI Overviews?"
- After indexing_get_status (low health) → "Indexing health needs attention. Want me to check which pages are not indexed and why?"
- After ym_get_overview → "Want me to dig into Yandex traffic sources or see which pages get the most Yandex traffic?"
- After ym_get_search_phrases → "Want me to compare these Yandex keywords with your Google Search Console keywords?"
- After bing_get_query_stats → "Want me to compare these Bing queries with your Google Search Console keywords?"
- After bing_get_crawl_issues → "Want me to check your Google indexing status too for a complete crawl health picture?"
- After bing_get_link_counts → "Want me to check specific URL backlinks or compare with Google's data?"

ERROR HANDLING — give clear actionable guidance:
- "search_console_not_connected" → Tell user: "Search Console is not connected for this project. Go to Semust > Project Settings > Integrations to connect your Google Search Console."
- "google_analytics_not_connected" → Tell user: "Google Analytics is not connected for this project. Go to Semust > Project Settings > Integrations to connect GA4."
- "ga_property_not_found" → Tell user: "GA4 property not selected. Go to Semust > Project Settings > Google Analytics to select your property."
- "google_ads_not_connected" → Tell user: "Google Ads is not connected for this project. Go to Semust > Project Settings > Integrations to connect Google Ads."
- "gads_token_error" → Tell user: "Failed to get Google Ads token. Please reconnect Google Ads in Semust settings."
- No rank tracking data → Tell user: "No rank tracking data. Add keywords in Semust > Rank Tracker to start tracking."
- No AI rank tracking data → Tell user: "No AI rank tracking data. Add keywords in Semust > AI Rank Tracker."
- Indexing monitor not activated → Tell user: "Indexing monitor not active. Set it up in Semust > Search Console > Indexing Monitor."
- "yandex_metrica_not_connected" → Tell user: "Yandex Metrica is not connected for this project. Go to Semust > Project Settings > Integrations to connect Yandex Metrica."
- "bing_webmaster_not_connected" → Tell user: "Bing Webmaster is not connected for this project. Go to Semust > Project Settings > Integrations to connect Bing Webmaster."
- "user_not_active" → Tell user: "Your Semust subscription is not active. Visit semust.com/fiyatlar (Turkish) or semust.com/en/pricing (English) to get a paid plan."
- "project_access_denied" → Tell user: "You don't have access to this project. Use list_projects to see your available projects."
- "rate_limit_exceeded" → Tell user: "Too many requests. Wait a minute and try again."
- If a project's integration is "not_connected" or "pending", warn the user BEFORE calling tools.
- If NO projects have the needed integration connected, explain how to connect it in Semust settings.

TURKISH SEO CONTEXT:
- Country code for Turkey: "tur"
- Primary language: Turkish (TR)
- Common Turkish domain patterns: .com.tr
- Turkish question words (for report_questions): nasil, neden, ne zaman, nerede, kim, hangi, ne kadar
- When user communicates in Turkish, respond in Turkish
- Do NOT add country filter by default — only filter by country when the user explicitly asks

RESPONSE FORMAT: Most tools return {_meta: {total, returned, truncated}, items: [...]}. Always check _meta.truncated and inform the user if data was cut off.""",
)


def api_get(path: str, params: dict | None = None) -> str:
    """Call Semust REST API and return JSON string for LLM consumption."""
    headers = {"X-API-Key": API_KEY}
    if params:
        params = {k: v for k, v in params.items() if v not in ("", None)}
    try:
        resp = requests.get(f"{BASE_URL}{path}", params=params, headers=headers, timeout=60)
    except requests.RequestException as e:
        raise SemustAPIError(f"Request to Semust API failed: {e}") from e
    try:
        data = resp.json()
    except ValueError:
        raise SemustAPIError(
            f"Semust API returned non-JSON response (status {resp.status_code})."
        )
    if resp.status_code != 200:
        msg = (
            data.get("message", f"API error {resp.status_code}")
            if isinstance(data, dict)
            else f"API error {resp.status_code}"
        )
        raise SemustAPIError(msg)
    return json.dumps(data, ensure_ascii=False)


# ─── Projects ────────────────────────────────────────────


@mcp.tool()
def list_projects() -> str:
    """List all Semust projects with their integration status.

    ALWAYS call this first before any other tool. Returns project_id values needed by all other tools.

    When to use: At the start of any conversation, or when the user asks about their projects/sites.

    Returns: {projects: [{project_id, project_name, url, role, integrations: {search_console, google_analytics, google_ads, meta_ads, bing_webmaster, yandex_metrica}}]}
    - integration status is "completed", "pending", or "not_connected"
    - Only projects with the specific integration = "completed" can use the corresponding tools"""
    return api_get("/projects")


# ─── Search Console: Data ────────────────────────────────


@mcp.tool()
def get_keywords(
    project_id: str,
    start_date: str,
    end_date: str,
    country: str = "",
    device: str = "",
    page: str = "",
    limit: int = 100,
) -> str:
    """Get top keywords (search queries) ranked by clicks from Google Search Console.

    When to use: User asks about keywords, search queries, what people search, keyword rankings, or keyword performance.
    Do NOT use for: Long-tail analysis (use report_long_tail), question queries (use report_questions), or keyword trends (use report_winner_loser).

    Returns: {_meta: {total, returned, truncated}, items: [{key, overall_clicks, overall_impressions, average_overall_position, average_overall_ctr, clicks_growth_rate, impressions_growth_rate, position_growth_rate}]}

    Tips:
    - Use country="tur" for Turkey-only data
    - Use page="/blog/" to see which keywords drive traffic to blog pages
    - Growth rates compare the first half vs second half of the date range

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        country: ISO 3166-1 alpha-3 country code (e.g. "tur" for Turkey, "usa" for US, "deu" for Germany)
        device: Filter by device — "desktop", "mobile", or "tablet"
        page: Filter keywords by page URL (contains match, e.g. "/blog/")
        limit: Max results (default 100, max 500)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/keywords", {
        "start_date": start_date, "end_date": end_date,
        "country": country, "device": device, "page": page, "limit": str(limit),
    })


@mcp.tool()
def get_pages(
    project_id: str,
    start_date: str,
    end_date: str,
    country: str = "",
    device: str = "",
    query: str = "",
    limit: int = 100,
) -> str:
    """Get top pages (URLs) ranked by clicks from Google Search Console.

    When to use: User asks about page performance, top URLs, best/worst performing pages, or which pages get the most traffic.
    Do NOT use for: Pages losing traffic (use report_content_decay), lowest performing pages (use report_thin_content).

    Returns: {_meta: {total, returned, truncated}, items: [{key (URL), overall_clicks, overall_impressions, average_overall_position, average_overall_ctr, clicks_growth_rate, ...}]}

    Tips:
    - Use query="seo" to find which pages rank for SEO-related keywords
    - Combine with get_keywords using page filter to see full keyword-page relationships

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        country: ISO 3166-1 alpha-3 country code
        device: Filter by device — "desktop", "mobile", or "tablet"
        query: Filter pages by keyword (contains match, e.g. "seo")
        limit: Max results (default 100, max 500)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/pages", {
        "start_date": start_date, "end_date": end_date,
        "country": country, "device": device, "query": query, "limit": str(limit),
    })


@mcp.tool()
def get_performance(
    project_id: str,
    start_date: str,
    end_date: str,
    country: str = "",
    device: str = "",
) -> str:
    """Get daily performance overview — clicks, impressions, CTR, position as a time series with summary.

    When to use: User asks "how is my site doing?", wants a traffic overview, daily breakdown, or period comparison.
    Do NOT use for: Individual keyword/page analysis (use get_keywords or get_pages).

    Returns: {data: [{keys: [date], clicks, impressions, ctr, position}], summary: {before: {total_clicks, total_impressions, average_ctr, average_position, days}, after: {...}, growth: {clicks_growth, impressions_growth, position_growth, ctr_growth}}}

    Tips:
    - The summary automatically splits the date range in half and compares before/after
    - Positive position_growth means positions got worse (higher number); negative means improvement

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        country: ISO 3166-1 alpha-3 country code
        device: Filter by device — "desktop", "mobile", or "tablet"
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/performance", {
        "start_date": start_date, "end_date": end_date,
        "country": country, "device": device,
    })


# ─── Search Console: Reports ─────────────────────────────


@mcp.tool()
def report_cannibalization(
    project_id: str,
    start_date: str,
    end_date: str,
    limit: int = 50,
) -> str:
    """Find keyword cannibalization — queries where multiple pages from the same site compete against each other in Google.

    When to use: User asks about cannibalization, duplicate rankings, competing pages, or "why is my traffic split between pages".

    Returns: {report, _meta, items: [{query, totalClicks, totalImpressions, averagePosition, ctr, issueType, pages: [{page (URL), clicks, impressions, averagePosition}]}]}

    Tips:
    - Each item shows one query and ALL pages competing for it
    - Fix by consolidating content, adding canonical tags, or redirecting weaker pages
    - 30-day date range usually gives the best results

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/keyword-cannibalization", {
        "start_date": start_date, "end_date": end_date, "limit": str(limit),
    })


@mcp.tool()
def report_monthly_summary(
    project_id: str,
    start_date: str,
    end_date: str,
) -> str:
    """Generate a comprehensive end-of-month SEO performance report.

    When to use: User asks for "monthly report", "SEO summary", "how was May", or any period comparison. Best for stakeholder reporting.

    Returns: A rich object with: top_queries (top 20), top_urls (top 20), query_winners, query_losers, page_winners, page_losers, top_20_new_pages, top_20_new_queries, current_summary, last_month_summary, last_year_summary, comparison_with_last_month, comparison_with_last_year, date_ranges.

    Tips:
    - Use first and last day of the month as dates (e.g. 2026-05-01 to 2026-05-31)
    - This report automatically compares with previous month AND previous year
    - All arrays are limited to 20 items each
    - Great for generating written SEO reports for clients

    Args:
        project_id: Project ID from list_projects
        start_date: First day of the month YYYY-MM-DD
        end_date: Last day of the month YYYY-MM-DD
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/end-of-month", {
        "start_date": start_date, "end_date": end_date,
    })


@mcp.tool()
def report_long_tail(
    project_id: str,
    start_date: str,
    end_date: str,
    condition: str = ">=3",
    limit: int = 50,
) -> str:
    """Find long-tail keyword opportunities — queries with 3+ words that often have lower competition.

    When to use: User asks about long-tail keywords, multi-word queries, niche keyword opportunities, or content gap analysis.
    Do NOT use for: General keyword listing (use get_keywords), question queries (use report_questions).

    Returns: {report, _meta, items: [{key (query), overall_clicks, overall_impressions, average_overall_position, average_overall_ctr, clicks_growth_rate, ...}]}

    Tips:
    - Default shows 3+ word queries; use condition=">=4" for even longer tail
    - Long-tail keywords often convert better — focus on ones with high impressions but low clicks
    - Sorted by clicks descending

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        condition: Word count filter — ">=3" (default), ">=4", ">=5", "==3", "==4"
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/long-tail", {
        "start_date": start_date, "end_date": end_date,
        "condition": condition, "limit": str(limit),
    })


@mcp.tool()
def report_winner_loser(
    project_id: str,
    start_date: str,
    end_date: str,
    metric: str = "clicks",
    limit: int = 50,
) -> str:
    """Identify which keywords gained or lost traffic by comparing two time periods.

    When to use: User asks "which keywords improved?", "what lost traffic?", "what's trending up/down?", or wants to understand traffic changes.

    Returns: {report, _meta, items: [{query, firstPeriodTotal, secondPeriodTotal, change, status}]}
    - status is one of: "Winner" (grew), "Loser" (declined), "New" (appeared in 2nd period), "Lost" (disappeared), "Stable"

    Tips:
    - Date range is split in half automatically (first half = period 1, second half = period 2)
    - Use 60-day range for meaningful before/after comparison
    - metric="position" inverts the logic (lower position = better)

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        metric: What to compare — "clicks" (default), "impressions", or "position"
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/winner-loser", {
        "start_date": start_date, "end_date": end_date,
        "metric": metric, "limit": str(limit),
    })


@mcp.tool()
def report_questions(
    project_id: str,
    start_date: str,
    end_date: str,
    language: str = "TR",
    limit: int = 50,
) -> str:
    """Find question-type search queries that bring users to the site.

    When to use: User asks about questions people search, FAQ opportunities, "People Also Ask" targets, or content ideas based on user questions.
    Do NOT use for: General keyword listing (use get_keywords).

    Returns: {report, _meta, items: [{key (question query), overall_clicks, overall_impressions, average_overall_position, average_overall_ctr, ...}]}

    Tips:
    - Turkish question words: nasil, neden, ne zaman, nerede, kim, hangi, ne kadar
    - English question words: how, why, when, where, who, which, what
    - Great for creating FAQ sections and blog content that answers real user questions

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        language: Question word detection language — "TR" (Turkish, default) or "EN" (English)
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/questions", {
        "start_date": start_date, "end_date": end_date,
        "language": language, "limit": str(limit),
    })


@mcp.tool()
def report_content_decay(
    project_id: str,
    start_date: str,
    end_date: str,
    limit: int = 50,
) -> str:
    """Find pages that are losing traffic over time (content decay analysis).

    When to use: User asks about declining pages, content that needs refreshing, "which pages are dying", or content update priorities.
    Do NOT use for: Currently low-traffic pages (use report_thin_content) — content decay specifically tracks DECLINE from a peak.

    Returns: {report, _meta, items: [{url, isHaveDecay (bool), lostClicks (total clicks lost from peak), statsByMonth: {"2026-01": {clicks, impressions, position, decayStart}}}]}

    Tips:
    - USE A 6-12 MONTH DATE RANGE for best results (this report needs enough history to detect trends)
    - Pages are sorted by lostClicks descending (biggest losses first)
    - decayStart=true marks the month when decline began
    - Recommend the user refresh/update these pages with new content

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD (6-12 months ago recommended)
        end_date: End date YYYY-MM-DD
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/content-decay", {
        "start_date": start_date, "end_date": end_date, "limit": str(limit),
    })


@mcp.tool()
def report_striking_distance(
    project_id: str,
    start_date: str,
    end_date: str,
    limit: int = 50,
) -> str:
    """Find "striking distance" keywords — ranking positions 11-30 (Google page 2-3). These are quick wins.

    When to use: User asks about "quick wins", "easy improvements", "almost ranking", "page 2 keywords", or "low-hanging fruit".

    Returns: {report, _meta, items: [{key (query), overall_clicks, overall_impressions, average_overall_position (11-30), average_overall_ctr, clicks_growth_rate, ...}]}

    Tips:
    - These keywords are close to page 1 — small optimizations can push them up
    - Focus on high-impression items first (more potential traffic)
    - Recommend: improve content, add internal links, optimize title/meta for these queries
    - 30-day date range works best

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/striking-distance", {
        "start_date": start_date, "end_date": end_date, "limit": str(limit),
    })


@mcp.tool()
def report_low_ctr(
    project_id: str,
    start_date: str,
    end_date: str,
    type: str = "query",
    limit: int = 50,
) -> str:
    """Find keywords or pages with low click-through rate that could be improved.

    When to use: User asks about CTR optimization, "why aren't people clicking?", title/description improvements, or snippet optimization.

    Returns: {report, _meta, items: [{key, overall_clicks, overall_impressions, average_overall_position, average_overall_ctr, extra_checks: {improvable: true, potential_additional_clicks: N}, ...}]}

    Tips:
    - Only returns items marked as "improvable" (already filtered)
    - potential_additional_clicks estimates how many more clicks if CTR reaches 5%
    - Sorted by potential_additional_clicks descending (biggest opportunities first)
    - Recommend: rewrite title tags and meta descriptions for these items
    - Use type="page" to see which URLs need better titles across all their keywords

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        type: Analyze by "query" (default) or "page"
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/low-ctr", {
        "start_date": start_date, "end_date": end_date,
        "type": type, "limit": str(limit),
    })


@mcp.tool()
def report_thin_content(
    project_id: str,
    start_date: str,
    end_date: str,
    type: str = "query",
    limit: int = 50,
) -> str:
    """Find the lowest-performing content — pages or queries with the least traffic.

    When to use: User asks about underperforming content, content audit, "what should I delete or merge", or wants to clean up their site.
    Do NOT use for: Pages that USED TO perform well (use report_content_decay).

    Returns: {report, _meta, items: [{key, overall_clicks, overall_impressions, average_overall_position, average_overall_ctr, clicks_growth_rate, ...}]}

    Tips:
    - Sorted by clicks ascending (worst performers first)
    - Use type="page" for page-level audit (most useful for content cleanup)
    - Recommend: merge similar thin pages, add more content, or redirect/remove
    - Pages with 0 clicks and high impressions might have indexing or CTR issues

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        type: Analyze by "query" (default) or "page"
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/search-console/reports/thin-content", {
        "start_date": start_date, "end_date": end_date,
        "type": type, "limit": str(limit),
    })


# ─── Google Analytics: Data ────────────────────────────────


@mcp.tool()
def ga_get_overview(
    project_id: str,
    start_date: str,
    end_date: str,
    compare_with_previous: bool = False,
) -> str:
    """Get Google Analytics overview — core metrics for the site.

    When to use: User asks "how is my traffic?", "analytics overview", "site summary", visitor stats, or general performance from GA.
    Do NOT use for: Daily traffic trends (use ga_report_traffic_trends), traffic sources (use ga_get_traffic_sources).

    Returns: {metrics: {total_users, new_users, sessions, screen_page_views, engaged_sessions, average_session_duration, bounce_rate, engagement_rate, sessions_per_user, events_per_session}, period, realtime: {active_users}}
    With compare_with_previous=true also returns: {comparison: {users_change, sessions_change, page_views_change, bounce_rate_change, avg_session_duration_change, engagement_rate_change}, previous_period}

    Tips:
    - Use compare_with_previous=true for "how did this month compare to last month" type questions
    - Realtime active users shows who is on the site RIGHT NOW
    - bounce_rate and engagement_rate are percentages (0-100)

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        compare_with_previous: Include previous period comparison (default false)
    """
    params = {
        "start_date": start_date,
        "end_date": end_date,
    }
    if compare_with_previous:
        params["compare_with_previous"] = "true"
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/overview", params)


@mcp.tool()
def ga_get_traffic_sources(
    project_id: str,
    start_date: str,
    end_date: str,
    dimension: str = "channel",
    limit: int = 20,
) -> str:
    """Get traffic source breakdown from Google Analytics.

    When to use: User asks "where does my traffic come from?", traffic channels, sources, referrers, campaigns, or acquisition analysis.

    Returns: {_meta: {total, returned, dimension}, items: [{name, sessions, users, percentage}]}

    Tips:
    - channel: High-level grouping (Organic Search, Direct, Paid Search, Social, Referral, Email)
    - source: Specific sources (google, facebook, twitter, direct)
    - medium: Traffic medium (organic, cpc, referral, email)
    - campaign: UTM campaign names
    - referrer: Referring domains

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        dimension: What to group by — "channel" (default), "source", "medium", "campaign", "referrer"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/traffic", {
        "start_date": start_date, "end_date": end_date,
        "dimension": dimension, "limit": str(limit),
    })


@mcp.tool()
def ga_get_pages(
    project_id: str,
    start_date: str,
    end_date: str,
    type: str = "top",
    limit: int = 20,
) -> str:
    """Get page performance data from Google Analytics.

    When to use: User asks about most visited pages, top landing pages, exit pages, or page-level traffic data.
    Do NOT use for: Page engagement quality (use ga_report_engagement_analysis), SEO page performance (use get_pages from Search Console).

    Returns: {_meta: {total, returned, type}, items: [{path, title, views, percentage}]}

    Tips:
    - top: Pages by total pageviews
    - entry: Landing pages (first page visitors see) — sorted by sessions
    - exit: Last pages visitors see before leaving — helps identify where users drop off

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        type: Page type — "top" (default), "entry", "exit"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/pages", {
        "start_date": start_date, "end_date": end_date,
        "type": type, "limit": str(limit),
    })


@mcp.tool()
def ga_get_geo(
    project_id: str,
    start_date: str,
    end_date: str,
    dimension: str = "country",
    limit: int = 20,
) -> str:
    """Get geographic breakdown of visitors from Google Analytics.

    When to use: User asks "where are my visitors from?", country breakdown, regional data, city-level traffic.

    Returns: {_meta: {total, returned, dimension}, items: [{name, users, sessions, percentage}]}

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        dimension: Geographic level — "country" (default), "region", "city"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/geo", {
        "start_date": start_date, "end_date": end_date,
        "dimension": dimension, "limit": str(limit),
    })


@mcp.tool()
def ga_get_devices(
    project_id: str,
    start_date: str,
    end_date: str,
    dimension: str = "category",
    limit: int = 20,
) -> str:
    """Get device, browser, or OS breakdown from Google Analytics.

    When to use: User asks about mobile vs desktop, browser stats, operating system breakdown, or device usage.

    Returns: {_meta: {total, returned, dimension}, items: [{name, users, sessions, percentage}]}

    Tips:
    - category: Desktop, Mobile, Tablet (most common use)
    - browser: Chrome, Safari, Firefox, Edge, etc.
    - os: Windows, macOS, iOS, Android, Linux, etc.

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        dimension: What to group by — "category" (default), "browser", "os"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/devices", {
        "start_date": start_date, "end_date": end_date,
        "dimension": dimension, "limit": str(limit),
    })


@mcp.tool()
def ga_get_key_events(
    project_id: str,
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> str:
    """Get key events (conversions) from Google Analytics.

    When to use: User asks about conversions, goals, key events, leads, signups, purchases, or any business outcomes tracked in GA4.

    Returns: {_meta: {total, returned, total_key_events}, items: [{event_name, key_events, percentage}]}

    Tips:
    - Key events are GA4's replacement for goals/conversions
    - Common key events: form_submit, purchase, sign_up, generate_lead, add_to_cart
    - percentage shows each event's share of total key events
    - If empty, the user may not have configured key events in GA4

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        limit: Max results (default 20, max 50)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/key-events", {
        "start_date": start_date, "end_date": end_date,
        "limit": str(limit),
    })


# ─── Google Analytics: Reports ────────────────────────────


@mcp.tool()
def ga_report_traffic_trends(
    project_id: str,
    start_date: str,
    end_date: str,
) -> str:
    """Analyze traffic trends — daily metrics with growth analysis, peak/trough detection, weekday vs weekend patterns.

    When to use: User asks "is my traffic growing?", "traffic trends", "daily breakdown", or wants to understand traffic patterns over time.
    Do NOT use for: One-time snapshot (use ga_get_overview), source breakdown (use ga_get_traffic_sources).

    Returns: {report, summary: {total_days, total_users, total_sessions, avg_daily_users, avg_daily_sessions, users_growth_rate, sessions_growth_rate, views_growth_rate, peak_day: {date, users}, trough_day: {date, users}, avg_weekday_users, avg_weekend_users}, daily_metrics: [{date, total_users, sessions, screen_page_views, bounce_rate, average_session_duration}], period}

    Tips:
    - Growth rates compare 2nd half vs 1st half of the date range — positive = growing, negative = declining
    - Use 30+ day range for meaningful trend analysis
    - Peak/trough days help identify anomalies or events that drove traffic spikes

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/reports/traffic-trends", {
        "start_date": start_date, "end_date": end_date,
    })


@mcp.tool()
def ga_report_landing_page_performance(
    project_id: str,
    start_date: str,
    end_date: str,
    event_name: str = "",
    limit: int = 50,
) -> str:
    """Analyze landing page conversion performance — which pages drive the most conversions from organic search.

    When to use: User asks "which pages convert best?", "landing page performance", "conversion rate by page", "SEO ROI", or wants to connect traffic to business outcomes.
    Do NOT use for: General page traffic (use ga_get_pages), page engagement (use ga_report_engagement_analysis).

    Returns: {report, summary: {total_pages, total_key_events, overall_conversion_rate, pages_with_conversions, optimization_opportunities}, top_converters: [{landing_page, sessions, key_events, conversion_rate}], opportunities: [{landing_page, sessions, key_events, conversion_rate}], period}

    Tips:
    - Filtered to ORGANIC SEARCH traffic only (most relevant for SEO)
    - top_converters: pages that have conversions — sorted by key_events
    - opportunities: pages with 10+ sessions but ZERO conversions — high traffic, no conversion = optimization target
    - Use event_name to filter by specific conversion (e.g. "form_submit", "purchase")
    - If no data, user may not have key events configured in GA4

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        event_name: Filter by specific event name (optional, e.g. "purchase")
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/reports/landing-page-performance", {
        "start_date": start_date, "end_date": end_date,
        "event_name": event_name, "limit": str(limit),
    })


@mcp.tool()
def ga_report_channel_comparison(
    project_id: str,
    start_date: str,
    end_date: str,
) -> str:
    """Compare traffic channels with automatic previous period comparison — see which channels are growing or declining.

    When to use: User asks "organic vs paid", "channel comparison", "which channels are growing?", "how is organic doing?", or monthly channel review.

    Returns: {report, _meta, items: [{name, sessions, users, percentage, previous_sessions, previous_users, sessions_change, users_change}], period, previous_period}

    Tips:
    - Automatically compares with the previous period (same duration, just before)
    - sessions_change and users_change are percentage changes (positive = growth)
    - Common channels: Organic Search, Direct, Paid Search, Social, Referral, Email, Display
    - Focus on Organic Search channel for SEO impact analysis

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/reports/channel-comparison", {
        "start_date": start_date, "end_date": end_date,
    })


@mcp.tool()
def ga_report_engagement_analysis(
    project_id: str,
    start_date: str,
    end_date: str,
    limit: int = 30,
) -> str:
    """Analyze page engagement quality — categorize pages into high/medium/low engagement tiers.

    When to use: User asks about engagement, bounce rate by page, "which pages keep visitors?", time on page, or content quality analysis.
    Do NOT use for: Page traffic volumes (use ga_get_pages), conversion rates (use ga_report_landing_page_performance).

    Returns: {report, summary: {total_pages, site_avg_engagement_time, site_bounce_rate, site_engagement_rate, high_engagement_pages, needs_improvement_pages, low_engagement_pages}, high_engagement: [...], needs_improvement: [...], low_engagement: [...], period}

    Each page: {page_path, page_title, screen_page_views, users, average_engagement_time, engagement_tier}

    Tips:
    - Tiers based on comparison to site average engagement time:
      - high: >=1.5x site average
      - needs_improvement: 0.5-1.5x site average
      - low: <0.5x site average
    - Focus on low engagement pages with high traffic — these are content quality issues
    - average_engagement_time is in seconds

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        limit: Max pages to analyze (default 30, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/analytics/reports/engagement-analysis", {
        "start_date": start_date, "end_date": end_date,
        "limit": str(limit),
    })


# ─── Google Ads: Data ──────────────────────────────────────


@mcp.tool()
def gads_get_campaigns(
    project_id: str,
    start_date: str,
    end_date: str,
    campaign_type: str = "",
    sort_by: str = "cost",
    limit: int = 50,
) -> str:
    """Get Google Ads campaign performance data.

    When to use: User asks "how are my campaigns?", "campaign performance", "best/worst campaigns", or wants to see ad campaign metrics.
    Do NOT use for: Daily trends (use gads_get_daily_metrics), search terms (use gads_get_search_terms).

    Returns: {_meta, currency, items: [{id, name, type, status, budget_amount, impressions, clicks, cost, ctr, cpc, conversions, conversion_value, conversion_rate, cpa, roas}]}

    Tips:
    - Campaign types: SEARCH, PERFORMANCE_MAX, DISPLAY, VIDEO, SHOPPING
    - ROAS > 4 is excellent, ROAS < 1 means losing money
    - Sort by "roas" to find best-performing campaigns, by "cost" to find biggest spenders

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        campaign_type: Filter by type — "" (all), "SEARCH", "PERFORMANCE_MAX", "DISPLAY", "VIDEO", "SHOPPING"
        sort_by: Sort campaigns — "cost" (default), "conversions", "roas", "impressions", "clicks"
        limit: Max results (default 50, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/campaigns", {
        "start_date": start_date, "end_date": end_date,
        "campaign_type": campaign_type, "sort_by": sort_by, "limit": str(limit),
    })


@mcp.tool()
def gads_get_daily_metrics(
    project_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str = "",
) -> str:
    """Get daily Google Ads metrics — impressions, clicks, cost, conversions as a time series.

    When to use: User asks about "daily ad spend", "ad performance over time", "spend trends", or wants a daily breakdown.
    Do NOT use for: Campaign listing (use gads_get_campaigns), one-time summary (use gads_report_performance_overview).

    Returns: {_meta, currency, items: [{date, impressions, clicks, cost, conversions, conversion_value, ctr, cpc, roas, cpa}]}

    Tips:
    - Leave campaign_id empty to see account-wide totals (aggregated across all campaigns)
    - Use a specific campaign_id from gads_get_campaigns to drill into one campaign
    - Great for spotting spend anomalies and trend changes

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        campaign_id: Specific campaign ID, or empty for all campaigns aggregated
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/daily", {
        "start_date": start_date, "end_date": end_date,
        "campaign_id": campaign_id,
    })


@mcp.tool()
def gads_get_geo(
    project_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str = "",
    limit: int = 20,
) -> str:
    """Get Google Ads performance by country/geographic location.

    When to use: User asks about "ad performance by country", "geographic targeting", "which countries convert best".

    Returns: {_meta, currency, items: [{country_name, country_code, impressions, clicks, cost, conversions, conversion_value, ctr, cpc, conversion_rate, roas, cpa}]}

    Tips:
    - Leave campaign_id empty for account-wide geographic breakdown
    - Sorted by impressions descending (most traffic first)
    - Use to identify profitable markets or wasteful geo targeting

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        campaign_id: Specific campaign ID, or empty for all campaigns
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/geo", {
        "start_date": start_date, "end_date": end_date,
        "campaign_id": campaign_id, "limit": str(limit),
    })


@mcp.tool()
def gads_get_devices(
    project_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str = "",
) -> str:
    """Get Google Ads performance by device type (mobile, desktop, tablet).

    When to use: User asks about "mobile vs desktop ads", "device performance", "which devices convert best".

    Returns: {_meta, currency, items: [{device, impressions, clicks, cost, conversions, conversion_value, ctr, cpc, conversion_rate, roas, cpa}]}

    Tips:
    - Leave campaign_id empty for account-wide device breakdown
    - Compare CPA and ROAS across devices to optimize bid adjustments
    - If mobile CPA is much higher, consider mobile bid reduction

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        campaign_id: Specific campaign ID, or empty for all campaigns
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/devices", {
        "start_date": start_date, "end_date": end_date,
        "campaign_id": campaign_id,
    })


@mcp.tool()
def gads_get_search_terms(
    project_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str = "",
    limit: int = 50,
) -> str:
    """Get actual search terms that triggered Google Ads (Search campaigns only).

    When to use: User asks "what search terms trigger my ads?", "keyword performance", "negative keyword ideas", "search query report".
    Do NOT use for: Organic search keywords (use get_keywords from Search Console).

    Returns: {_meta, currency, items: [{search_term, status, impressions, clicks, cost, conversions, conversion_value, ctr, cpc, conversion_rate, roas, cpa}]}

    Tips:
    - Only available for Search campaigns (not Performance Max, Display, Video)
    - Leave campaign_id empty to get search terms across ALL Search campaigns
    - Look for high-cost, zero-conversion terms → add as negative keywords
    - Compare with organic keywords (get_keywords) to find paid/organic overlap
    - status shows if the term is added as a keyword or not

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        campaign_id: Specific Search campaign ID, or empty for all Search campaigns
        limit: Max results (default 50, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/search-terms", {
        "start_date": start_date, "end_date": end_date,
        "campaign_id": campaign_id, "limit": str(limit),
    })


# ─── Google Ads: Reports ──────────────────────────────────


@mcp.tool()
def gads_report_performance_overview(
    project_id: str,
    start_date: str,
    end_date: str,
    compare_with_previous: bool = False,
) -> str:
    """Get a comprehensive Google Ads performance overview with campaign rankings and type breakdown.

    When to use: User asks "how are my ads doing?", "ads overview", "ad account summary", or wants a high-level advertising report.
    Do NOT use for: Individual campaign details (use gads_get_campaigns), daily trends (use gads_get_daily_metrics).

    Returns: {report, summary: {total_impressions, total_clicks, total_cost, total_conversions, total_conversion_value, overall_ctr, overall_cpc, overall_cpa, overall_roas, campaign_count, currency}, top_campaigns: [{name, type, cost, roas, conversions}], by_type: [{type, campaign_count, cost, cost_share_pct, conversions, roas}], period}
    With compare_with_previous=true: also returns comparison with % changes and previous_period dates.

    Tips:
    - top_campaigns: Top 5 by ROAS — shows best-performing campaigns
    - by_type: Breakdown by campaign type (SEARCH, PMAX, DISPLAY, etc.) with cost share
    - Use comparison to answer "how did this month compare to last month?"

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        compare_with_previous: Include previous period comparison (default false)
    """
    params = {
        "start_date": start_date,
        "end_date": end_date,
    }
    if compare_with_previous:
        params["compare_with_previous"] = "true"
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/reports/performance-overview", params)


@mcp.tool()
def gads_report_spend_analysis(
    project_id: str,
    start_date: str,
    end_date: str,
) -> str:
    """Analyze Google Ads spending — daily spend trends, per-campaign cost breakdown, and ROI metrics.

    When to use: User asks "how much am I spending?", "spend breakdown", "where is my budget going?", "daily ad spend".

    Returns: {report, summary: {total_cost, total_conversions, total_conversion_value, total_impressions, total_clicks, avg_daily_spend, overall_roas, overall_cpa, currency, days}, daily_spend: [{date, cost, conversions, roas}], by_campaign: [{name, type, cost, cost_share_pct, conversions, roas}], period}

    Tips:
    - daily_spend shows spend over time — look for unusual spikes
    - by_campaign shows which campaigns consume the most budget
    - cost_share_pct shows what % of total budget each campaign uses
    - Compare ROAS across campaigns to identify where budget is well/poorly spent

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/reports/spend-analysis", {
        "start_date": start_date, "end_date": end_date,
    })


@mcp.tool()
def gads_report_conversion_breakdown(
    project_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str = "",
) -> str:
    """Get conversion breakdown by action type — see which conversion actions are firing and their values.

    When to use: User asks "conversion breakdown", "which conversions am I getting?", "conversion types", "conversion actions".

    Returns: {report, _meta, summary: {total_conversions, total_conversion_value}, currency, items: [{conversion_action_name, conversions, conversions_value}], period}

    Tips:
    - Shows all configured conversion actions (purchase, form_submit, phone_call, etc.)
    - Leave campaign_id empty for account-wide conversion data
    - If empty, user may not have conversion tracking configured
    - Use to identify which conversion types drive the most value

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        campaign_id: Specific campaign ID, or empty for all campaigns
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ads/reports/conversions", {
        "start_date": start_date, "end_date": end_date,
        "campaign_id": campaign_id,
    })


# ─── Rank Tracker: Data ────────────────────────────────────


@mcp.tool()
def rank_get_keywords(
    project_id: str,
    device: str = "mobile",
    search: str = "",
    location: str = "",
    trend: str = "",
    limit: int = 50,
) -> str:
    """Get keyword rankings from the Rank Tracker — current positions, changes, and search volume.

    When to use: User asks "where do I rank?", "show my rankings", "keyword positions", "which keywords am I ranking for?".
    Do NOT use for: Search Console keyword data (use get_keywords), ad keyword data (use gads_get_search_terms).

    Returns: {_meta, items: [{query, location, device, position, change_1d, change_7d, change_30d, is_ranking, search_volume}]}

    Tips:
    - position: current Google ranking (1 = first result). 0 = not ranking.
    - change_1d/7d/30d: positive = improved (moved UP), negative = dropped
    - Use trend="rising" to find improving keywords, trend="falling" for declining
    - Combine with get_keywords (GSC) for impressions/clicks data on the same keywords

    Args:
        project_id: Project ID from list_projects
        device: Device type — "mobile" (default) or "desktop"
        search: Filter keywords by text (contains match)
        location: Filter by tracking location
        trend: Filter by trend — "" (all), "rising", "falling", "stable", "not_ranking"
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/rank-tracker/keywords", {
        "device": device, "search": search, "location": location,
        "trend": trend, "limit": str(limit),
    })


@mcp.tool()
def rank_get_overview(
    project_id: str,
    device: str = "mobile",
) -> str:
    """Get ranking overview — distribution, visibility score, and yesterday's changes.

    When to use: User asks "how are my rankings?", "ranking overview", "ranking distribution", "visibility score".

    Returns: {summary: {total_tracked, ranking, not_ranking, average_position, visibility_score}, distribution: {top_3, top_10, top_20, top_30, top_100, not_ranking}, yesterday_changes: {improved, declined, no_change}, device}

    Tips:
    - visibility_score: 0-100%, weighted by position (top 1-3 positions = highest weight)
    - distribution shows how many keywords are in each position range
    - yesterday_changes shows ranking movement from the last crawl
    - If total_tracked = 0, user needs to add keywords in Semust > Rank Tracker

    Args:
        project_id: Project ID from list_projects
        device: Device type — "mobile" (default) or "desktop"
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/rank-tracker/overview", {
        "device": device,
    })


@mcp.tool()
def rank_get_history(
    project_id: str,
    device: str = "mobile",
    days: int = 30,
) -> str:
    """Get daily average position history — track ranking trends over time.

    When to use: User asks "are my rankings improving?", "ranking trends", "average position history", "position over time".

    Returns: {_meta, items: [{date, avg_position, total_queries}]}

    Tips:
    - avg_position: lower is better (position 1 = best)
    - Decreasing avg_position over time = rankings are improving
    - Use 30-90 days for meaningful trend analysis
    - Compare with get_performance (GSC) to correlate ranking changes with traffic changes

    Args:
        project_id: Project ID from list_projects
        device: Device type — "mobile" (default) or "desktop"
        days: Number of days of history (default 30, max 90)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/rank-tracker/history", {
        "device": device, "days": str(days),
    })


@mcp.tool()
def rank_report_gainers_losers(
    project_id: str,
    device: str = "mobile",
    period: str = "7d",
    limit: int = 20,
) -> str:
    """Find keywords that gained or lost rankings — biggest movers in the selected period.

    When to use: User asks "which keywords improved?", "which keywords dropped?", "ranking winners/losers", "biggest ranking changes".

    Returns: {report, period, device, gainers: {count, items: [{query, position, change, is_ranking}]}, losers: {count, items: [...]}}

    Tips:
    - change > 0 = moved UP in rankings (improved). change < 0 = dropped.
    - period="1d" for yesterday's changes, "7d" for weekly, "30d" for monthly
    - Focus on high-volume keywords that dropped — those need attention first

    Args:
        project_id: Project ID from list_projects
        device: Device type — "mobile" (default) or "desktop"
        period: Time period — "1d" (yesterday), "7d" (default, last week), "30d" (last month)
        limit: Max results per group (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/rank-tracker/reports/gainers-losers", {
        "device": device, "period": period, "limit": str(limit),
    })


@mcp.tool()
def rank_report_distribution(
    project_id: str,
    device: str = "mobile",
) -> str:
    """Get ranking position distribution — how many keywords in each position range.

    When to use: User asks "how many keywords on page 1?", "ranking distribution", "position breakdown".

    Returns: {report, device, total_tracked, distribution: [{range, count, percentage}]}
    Ranges: "1-3", "4-10", "11-20", "21-30", "31-100", "Not Ranking"

    Tips:
    - "1-3" = top of page 1 (best visibility)
    - "4-10" = rest of page 1 (good visibility)
    - "11-20" = page 2 (striking distance — optimize these!)
    - "Not Ranking" = not found in top 100

    Args:
        project_id: Project ID from list_projects
        device: Device type — "mobile" (default) or "desktop"
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/rank-tracker/reports/distribution", {
        "device": device,
    })


# ─── AI Rank Tracker ──────────────────────────────────────


@mcp.tool()
def ai_rank_get_overview(
    project_id: str,
) -> str:
    """Get AI Overview visibility summary — how often your site appears in Google's AI-generated answers.

    When to use: User asks "AI visibility", "am I in AI Overviews?", "AI overview performance", "AI search presence".

    Returns: {summary: {total_queries, in_ai_overview, not_in_ai_overview, pending, top_3, top_5, top_10, visibility_score}, project_url}

    Tips:
    - visibility_score: 0-100%, weighted by position in AI Overview (position 1 = 10 points, position 10 = 1 point)
    - in_ai_overview: number of tracked queries where your site is cited in the AI answer
    - AI Overviews appear for ~15-30% of queries — being cited is increasingly important for traffic
    - If no data, user needs to add keywords in Semust > AI Rank Tracker

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ai-rank-tracker/overview")


@mcp.tool()
def ai_rank_get_keywords(
    project_id: str,
    search: str = "",
    location: str = "",
    limit: int = 50,
) -> str:
    """Get AI Overview tracking data per keyword — which queries show your site in AI answers.

    When to use: User asks "which queries have AI overviews?", "AI overview keywords", "where does my site appear in AI?".

    Returns: {_meta, items: [{query, location, device, position, change_1d, change_7d, change_30d, in_ai_overview, crawl_status}]}

    Tips:
    - position > 0 = your site appears at that position in the AI Overview
    - position = 0 = your site is NOT cited in the AI answer for this query
    - in_ai_overview: true/false for quick filtering
    - change_1d/7d/30d: position changes (positive = improved)
    - Compare with rank_get_keywords to see how AI visibility differs from traditional rankings

    Args:
        project_id: Project ID from list_projects
        search: Filter keywords by text (contains match)
        location: Filter by tracking location
        limit: Max results (default 50, max 200)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ai-rank-tracker/keywords", {
        "search": search, "location": location, "limit": str(limit),
    })


@mcp.tool()
def ai_rank_get_domains(
    project_id: str,
    limit: int = 10,
) -> str:
    """Get top domains appearing in AI Overviews — see which competitors are cited most in AI answers.

    When to use: User asks "which competitors appear in AI?", "top domains in AI overviews", "AI competitor analysis".

    Returns: {_meta, project_url, items: [{domain, appearance_count, avg_position, is_our_domain}]}

    Tips:
    - is_our_domain: true if this is the user's own domain
    - appearance_count: how many tracked queries cite this domain
    - avg_position: average position within AI Overviews (lower = more prominent)
    - Domains NOT in your list = competitors who are being cited instead of you

    Args:
        project_id: Project ID from list_projects
        limit: Max results (default 10, max 50)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/ai-rank-tracker/domains", {
        "limit": str(limit),
    })


# ─── Indexing Monitor ─────────────────────────────────────


@mcp.tool()
def indexing_get_status(
    project_id: str,
) -> str:
    """Get URL indexing status — health score, indexed/not-indexed counts, coverage breakdown, and warnings.

    When to use: User asks "are my pages indexed?", "indexing status", "indexing health", "which pages are not indexed?".

    Returns: {health_score: {score, indexing_rate, crawl_freshness, warning_count}, counts: {total, indexed, not_indexed, never_checked, warnings}, coverage_groups: [{state, count}], recent_alerts: {deindexed_count, reindexed_count, stale_crawl_count}, not_indexed_urls: [{url, coverage_state, warning_type}]}

    Tips:
    - health_score 80-100: excellent. 60-80: good. 40-60: needs attention. <40: critical issues.
    - indexing_rate: % of monitored URLs that are indexed (higher = better)
    - crawl_freshness: % of URLs crawled within last 30 days
    - coverage_groups: INDEXED, SUBMITTED, EXCLUDED, etc. (from Google)
    - not_indexed_urls: up to 10 URLs that are NOT indexed — check these first
    - warning_type: "blocked" (robots/meta), "canonical_mismatch", "stale_crawl" (120+ days)
    - If no data, user needs to set up monitoring in Semust > Search Console > Indexing Monitor

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/indexing-monitor/status")


@mcp.tool()
def indexing_get_history(
    project_id: str,
    days: int = 30,
) -> str:
    """Get indexing history — daily indexed/not-indexed counts over time.

    When to use: User asks "indexing trends", "indexing history", "are more pages getting indexed?".

    Returns: {_meta, items: [{date, indexed_count, not_indexed_count, warning_count}]}

    Tips:
    - Increasing indexed_count over time = pages are getting picked up by Google
    - Sudden drops in indexed_count = possible deindexing issue — check recent_alerts via indexing_get_status
    - warning_count trending up = growing technical issues (blocked pages, canonical mismatches)

    Args:
        project_id: Project ID from list_projects
        days: Number of days of history (default 30, max 60)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/indexing-monitor/history", {
        "days": str(days),
    })


# ─── Yandex Metrica ───────────────────────────────────────


@mcp.tool()
def ym_get_overview(
    project_id: str,
    start_date: str,
    end_date: str,
    compare_with_previous: bool = False,
) -> str:
    """Get Yandex Metrica analytics overview — visitors, visits, pageviews, bounce rate, daily trends, top sources/pages/geo/devices/search phrases.

    When to use: User asks about Yandex traffic, Yandex analytics, Yandex Metrica overview, or Russian/Turkish market analytics.
    Do NOT use for: Google Analytics data (use ga_get_overview), Google Search Console data (use get_performance).

    Returns: {counter_id, counter_name, period, metrics: {visitors, visits, pageviews, new_users, bounce_rate, avg_duration, page_depth}, daily_metrics: [...], sources: [...], pages_top: [...], geo_countries: [...], device_categories: [...], search_phrases: [...], traffic_source_breakdown: {...}}
    With compare_with_previous=true also returns: {comparison: {visitors_change, visits_change, ...}, previous_period}

    Tips:
    - Yandex Metrica data is near real-time (use today - 1 day as end_date)
    - Set compare_with_previous=true for period-over-period comparison
    - This is the most comprehensive Yandex tool — start here for any Yandex question
    - Compare with ga_get_overview and get_performance for cross-platform analysis

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        compare_with_previous: Compare with previous period of same length (default false)
    """
    params = {"start_date": start_date, "end_date": end_date}
    if compare_with_previous:
        params["compare_with_previous"] = "true"
    return api_get(f"/projects/{_safe_project_id(project_id)}/yandex-metrica/overview", params)


@mcp.tool()
def ym_get_traffic(
    project_id: str,
    start_date: str,
    end_date: str,
    filter: str = "sources",
    limit: int = 20,
) -> str:
    """Get Yandex Metrica traffic source data — where visitors come from.

    When to use: User asks about Yandex traffic sources, referrers, which search engines drive Yandex traffic.

    Returns: {_meta: {total, returned, filter}, items: [{name, value (visits), second_value (users), percentage}]}

    Tips:
    - sources: All traffic sources (organic, direct, social, etc.)
    - search_engines: Only search engine traffic (Yandex, Google, etc.)
    - social: Only social media traffic

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        filter: "sources" (default), "search_engines", or "social"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/yandex-metrica/traffic", {
        "start_date": start_date, "end_date": end_date,
        "filter": filter, "limit": str(limit),
    })


@mcp.tool()
def ym_get_pages(
    project_id: str,
    start_date: str,
    end_date: str,
    filter: str = "top",
    limit: int = 20,
) -> str:
    """Get Yandex Metrica page performance data.

    When to use: User asks about top pages in Yandex, landing pages, exit pages from Yandex analytics.

    Returns: {_meta: {total, returned, filter}, items: [{name (URL or title), value (pageviews), second_value (visits), percentage}]}

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        filter: "top" (default), "landing", "exit", or "titles"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/yandex-metrica/pages", {
        "start_date": start_date, "end_date": end_date,
        "filter": filter, "limit": str(limit),
    })


@mcp.tool()
def ym_get_geo(
    project_id: str,
    start_date: str,
    end_date: str,
    filter: str = "countries",
    limit: int = 20,
) -> str:
    """Get Yandex Metrica geographic visitor data.

    When to use: User asks about visitor locations in Yandex, geographic breakdown from Yandex Metrica.

    Returns: {_meta: {total, returned, filter}, items: [{name, value (visits), second_value (users), percentage}]}

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        filter: "countries" (default), "regions", or "cities"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/yandex-metrica/geo", {
        "start_date": start_date, "end_date": end_date,
        "filter": filter, "limit": str(limit),
    })


@mcp.tool()
def ym_get_devices(
    project_id: str,
    start_date: str,
    end_date: str,
    filter: str = "device",
    limit: int = 20,
) -> str:
    """Get Yandex Metrica device/browser/OS breakdown.

    When to use: User asks about device types, browsers, or operating systems from Yandex analytics.

    Returns: {_meta: {total, returned, filter}, items: [{name, value (visits), second_value (users), percentage}]}

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        filter: "device" (default), "browser", or "os"
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/yandex-metrica/devices", {
        "start_date": start_date, "end_date": end_date,
        "filter": filter, "limit": str(limit),
    })


@mcp.tool()
def ym_get_search_phrases(
    project_id: str,
    start_date: str,
    end_date: str,
    limit: int = 20,
) -> str:
    """Get Yandex Metrica search phrases — keywords visitors used to find the site via Yandex search.

    When to use: User asks about Yandex search keywords, search phrases from Yandex, what people search on Yandex.
    Do NOT use for: Google search keywords (use get_keywords), Bing keywords (use bing_get_query_stats).

    Returns: {_meta: {total, returned}, items: [{phrase, visits, users, percentage}]}

    Tips:
    - Compare with Google Search Console keywords (get_keywords) to see search engine differences
    - Yandex search phrases are especially useful for Russian and Turkish market analysis
    - Unlike GSC, Yandex does not hide search phrases behind "(not provided)"

    Args:
        project_id: Project ID from list_projects
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        limit: Max results (default 20, max 100)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/yandex-metrica/search-phrases", {
        "start_date": start_date, "end_date": end_date, "limit": str(limit),
    })


# ─── Bing Webmaster ──────────────────────────────────────


@mcp.tool()
def bing_get_query_stats(project_id: str) -> str:
    """Get Bing search query statistics — top queries with clicks, impressions, CTR, and position.

    When to use: User asks about Bing keywords, Bing search queries, Bing search performance.
    Do NOT use for: Google search keywords (use get_keywords), Yandex keywords (use ym_get_search_phrases).

    Returns: {_meta: {total, returned, truncated}, items: [{Query, Date, Impressions, Clicks, Ctr, AvgClickPosition, AvgImpressionPosition}]}

    Tips:
    - Compare with Google Search Console get_keywords to see search engine differences
    - Bing has ~6% global market share but higher in some demographics (enterprise, US users)
    - CTR is calculated from Clicks/Impressions (not returned by Bing API directly)

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/query-stats")


@mcp.tool()
def bing_get_page_stats(project_id: str) -> str:
    """Get Bing page-level performance — pages with clicks, impressions, CTR, and position.

    When to use: User asks about Bing page performance, which pages rank on Bing.

    Returns: {_meta: {total, returned, truncated}, items: [{Query (page URL), Impressions, Clicks, Ctr, AvgClickPosition, AvgImpressionPosition, Date}]}

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/page-stats")


@mcp.tool()
def bing_get_crawl_stats(project_id: str) -> str:
    """Get Bing crawl statistics over time — crawled pages, errors, indexed count, inbound links.

    When to use: User asks about Bing crawl health, how Bing crawls the site, Bing indexing status.

    Returns: {_meta: {total, returned}, items: [{Date, CrawledPages, CrawlErrors, InIndex, InLinks}]}

    Tips:
    - Compare InIndex trend to see if Bing is indexing more or fewer pages over time
    - CrawlErrors trending up = technical issues that need fixing
    - Combine with indexing_get_status (Google) for complete crawl health picture

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/crawl-stats")


@mcp.tool()
def bing_get_crawl_issues(project_id: str) -> str:
    """Get Bing crawl issues — URLs with errors, HTTP codes, and issue types.

    When to use: User asks about Bing crawl errors, broken pages on Bing, Bing indexing issues.

    Returns: {_meta: {total, returned, truncated}, items: [{Url, HttpCode, IssueType, DateDetected}]}

    Tips:
    - Fix 4xx/5xx errors to improve Bing indexing
    - Compare with Google indexing_get_status for complete crawl health picture across search engines

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/crawl-issues")


@mcp.tool()
def bing_get_rank_traffic(project_id: str) -> str:
    """Get Bing rank and traffic statistics over time — daily impressions and clicks.

    When to use: User asks about Bing traffic trends, Bing visibility over time.

    Returns: {_meta: {total, returned}, items: [{Date, Impressions, Clicks}]}

    Tips:
    - Compare with get_performance (Google Search Console) for cross-engine traffic trends

    Args:
        project_id: Project ID from list_projects
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/rank-traffic")


@mcp.tool()
def bing_get_link_counts(project_id: str, page: int = 0) -> str:
    """Get Bing inbound link counts per URL — see which pages have the most backlinks according to Bing.

    When to use: User asks about Bing backlinks, link profile from Bing, which pages have links.

    Returns: {_meta: {total, returned, page}, items: [{Url, LinkCount}]}

    Tips:
    - Bing's link data can differ from Google's — useful for cross-validation
    - Use bing_get_url_links to see the actual linking pages for a specific URL

    Args:
        project_id: Project ID from list_projects
        page: Pagination page number (default 0)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/link-counts", {
        "page": str(page),
    })


@mcp.tool()
def bing_get_keyword_stats(project_id: str, keyword: str) -> str:
    """Get Bing keyword volume data — broad and exact match impressions for a specific keyword.

    When to use: User asks about Bing keyword volume, keyword research on Bing, how popular a keyword is on Bing.

    Returns: {_meta: {total, returned, keyword}, items: [{Keyword, Date, BroadImpressions, ExactImpressions}]}

    Tips:
    - BroadImpressions: impressions for broad match (includes variations)
    - ExactImpressions: impressions for exact match only
    - Useful for keyword research and comparing Bing vs Google keyword volume

    Args:
        project_id: Project ID from list_projects
        keyword: The keyword to research (required)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/keyword-stats", {
        "keyword": keyword,
    })


@mcp.tool()
def bing_get_url_traffic(project_id: str, url: str) -> str:
    """Get Bing traffic data for a specific URL — impressions and clicks over time.

    When to use: User asks about a specific page's performance on Bing.

    Returns: {_meta: {total, returned, url}, items: [{Url, Impressions, Clicks, Date}]}

    Args:
        project_id: Project ID from list_projects
        url: The full page URL to check (required)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/url-traffic", {
        "url": url,
    })


@mcp.tool()
def bing_get_url_links(project_id: str, url: str, page: int = 0) -> str:
    """Get Bing inbound links for a specific URL — see which external pages link to a given URL.

    When to use: User asks about backlinks to a specific page on Bing, who links to this URL.

    Returns: {_meta: {total, returned, url, page}, items: [{Title, Url, AnchorText}]}

    Tips:
    - Shows the linking page title, URL, and anchor text used
    - Useful for backlink analysis and identifying link building opportunities

    Args:
        project_id: Project ID from list_projects
        url: The page URL to check backlinks for (required)
        page: Pagination page number (default 0)
    """
    return api_get(f"/projects/{_safe_project_id(project_id)}/bing-webmaster/url-links", {
        "url": url, "page": str(page),
    })


# ─── Main ─────────────────────────────────────────────────


if __name__ == "__main__":
    if not API_KEY:
        raise ValueError(
            "SEMUST_API_KEY environment variable is required. "
            "Set it in your Claude Desktop config or run:\n"
            '  $env:SEMUST_API_KEY="your-key"\n'
            '  $env:SEMUST_BASE_URL="http://localhost:3001/v1/mcp"\n'
            "  python semust_mcp.py"
        )
    mcp.run()
