# Part 2: Lived values in the annual proxy

## What this part does

It collects one proxy statement per firm per year for the same 50 companies, from 2016 through 2024, and measures how the language and the concrete practices in that document move over time.

The document is the definitive proxy, form DEF 14A, taken from the SEC EDGAR submissions API and the EDGAR archives. One filing is kept per calendar year, chosen by filing date. If a year has more than one DEF 14A, the HTML filing closest to April 30 is kept, and a same-day "notice of meeting" is passed over when a full proxy was filed beside it. A preliminary proxy (PRE 14A) is used only when that year has no DEF 14A. Additional proxy materials (DEFA14A) are never used. Those are often contest letters, not the board's own statement.

Full cleaned text is stored at `data/text/{ticker}_{year}.txt`. The analysis table is `data/proxy_company_year.csv`. Gaps are listed in `data/coverage_gaps.csv` and are also empty rows in the main table, so a missing year cannot be mistaken for a quiet year.

## Why a proxy

A sustainability report is voluntary. The firms that publish one are already the firms willing to talk. A proxy is filed by every US public company, and it is where the board tells shareholders what it oversees and what pay depends on. That is the closest public document to a revealed priority. The same ten value categories used on the About pages are counted here, so Part 3 can compare like with like. Counts are turned into mentions per 1,000 words so a long proxy is not scored as more virtuous.

Words in a legal document are cheap. The second layer is a set of practices: a representation statistic, a pay-equity statement, a diversity or climate or safety metric inside the pay design, an emissions target, a safety rate, a human-capital number, a customer metric in pay, political-spending disclosure, a dollar community investment, and a board committee with an environmental or social mandate. A practice is what Part 3 treats as follow-through. Shareholder mentions and generic compliance language are not treated as practices, because a proxy is required to contain them.

Change across years is measured in two ways. Content-word similarity uses the same 0.85 cutoff as the About pages, so the projects stay comparable. Theme-mix shift is the distance between the two years' theme compositions. The similarity cutoff was not lowered after seeing the results.

## Coverage

447 of 450 firm-years have text (99.3%). Median length is about 50,000 words.

Three years are genuine filing gaps, not failed downloads:

- **Apple, 2018.** The proxies on either side were filed on 27 December 2017 and 8 January 2019. No DEF 14A has a 2018 filing date.
- **ExxonMobil, 2021.** The Engine No. 1 contest produced a large stack of DEFA14A letters. The submissions index has no DEF 14A and no PRE 14A in calendar 2021. Those letters were not substituted for the board's proxy.
- **Starbucks, 2024.** The next definitive proxy was filed on 24 January 2025. Calendar 2024 contains contest materials only.

One recovery, documented rather than hidden: **McDonald's 2022** has a PRE 14A and no DEF 14A. The preliminary proxy (61,544 words, filed 28 March 2022) is used, and `document_type` is `PRE 14A`. NVIDIA's 2022 primary document was a two-page notice; the full proxy filed the same day (60,041 words) is the one kept.

Broadcom's pre-2018 proxies are taken from the Broadcom Limited CIK. The primary CIK wins when both filers have a document.

## Assumptions

The filing year is the panel year. A proxy filed in October describes a fiscal year that ended in June. Pairing it with a mid-year About page is a choice, revisited in Part 3.

A single regex hit counts as the practice being present. The flag is binary on purpose. Repeating "pay equity" twenty times does not make the practice twenty times more real.

"Greenhouse gas" and "carbon neutral" count as a climate practice. A firm that mentions an existing neutrality claim is coded as having one. The flag does not check whether the target was met.

Berkshire's proxy is short (about 10,000 to 17,000 words). Per-1,000 densities there move more for the same sentence than they do in a 70,000-word bank proxy.

## What more time would change

Split the proxy into the compensation discussion, the governance section, and the risk factors, and score practices only in the first two. Risk-factor mentions of emissions currently count. Hand-check a sample of flags against the page they came from, and publish the error rate. For the three gap years, build a separate series from the contest letters instead of leaving the year blank. Extend the same collector to the rest of the S&P 500: the firm list, the CIK, and the alternate CIK are the only firm-specific inputs.

## Limitations

The practice flags saturate. By 2023, 96% of these proxies trip the DEI flag and 96% trip the climate flag. The flag still separates firms in 2016, and it still separates the holdouts (Broadcom trips it in one year out of nine; Halliburton, EOG, and Thermo Fisher in about a third). It no longer separates the majority in the later years. Later-year differences have to be read from the densities, not the flags.

Similarity is dominated by the legal template. Median similarity to the prior proxy is 0.97. Only 20 of 395 comparable pairs fall below 0.85, so the change flag is usually false even when emphasis moves. Theme-mix shift and the per-1,000 densities are the measures to use.

The tone lists are a short original lexicon for within-firm comparison. They are not a general financial-sentiment model. Net tone barely moves, which is itself informative: the story is not "the writing got happier."

## Columns

Identifiers and provenance: `ticker`, `company_name`, `sector`, `year`, `document_type`, `source`, `cik_used`, `accession`, `filing_date`, `source_url`, `text_path`, `text_sha1`, `gap_reason`, `word_count`, `event_context`, `rubric_version`.

`event_context` is the same calendar note for every firm in a year. It is a join key for the write-up, not a claim that the event hit that firm.

Themes: for each of the ten categories, `theme_count_*`, `theme_per_1k_*`, and `theme_share_*`. `theme_categories` lists categories whose share of theme hits is at least 8%. Shares are a composition, so they say what the document emphasizes relative to its other value language. Per-1,000 figures are comparable across documents of different lengths. Both are kept because they answer different questions.

Practices: each `flag_*` is 1 if the pattern hit at least once, and `flag_*_count` is the number of hits. `operational_dei` is 1 if any of the representation, pay-equity, or diversity-in-pay flags hit. `operational_climate` is 1 if an emissions target or a climate-linked pay metric hit.

Language: `commitment_per_1k`, `positive_per_1k`, `negative_per_1k`, `uncertainty_per_1k`, `we_our_per_1k`, `numeric_token_share`, `tone_net` (positive minus negative, divided by their sum). `similarity_to_prior`, `changed_from_prior`, `theme_mix_shift`. `analyst_notes` states the filing date, the dominant themes, which practices fired, and any large within-firm move. `changed_from_prior` is blank when the prior year is missing. Text is not copied forward.

## How to rerun

From the repository root: `python3 part2/code/collect_proxies.py` then `python3 part2/code/analyze_proxies.py`. A ticker argument limits the run. Successful years are skipped. EDGAR requires the contact email in the user agent set in `src/constants.py`.
