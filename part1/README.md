# Part 1: What the company says about itself

## What this part does

It collects one archived snapshot per firm per year, 2016 through 2024, of the page where the company describes itself to the public. The Internet Archive's CDX API is the index. The snapshot closest to July 1 is preferred, so firms are compared at a similar point in the year rather than on whatever day the crawler happened to visit. The replay URL uses the `id_` form, which returns the page without the Wayback toolbar.

Visible text is kept. Navigation, footers, cookie banners, and a short list of interface lines are removed. Headings and list items are kept, because a values page is often a list of principles rather than a paragraph. Pages shorter than 120 characters after cleaning are treated as empty shells and the next candidate in that year is tried.

## How the page is chosen

Each firm has an ordered list of historical About, mission, or values URLs in `src/companies.py`. A capture is eligible when its normalized URL matches one of those seeds. Careers, news, investor, privacy, and diversity-only paths are not accepted as substitutes. A sustainability report is not accepted either: that document belongs to Part 2, and using it here would make the two sides of the comparison the same text.

Redirects are followed one hop, and only when the target stays on the firm's own domain and still looks like an About page. A redirect to a careers site or a homepage is rejected.

Berkshire Hathaway is the one firm allowed to use its corporate homepage. It does not publish a separate values URL. The homepage is the public statement.

Missing years are stored as gaps. Text is never copied from the previous or the next year. A gap row is kept in `data/company_year.csv` so the panel stays rectangular: 50 firms times 9 years.

## How the text is coded

The categories are an analyst's rubric that has been frozen in code (`src/taxonomy.py`, version `codebook-1.0`). The same ten categories are used on the proxy, which is what makes an alignment score possible. They separate inclusion from generic employee language, and environment from community, because those are the shifts a 2016-2024 panel can actually see. Vague words such as "excellence" and "world-class" are counted as boilerplate, not as a value. Bare "equity", bare "trust", bare "environment", and bare "safe" are excluded because they collide with accounting, bank products, "work environment", and "safe harbor".

A theme is present if the rubric hits at least once. `theme_categories` lists the hits. Shares say which themes dominate the page.

`changed_from_prior` compares the page with the immediately previous calendar year, using cosine similarity of content words. Pronouns are left out of that comparison and measured on their own. Similarity below 0.85 is a material change. If the previous year is missing, the flag is left blank rather than compared with an older year. The threshold was set before looking at the results. The raw similarity is stored, so the cutoff can be recomputed without scraping again.

`analyst_notes` states the themes, whether the wording moved, which themes entered or left, and any linguistic move that is both relatively large (35%) and absolutely large. A new sentence that carries the most rubric hits is quoted when one exists.

## Assumptions

The assignment list is the January 2024 sector leaders. Market caps are not re-ranked.

Alphabet is represented by Google's public values and About pages. Alphabet's holding-company page is a sparse fallback, not the preferred text.

A July snapshot is "the company's stated values that year" even if the page was rewritten in November.

Apple's `/about/` page in the years it exists is kept even when it is a corporate address card. That is the page Apple published. It is not replaced with the leadership directory or the diversity page, both of which would invent a values statement the About URL did not contain.

## What more time would change

Hand-check a sample of pages against the archived original and publish the share that still contain navigation. Add a second pass that follows a firm's own "values" link inside a thin About page, still staying on the company domain. Ask the Wayback project for a higher request budget; the public CDX and replay servers return 429 quickly, and the collector is built to cache every success and resume. The firm list is the only thing that has to grow to cover the other 450 S&P firms.

## Coverage

The collector finished with text for 265 of 450 firm-years (59%). Financials are the most complete (74%), then healthcare (67%), consumer discretionary (60%), technology (58%), and energy (36%). Of the 185 gaps, 115 have no eligible capture in the archive, 64 are captures whose visible text was an empty shell, and 6 failed because the Internet Archive returned HTTP 429: Broadcom 2018 to 2021, Meta 2022, and NVIDIA 2019. Those six are recorded as download failures and can be retried; they are not filled from another year.

Among the 210 pairs with text in both the current year and the previous calendar year, 75 (36%) fall below the 0.85 similarity cutoff. The median similarity is still 0.95, so the typical page is stable and the rewrites are a minority. Median length is 355 words.

## Limitations

Archived pages are sometimes a JavaScript shell. Those years are gaps, not imputed text. Some navigation still leaks through as a short line; the cleaner drops a known list of those lines, and anything not on the list can still create a stray theme hit. The rubric is transparent and replicable. It will miss a value that is expressed only by a metaphor, and it will count a value that is named once in passing.

## How to rerun

From the repository root: `python3 part1/code/collect_about.py` then `python3 part1/code/analyze_about.py`. A ticker argument limits collection. Successful years are not downloaded again. The client waits between requests and backs off on HTTP 429. Do not run a second collector against the same API at the same time.
