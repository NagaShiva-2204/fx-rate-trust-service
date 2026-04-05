# Decisions and Reasoning

## APIs chosen and why
- **open.er-api.com**: Reliable free tier, includes UNIX timestamp for last update which helps with freshness labeling.
- **exchangerate.host**: Simple JSON API with broad currency coverage and a clear base parameter.
- **frankfurter.app**: Clean response shape and historically stable uptime.

I picked three sources to reduce single-point failures and enable simple aggregation without blowing up complexity.

## Fallback strategy when an API fails
- Call all three sources sequentially with short timeouts.
- If one or two fail, use what succeeded and note warnings in the response.
- If all fail, return the last successful response from an in-memory cache (2-minute TTL) and show a warning.

## Conflicting data handling
- For each currency, collect all available values and take the **median**. This reduces outlier impact while staying fast and explainable.

## What the user sees on failure or staleness
- **Freshness badge**: `fresh` (<=10 min), `acceptable` (<=60 min), or `stale`.
- **Warnings** if a source failed or if cached data is served.
- UI still renders with placeholders and a friendly error message if everything fails.

## Staleness improvements
- In-memory cache for 2 minutes reduces API spam and gives consistent snapshots.
- Freshness derived from provider timestamps where available; otherwise falls back to fetch time.

## Cuts to ship in 60 minutes
- No per-user premium API spend logic (budgeted $5/day). This would require auth and usage tracking.
- No historical charting.
- No persistent cache layer (Redis).
- No server-side currency list endpoint.

## What I'd add with more time
- Premium API routing for high-intent users (pricing page, repeated refreshes).
- Persistent cache + background refresh job.
- A/B test for trust messaging vs. premium upsell.
- Structured metrics (success rate, staleness distribution, conversion funnel tracking).

## Other thoughts
- The trust moment for free users is the first 10 seconds. The UI shows freshness and source transparency to help them build confidence quickly.
