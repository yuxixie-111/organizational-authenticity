# Part 3: Organizational Authenticity Index

## What this part does

It scores each firm-year on how closely the public values page and that year's proxy emphasize the same things, and on whether the values the firm actually stresses are backed by a concrete practice in the proxy.

The panel is `data/authenticity_panel.csv`. A score is missing when either document is missing, or when the About page contains none of the ten categories. Missing is not zero. A firm that does not publish a values statement has not been measured as inauthentic. It has declined to make the statement the index compares.

## What "alignment" means here

Two different complaints get called inauthenticity, and they are kept separate.

**Rhetorical alignment** is whether the mix of themes is the same. Both sides are turned into compositions that sum to one. On the About page the composition is the share of rubric hits. On the proxy it is the share of per-1,000-word densities, plus a fixed bonus of 2.0 on any theme that has a concrete practice. Cosine similarity of those two compositions is the rhetorical score. It runs from 0 to 1. Shareholder language is required in a proxy, so a second cosine is stored with that theme removed and both vectors renormalized (`cosine_ex_shareholder`). The main score keeps it. The second number is there so a reader can see how much of the gap is just the genre of the document.

**Follow-through** asks a narrower question. Of the themes the About page actually emphasizes (at least 12% of its rubric hits), and that a proxy can operationalize, what fraction have a practice? Silence is not punished. A firm that never mentions inclusion is not scored down for having no diversity statistic. A firm that leads with inclusion and has no representation figure, no pay-equity statement, and no diversity metric in pay is scored down. Innovation, shareholder, and collaboration have no practice indicator that is both discretionary and reliable in a DEF 14A, so they do not enter this test.

The index is

100 × (0.5 × rhetorical alignment + 0.5 × follow-through).

When the About page emphasizes no operationalizable theme, follow-through is undefined and the index equals the rhetorical score alone. The weights were set as an equal split between "same topics" and "a practice behind the topics you feature." They are not fitted to produce a ranking.

Two sensitivities are stored. `oai_bonus0` ignores practices and uses the proxy's word mix only. `oai_bonus5` lets a practice dominate the lived mix. The reported index uses the bonus of 2.0.

## Why this and not a count of shared words

A proxy is a legal document. It will always mention shareholders, risk, and employees. Counting raw overlaps would call every firm authentic. Compositions ask what each document emphasizes relative to its other value language. The practice layer asks whether a featured value shows up as a number, a target, or a pay link, which is the difference between a sentence and a priority.

The same rubric codes both documents. A category invented for one side and not the other cannot be an alignment.

## Validity checks, decided before the scores

The distribution is in `output/distribution.json`: mean, spread, quartiles, and the mean by sector and by year.

The index is correlated with the length of each document. A large correlation would mean the score is a verbosity artifact.

Six firms were named before any score was computed, as cases to interpret rather than as a sample picked because the scores looked convenient: Wells Fargo, Salesforce, Berkshire Hathaway, ExxonMobil, Nike, and Meta. Their component scores are in `output/face_validity_cases.csv`. The eight lowest and eight highest firm averages are in `output/oai_extremes.csv`.

## What this run produced

250 of 450 firm-years get a score. Mean 37, median 36, standard deviation 22 (about 1.5 to 94). The mean goes from 23 in 2016 to 47 in 2021, then 36 in 2023 and 41 in 2024. Scored energy years average 54 and consumer years 29. Energy has the fewest pages, so that average is mostly the later years the archive kept. Correlation with About-page length is -0.09 and with proxy length is 0.04. Dropping shareholder language raises mean cosine from 0.41 to 0.47. The bonus-0 and bonus-5 versions correlate with the reported index at 0.98 and 0.99. The reading is in `SUMMARY.md`.

## Assumptions

The About page and the proxy from the same calendar year are treated as contemporaneous. Many proxies are filed in the spring and describe the year just finished. A July About page can post-date that proxy by a few months. The alternative, lagging the proxy by a year, is a robustness check left for later. It is not the reported index.

A practice bonus of 2.0 is roughly a moderate verbal emphasis. It is a judgment.

## What more time would change

Lag the proxy by one year and report whether the ranking moves. Parse the compensation discussion separately so a risk-factor mention cannot count as a practice. Have a second coder apply the rubric to a sample of pages and publish agreement. Vary the 12% emphasis cutoff.

## Limitations

The practice flags saturate after 2021. Follow-through then stops separating firms that all disclose a DEI or climate metric, and the index leans on the rhetorical cosine. That is a property of the documents in this window, and it is reported rather than adjusted away.

A scandal can look like integrity. A firm that talks about misconduct and remediation uses integrity words on both sides and can score as aligned. The index measures alignment of emphasis, not whether the emphasis is admirable. Wells Fargo is the case to read that way.

Absence of a values page is undefined, not a low score. Readers who want "says nothing" to count as a kind of authenticity, or as a kind of failure, are asking a question this index does not answer. The gap column answers it.
