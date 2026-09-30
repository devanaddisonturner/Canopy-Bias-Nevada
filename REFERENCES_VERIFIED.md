# Reference verification record

*Devan Cantrell Addison-Turner, ORCID [0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil and Environmental Engineering, Stanford University. From the reproduction package for "An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals", prepared for GIScience & Remote Sensing. Repository: https://github.com/devanaddisonturner/Canopy-Bias-Nevada Code MIT, released data CC0 1.0.*

Every reference in the manuscript checked against an authoritative record.
Checked 27 September 2026, extended 28 September. Result: **27 of 27 verified,
no remaining errors.**

Two entries were found wrong during this audit and corrected in the
manuscript; both are recorded at the end.

## Journal and dataset DOIs (21 of 21 verified)

| # | Reference | Checked against | Result |
|---|---|---|---|
| 1 | Ahn et al. 2024 | Crossref | Scientific Data 11 (1): 275. Exact |
| 2 | Brown et al. 2022 | Crossref | Scientific Data 9 (1): 251. Exact |
| 3 | Conley 1999 | Crossref | J. Econometrics 92 (1): 1–45. Exact |
| 4 | Culler et al. 2024 | Crossref | RSASE 35: 101247. Exact |
| 5 | Dewitz 2021 | DataCite | USGS data release, pub. year 2021, ver. 3.0 Feb 2024. Exact |
| 6 | Leyk and Uhl 2018 | Crossref | Scientific Data 5: 180175. Exact |
| 7 | Locke et al. 2021 | nature.com | npj Urban Sustainability 1: 15, 25 Mar 2021. Exact |
| 8 | Nolte et al. 2024 | Crossref | Land Economics 100 (1): 200–221. Exact |
| 9 | Nowak and Greenfield 2010 | Crossref | Environmental Management 46 (3): 378–390. Exact |
| 10 | Pesaresi et al. 2024 | Crossref | Int. J. Digital Earth 17 (1): 2390454. Exact |
| 11 | Pilant et al. 2020 | Crossref | Remote Sensing 12 (12): 1909. Exact; four authors, Pilant, Endres, Rosenbaum, Gundersen |
| 12 | Schwarz et al. 2015 | Crossref | PLOS ONE 10 (4): e0122051. Exact |
| 13 | Tolan et al. 2024 | Crossref | Remote Sens. Environ. 300: 113888, print Jan 2024. Exact |
| 14 | Uhl et al. 2020 | Crossref | Int. J. Digital Earth 13 (1): 22–44. Exact |
| 15 | Uhl et al. 2021 | Copernicus | Earth Syst. Sci. Data 13: 119–153. Exact |
| 16 | Wickham et al. 2020 | Crossref | Int. J. Appl. Earth Obs. Geoinf. 84: 101955. Exact |
| 17 | Wickham et al. 2021 | Crossref | Remote Sens. Environ. 257: 112357. Exact |
| 18 | Wickham et al. 2023 | Crossref | GIScience & Remote Sensing 60 (1): 2181143. Exact |
| 19 | Wickham et al. 2026 | Crossref | GIScience & Remote Sensing 63 (1): 2659490. Exact |
| 20 | Yang et al. 2018 | Crossref | ISPRS J. Photogramm. 146: 108–123. Exact |
| 21 | Zanaga et al. 2022 | DataCite | Zenodo, ESA WorldCover 10 m 2021 v200, 2022. Exact |

Titles, journals, volumes, issues, page or article numbers, years and the
named author order were each compared. No discrepancy was found in any of the
twenty-one.

## Documents without a DOI (6 of 6 verified)

| Reference | Checked against | Result |
|---|---|---|
| Connecticut DEP 2006 | portal.ct.gov | URL resolves; the unusual filename is genuine |
| MRLC 2021 | mrlc.gov product metadata | **URL corrected** (see below); nighttime-lights passage confirmed near verbatim |
| OEHHA 2010 | oehha.ca.gov | **Entry corrected** (see below); coefficient equation confirmed |
| US Census Bureau 2025 | census.gov QuickFacts | Resolves; independently confirms the 101,911 population figure cited |
| US EPA 2015 | epa.gov | Resolves; title "Innovative TMDLs using Impervious Cover" exact |
| USDA SCS 1986 | multiple hosted copies | Running header "(210-VI-TR-55, Second Ed., June 1986)" confirms edition and year |

## Two entries found wrong and corrected

**OEHHA.** The entry read "CalEnviroScreen 4.0 Indicator: Impervious Surface
Cover. 2021" with a URL that returns 404. Impervious surface is not a
CalEnviroScreen indicator. The real source is *User's Guide for the California
Impervious Surface Coefficients*, OEHHA Ecotoxicology Program, December 2010.
Its equation, ISC = 0.2449 + 0.352 log10(dwelling units per acre), is exactly
what `analyze_canopy_bias.py` implements, so the result was unaffected and only
the citation was wrong. Corrected in title, year and URL.

**MRLC.** The URL returned 404. Repointed to the live product metadata,
`nlcd_2019_impervious_l48_20210604.xml`, whose text confirms the claim the
citation carries in Section 3.5: "DMSP Nighttime Lights (for 2011) and VIIRS
Day/Night band Nighttime Lights (for 2016) were superimposed on NLCD 2011
Impervious Surface data to exclude low density impervious areas outside urban
and suburban centers."

## Two metadata traps avoided

- Semantic Scholar reports **Locke et al. as 2020**. The publisher gives
  25 March 2021. The manuscript's 2021 is correct.
- Semantic Scholar reports **Tolan et al. as 2023**, and the DOI string itself
  contains 2023. Crossref gives published-print January 2024 in volume 300.
  The manuscript's 2024 is correct.

A third lookup returned an unrelated article when the Schwarz DOI was fetched
through the PLOS site; it was treated as a failed fetch, not as evidence, and
the reference was then confirmed through Crossref.

## Substantive claims: as they stood earlier on 28 September

> **Status note, added 2026-09-28.** This section is superseded and is kept for
> provenance, because the three failed access routes it records are worth
> keeping. Both substantive claims are now verified: see **Quoted figures read
> out of the source papers** immediately below, where all three Nowak and
> Greenfield figures are read out of the publisher's full text. The heading and
> the "NOT VERIFIED" label below describe the state before that read, not the
> state now. Nothing in the manuscript rests on an unchecked source.

This record covers **bibliographic metadata** above: that each cited work exists
and is described correctly. The manuscript also attributes specific figures to
two of these works, which metadata checking cannot reach. Status as of
28 September 2026:

**Wickham et al. 2020 — VERIFIED.** The publisher's record for
doi:10.1016/j.jag.2019.101955 confirms all four elements the Introduction
quotes: "18 metropolitan areas throughout the conterminous United States", and
1st and 99th percentile deviations of **-29.21** and **25.31** percent at the
**1 ha** lattice cell size. The manuscript's "18 metropolitan areas" and
"deviations of minus 29.2 and plus 25.3 points at the 1 ha assessment unit"
match.

**Nowak and Greenfield 2010 — NOT VERIFIED.** The manuscript quotes 1.4
percentage points with a standard error of 0.4, rising to 5.2, across 65 mapping
zones. The published abstract does not carry any of these numbers, and three
routes to the full text failed without a way around them that should be taken:

- the USDA Forest Service PDF (`research.fs.usda.gov/download/treesearch/36593.pdf`)
  is disallowed by that site's robots.txt;
- PubMed Central returned a CAPTCHA challenge;
- the Springer article page returned HTTP 429 with an instruction not to retry.

The Forest Service hosts this paper in the public domain, so a manual download
from `research.fs.usda.gov/treesearch/36593` will settle it in a minute. These
three figures are the last substantive numbers in the manuscript that no check
here can reach, because they are not ours to recompute.

## Quoted figures read out of the source papers (28 September 2026)

Citations being correct is not the same as the numbers quoted from them being
correct. The three figures the Introduction attributes to Nowak and Greenfield
(2010) were the last unverified material in the manuscript. All three have now
been read out of the paper itself, not a secondary source.

| Manuscript says | Source text | Where |
|---|---|---|
| national underestimation of 1.4 percentage points (standard error 0.4) | "Impervious cover was also underestimated in 44 zones with an average underestimation of 1.4% (SE = 0.4%)" | Abstract |
| rising to 5.2 points within developed land with a standard error of 4.8 | "NLCD estimates in developed land also significantly underestimated impervious cover in 14 mapping zones, overestimated impervious cover in three zones, and had an overall impervious cover underestimation of 5.2% (SE = 4.8%)" | Results |
| across all 65 mapping zones | 65 mapping zones across the conterminous United States | Methods |

Read from the publisher's full text at
`link.springer.com/content/pdf/10.1007/s00267-010-9536-9.pdf`, the open-access
location that OpenAlex records for the hybrid-OA article. Earlier attempts
failed on a robots.txt disallow, a CAPTCHA and a rate limit, which is why this
sat open. The abstract was independently reconstructed from OpenAlex's inverted
index and agrees.

The companion Wickham et al. (2020) figures, 18 metropolitan areas and 1st and
99th percentile deviations of minus 29.21 and plus 25.31 at the 1 ha unit, were
verified against the publisher's record in an earlier pass.

All nine quoted values are now pinned by `make_tables.py::literature_figures()`,
so an edit to any of them fails the run and sends the editor back to the source
rather than letting the number drift.
