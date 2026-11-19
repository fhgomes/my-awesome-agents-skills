# Reading Search Console and GA4 output

The scripts print raw rows. This is how to turn them into a recommendation.

## Search Console (`gsc.py top`, `status`, `inspect`)

| Signal | Means | Do |
|---|---|---|
| Impressions high, CTR < 2% | Google shows the page, people skip it | Rewrite title (front-load the promise, under 60 chars) and meta description (under 155, ends with a reason to click) |
| Position 8-20 for a query with volume | Page two, one push from page one | Add the query's phrasing to H1/H2, add an internal link from a stronger page, expand the section that answers it |
| Position 1-3, few impressions | Ranking for a query nobody searches | Fine as a long tail; do not spend time here |
| Same query ranks two of your URLs | Cannibalization | Merge or canonicalize to the stronger one |
| Sitemap `errors > 0` | Malformed or unreachable URLs | `curl -I` the listed URL; usually a deleted post or a redirect loop |
| Sitemap `submitted` >> `indexed` | Google saw the URLs but chose not to index | `inspect` a few; see verdicts below |

### `inspect` verdicts (`coverageState`)

- **Submitted and indexed**: nothing to do.
- **Crawled, currently not indexed**: content judged thin or duplicate. Improve or `noindex` it.
- **Discovered, currently not indexed**: crawl budget or low priority. Internal links help.
- **Excluded by noindex tag**: check that this is intentional (internal tools, thank-you pages).
- **Page with redirect** / **Not found (404)**: expected after slug changes; make sure a 301 exists.

Data lags about two days and is sampled for small sites. Compare 28-day windows, not days.

## GA4 (`ga4.py report`, `landing`, `realtime`)

| Signal | Means | Do |
|---|---|---|
| `sessionSource / medium` = `google / organic` growing | SEO work is paying | Keep publishing on the queries from Search Console |
| `(direct) / (none)` dominant | Untagged links (QR codes, chat, email, apps) | Add `utm_source`/`utm_medium`/`utm_content` to every link you control |
| `linkedin.com / referral` spikes then dies | Social traffic, not search | Normal; judge posts on 7-day windows |
| Landing page with sessions but engagement rate < 40% | People arrive and bounce | Check the above-the-fold promise matches the query that brought them |
| Country mix differs from the content language | Audience mismatch | Either translate or stop optimizing for that geography |

`realtime` is for checking that the tag fires after a deploy: open the site in a browser,
run `realtime`, expect one active user on that page within ~30 seconds.

## Weekly report template

```
SEO week of <date>  <site>
Decision: <one sentence: what to change or keep doing>

Search (28d): <clicks> clicks / <impr> impressions / avg pos <n>   (vs previous 28d: +/-)
Top queries:            Top pages:
  <q1>  pos <n> ctr <n>%   <page1>  <clicks>
  ...                        ...
Index: <indexed>/<submitted> in sitemap, <n> URLs not indexed (list if <= 5)

Traffic (GA4 28d): <users> users, top source <source>, top landing <page> (engaged <n>%)
Next: <1-3 concrete actions with the URL they apply to>
```

Keep it under 25 lines. Numbers without a decision are noise.
