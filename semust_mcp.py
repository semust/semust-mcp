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

__version__ = "1.0.0"

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
    instructions="""You are connected to Semust, a Turkish SEO analytics platform. You can access the user's Google Search Console data through these tools.

WORKFLOW:
1. ALWAYS call list_projects first to get available projects and their project_id values.
2. Only use Search Console tools on projects where integrations.search_console = "completed".
3. Use the project_id from list_projects in all subsequent tool calls.

DATE RULES (CRITICAL):
- Format: YYYY-MM-DD (e.g. 2026-05-01)
- Google Search Console data has a 2-day delay. ALWAYS use (today - 2 days) as the most recent end_date. Never use today or yesterday.
- When user says "last 30 days": end_date = today - 2 days, start_date = end_date - 30 days
- When user says "this month" (e.g. June 2026): start_date = 2026-06-01, end_date = today - 2 days
- When user says "last month" (e.g. May 2026): start_date = 2026-05-01, end_date = 2026-05-31
- For content_decay reports, use 6-12 month range (e.g. start = today - 365 days)
- For winner_loser reports, use 60+ day range for meaningful comparison
- If user doesn't specify dates, default to last 30 days (end = today - 2, start = end - 30)

TOOL SELECTION GUIDE:
- User asks about "keywords", "queries", "what people search" → get_keywords
- User asks about "pages", "URLs", "which pages perform" → get_pages
- User asks about "traffic trends", "how is my site doing", "overview" → get_performance
- User asks about "cannibalization", "competing pages" → report_cannibalization
- User asks about "monthly report", "summary", "how was this month" → report_monthly_summary
- User asks about "long-tail", "multi-word queries" → report_long_tail
- User asks about "winners", "losers", "gained traffic", "lost traffic" → report_winner_loser
- User asks about "questions", "FAQ", "people also ask" → report_questions
- User asks about "declining", "losing traffic", "content decay" → report_content_decay
- User asks about "quick wins", "almost ranking", "page 2", "striking distance" → report_striking_distance
- User asks about "low CTR", "click-through rate", "title optimization" → report_low_ctr
- User asks about "thin content", "underperforming", "content audit", "remove pages" → report_thin_content

MULTI-TOOL CHAINING — combine tools for complex requests:
- "Full SEO audit" → call: get_performance + get_keywords + get_pages + report_striking_distance + report_low_ctr + report_thin_content
- "Content strategy" → call: report_questions + report_long_tail + report_content_decay
- "Monthly client report" → call: report_monthly_summary + get_performance + get_keywords(limit=20)
- "Quick wins" → call: report_striking_distance + report_low_ctr

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

OUTPUT FORMATTING:
- Present data in tables when showing lists of keywords/pages
- Bold the most important metrics and findings
- Always provide actionable SEO recommendations, not just raw data
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

ERROR HANDLING — give clear actionable guidance:
- "search_console_not_connected" → Tell user: "Search Console is not connected for this project. Go to Semust > Project Settings > Integrations to connect your Google Search Console."
- "user_not_active" → Tell user: "Your Semust subscription is not active. Visit semust.com/fiyatlar (Turkish) or semust.com/en/pricing (English) to get a paid plan."
- "project_access_denied" → Tell user: "You don't have access to this project. Use list_projects to see your available projects."
- "rate_limit_exceeded" → Tell user: "Too many requests. Wait a minute and try again."
- If a project's integration is "not_connected" or "pending", warn the user BEFORE calling tools: "This project doesn't have Search Console connected. Connect it in Semust first."
- If NO projects have Search Console connected, explain: "None of your projects have Search Console connected. Go to Semust, open a project, and connect Google Search Console to start."

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

    Returns: {projects: [{project_id, project_name, url, role, integrations: {search_console, google_analytics, google_ads, meta_ads}}]}
    - integration status is "completed", "pending", or "not_connected"
    - Only projects with search_console = "completed" can use the Search Console tools"""
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
