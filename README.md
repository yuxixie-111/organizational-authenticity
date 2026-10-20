# Organizational Authenticity

Stated values on company About pages, compared with language and practices in annual proxy statements, for 50 large US firms from 2016 through 2024.

The firm list is fixed: the ten largest companies by market cap in Technology, Financials, Healthcare, Consumer Discretionary, and Energy, using the January 2024 composition supplied with the assignment. Market caps are not re-ranked. Missing firm-years are kept as documented gaps. Text is never copied from a neighboring year.

## Layout

- `src/` holds the shared firm list, theme codebook, text cleaning, and the authenticity score.
- `part1/` collects one Wayback Machine About-page snapshot per firm-year and codes themes.
- `part2/` collects the annual DEF 14A (PRE 14A only when no DEF 14A exists) and codes the same themes plus observable practices.
- `part3/` builds the Organizational Authenticity Index from the two panels.
- `part4/` compares stated inclusion with operational DEI around 2020 to 2021 and 2023 to 2024.
- `tests/test_core.py` checks the exclusions in the codebook and the score arithmetic.

## Run

```bash
pip install -r requirements.txt
python3 -m unittest tests.test_core -v
python3 part2/code/analyze_proxies.py
python3 part1/code/analyze_about.py
python3 part3/code/build_index.py
python3 part4/code/dei_discontinuity.py
```

`part1/code/collect_about.py` and `part2/code/collect_proxies.py` download the source documents. The About-page collector waits 20 seconds between Internet Archive requests. Re-running it skips firm-years that already have text.

Raw download caches under `data/cache/` are local only and are not in this repository.

## Status

Part 1 has readable text for 265 of 450 About pages. Gaps are in `part1/data/coverage_gaps.csv`. Part 2 has 447 of 450 proxies. The blanks are Apple 2018, Exxon Mobil 2021, and Starbucks 2024. Part 3 scores 250 firm-years. Part 4's three checks are in `part4/output/hypothesis_summary.json`. Each part has a method note (`README.md`) and a short reading (`SUMMARY.md`).
