# skill_demand_forecast

Forecasts next-period demand count per skill via a simple linear trend — backs the demand-trend chart on /skills/[slug].

**Current version:** 1.0.0
**Features:** skill_demand.demand_count (weekly time series)
**Training window:** 19 skills with >= 3 weekly periods
**Metric:** mae = 7.1884

**Baseline(s):**
- naive_last_period_mae: 8.4211

**Limitations:** Only 19 of 45 skills with any demand data have >= 3 weekly periods to backtest against — most of the taxonomy has too short a real history yet for this model to say anything about. Weekly buckets span a few months of real Adzuna posting dates (not months of live production traffic), so this evaluates a real but early-stage trend, not a mature forecast.

**Last retrained:** 2026-08-24T15:59:46.418414+00:00 (commit unknown)
