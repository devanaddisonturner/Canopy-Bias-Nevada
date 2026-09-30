# GitHub repository, then the Zenodo DOI

*Devan Cantrell Addison-Turner, ORCID [0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil and Environmental Engineering, Stanford University. From the reproduction package for "An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals", prepared for GIScience & Remote Sensing. Repository: https://github.com/devanaddisonturner/Canopy-Bias-Nevada Code MIT, released data CC0 1.0.*

The DOI is the hardest submission blocker: the journal requires data deposited
in a FAIR-aligned repository **prior to or at the time of submission**, and the
submission form asks for the DOI or a pre-reserved DOI. This is the route you
chose: repository first, DOI from a Zenodo release off it.

Everything below has to be run by you. Nothing in this session can push to
GitHub: it has no credentials for your account, and publishing under your name
is yours to do, not something to delegate. The file contents are finished and
verified; the commands are the whole of what is left.

## Before you start

Nothing here is blocked. The licence is chosen (MIT for the code, CC0 for the
data), `LICENSE`, `CITATION.cff`, `.zenodo.json`, `.gitignore` and
`requirements.txt` are written and checked by the harness, and the package
verifies at 522 assertions from a clean unzip.

What goes to Zenodo is `canopy_bias_reproduction_package.zip`, built by
`bash build_package.sh`. The two archives the journal gets,
`canopy_bias_submission.zip` and `canopy_bias_figures.zip`, are built separately by
`bash build_submission.sh` and are **not** part of the deposit. If you edit
`README_submission.txt`, which states the package's own file count, run the two
builders in the order `SUBMISSION_CHECKLIST.md` sets out under "Producing the files
you upload"; they depend on each other and the obvious order is the wrong one.

**One thing to do first, every time you build the package.** Some image writers
attach a content-credentials manifest (C2PA) to a file they produce, carrying an
identifier minted at write time. The figures here must not ship one: it is
provenance metadata about tooling, embedded in figures bound for a journal and a
public release, and it makes the files byte-irreproducible for no benefit. So
regenerate the figures before packaging:

```bash
for s in make_figure_studyarea.py make_figure_schematic.py \
         make_figure_matched_parcels.py make_figure_divergence.py \
         make_graphical_abstract.py; do python3 "$s"; done
```

They come out pixel-identical, and `make_tables.py` fails if a manifest is
present, so `build_package.sh` aborts rather than building a package that carries
one. If the build stops with `figures carry a content-credentials manifest`, this
is the fix.

**Regenerating the figure scripts does not cover the six panel exports.** The
Earth Engine exports under `matched_parcel_panels/` are inputs, not outputs: no
script regenerates them, and all six shipped a manifest claiming Claude had
provided the file until 29 September 2026, when they were stripped in place. The
scan meant to catch that read the package's explicit file list, which names the
directory rather than the six files, so it covered nine images and truthfully
reported all nine clean. It walks the directory now and covers fifteen. If the
build ever stops on one of those six, the fix is not to regenerate but to strip
the manifest and rewrite that file's line in `CHECKSUMS.sha256`, recording why, as
that file does for the 29 September change. Before rewriting a hash, confirm the
panel still decodes pixel-identical and that `make_figure_matched_parcels.py`
still rebuilds Figure 3 byte-identical from it.

## The metadata a wrong value gets permanently attached to

`CITATION.cff` is what GitHub's "Cite this repository" widget reads, and
`.zenodo.json` is what the deposit is built from. A wrong ORCID or a stale
affiliation in either is not a working error waiting to be spotted: it is
published, bound to a DOI and harvested. `make_tables.py` now checks both against
the manuscript, which is the authority, on the ORCID, the surname, the email and
the affiliation stem, so correcting one during revision and forgetting the others
fails the run.

`CITATION.cff` was also validated against the CFF 1.2.0 schema with
cffconvert 2.0.0 on 29 September 2026, and renders as expected. cffconvert is
deliberately **not** a dependency of this package, so the shipped check is a
required-field check rather than a schema validation; if you want the schema
check, `pip install cffconvert` and run `cffconvert --validate`.

## 1. Create the repository

On GitHub, new repository, **public**, under your account
(`devanaddisonturner`, the username confirmed current in this project's record;
`daddisonturner` is your Stanford email local-part and is **not** the GitHub
account).

Suggested name: `canopy-bias-nevada`. If you pick a different one, change the
`license-url` line in `CITATION.cff` to match, which is the only place the repo
name is written down.

Do **not** let GitHub add a README, a licence or a .gitignore during creation.
All three exist here and an initial commit from GitHub's side only creates a
conflict to resolve.

## 2. Push

From the unpacked reproduction package:

```
git init
git add .
git commit -m "Reproduction package for the canopy-bias measurement paper

Full 24,088-record parcel census, extraction and analysis code, figure
scripts, and a verification harness of 522 assertions that reproduces every
table, figure and quoted value from the released data.

Code MIT, data CC0."
git branch -M main
git remote add origin https://github.com/devanaddisonturner/Canopy-Bias-Nevada.git
git push -u origin main
```

`.gitignore` already excludes `node_modules/`, `__pycache__/` and the harness's
working CSVs. It deliberately does **not** exclude the rendered `.docx`, `.pdf`,
figure images or released CSVs: those are the record of what was submitted, and
the harness checks the rendered documents against their sources, which it cannot
do if they are absent.

Check after pushing that GitHub shows an **MIT License** label on the repository
home page and a **Cite this repository** button on the right. Both come from
files already in the package. If either is missing, the file did not upload.

## 2a. The verification workflow runs itself

`.github/workflows/verify.yml` ships in the package and runs on every push. It
installs `poppler-utils` and the pinned requirements, then runs all three gates:
the 522-assertion numeric harness, the layout checks and the colour-vision
checks. Node is deliberately not installed, because it is needed only to rebuild
the manuscript `.docx` and never to verify a number.

Verified before shipping: all three gates pass in a virtual environment built
from `requirements.txt` alone, so the workflow is not aspirational.

The first push will therefore show a green or red check beside the commit. A
claim that 522 assertions reproduce is worth more when a machine that is not
yours re-checks it on every commit, and this is the cheapest credibility the
package can buy.

## 2b. Badges, once the repository exists

Not shipped, because a badge pointing at a repository that does not exist yet
renders as a broken image. Add these two lines directly under the README's title
once the repo is up and the DOI exists:

```
[![verify](https://github.com/devanaddisonturner/Canopy-Bias-Nevada/actions/workflows/verify.yml/badge.svg)](https://github.com/devanaddisonturner/Canopy-Bias-Nevada/actions/workflows/verify.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

Replace `XXXXXXX` with the version DOI from step 4, not the concept DOI.

## 3. Deposit in Zenodo, reserving the DOI FIRST

**Reserve the DOI before uploading, rather than cutting a GitHub release and
letting Zenodo mint one afterwards.** Both routes give a valid DOI, and the
difference matters here.

If Zenodo mints the DOI from a release, the DOI does not exist until the release
is published, so the files inside that release cannot state it. The archive at
that DOI is then a package whose README, `CITATION.cff` and manuscript all say the
DOI is still to be assigned. Fixing it means cutting another release, which gets
another version DOI, whose files cite the previous one. That does not converge.

Reserving first breaks the loop: the DOI exists before the files are built, so the
deposit states its own identifier.

1. Zenodo, signed in: **New upload**.
2. In the DOI field choose **"Reserve DOI"**. Zenodo shows the DOI it will use.
   Copy it. Nothing is public yet and a reserved DOI can be abandoned.
3. Do step 5 below, filling that DOI into the package, and rebuild.
4. Return to the same draft upload and attach
   `canopy_bias_reproduction_package.zip`.
5. Check the metadata Zenodo prefilled against `.zenodo.json`: title, author name,
   ORCID, affiliation, keywords, description, licence, version.
6. **Publish.** The reserved DOI becomes live.

Then push the repository to GitHub (section 2) if you have not already, and add
the GitHub URL to the Zenodo record as a related identifier. If you also want
future versions archived automatically, switch the repository on under Zenodo's
GitHub tab now; it archives releases created after the switch, so it affects the
next version rather than this one.

`.zenodo.json` controls the record's metadata, so the title, your name,
affiliation, ORCID, keywords, description and licence are set from the file rather
than guessed from the repository name. This is worth having: the record for the
JVET package needed its licence and DOI corrected by hand afterwards.

## 4. The DOI you want is the VERSION DOI, not the concept DOI

Zenodo mints two and they differ by one digit, which this project has already
been caught by once.

- The **concept DOI** always resolves to whichever version is newest.
- The **version DOI** points at `v1.0.0` specifically.

**Cite the version DOI.** A reader following the concept DOI a year from now
lands on a different archive than the one the paper's numbers came from, which
defeats the point of depositing.

## 5. Put the DOI in four places, then rebuild and re-verify

Once you have the reserved DOI, it goes in all four and they must agree:

1. **`build_manuscript.js`**, the Data availability statement: replace the whole
   bracketed placeholder, brackets included, with a sentence naming the DOI.
   `check_layout.py --submission` fails until this is done and passes after.
2. **`CITATION.cff`**: uncomment the `doi:` line near the foot of the file and put
   the DOI on it.
3. **`README.md`**: the "How to cite" section, where the repository citation shows
   `https://doi.org/[version DOI]`.
4. **The submission form**, which asks for it directly.

Then two edits the harness will demand, because filling the DOI clears the last
blocking item and two documents still say one is outstanding:

5. **`SUBMISSION_CHECKLIST.md`**, the line under "Required before you can submit":
   change `**One item, down from three on 29 September.**` to `**Zero.**` plus
   whatever note you want.
6. **This file**, the line under "What is still blocking submission after this":
   change `**One, and it is what this document is for: the DOI itself.**` to
   `**Zero.**`.

Then rebuild, in this order, and expect a clean run:

```
node build_manuscript.js                    # the .docx now carries the DOI
python3 -c "import subprocess,sys; subprocess.run([sys.executable,'-c','pass'])"
#   reconvert the PDF from the .docx with LibreOffice or Word. The harness checks
#   the rendered PDF against its source and fails if the PDF is left behind.
python3 make_tables.py                      # expect 0 failures
python3 check_layout.py --submission        # expect exit 0, no placeholders
bash build_package.sh
bash build_submission.sh
bash build_package.sh                       # again: it ships README_submission.txt
```

The double `build_package.sh` is not a typo; the ordering is explained in
`SUBMISSION_CHECKLIST.md` under "Producing the files you upload".

**Upload the rebuilt `canopy_bias_reproduction_package.zip` to the reserved-DOI
draft, not the copy you built before the DOI existed.**

## One thing to decide in the Zenodo UI

`.zenodo.json` sets the record's licence to **MIT**, because most of the archive
is code. The datasets inside are CC0, which `LICENSE`, the README and the
Zenodo description all state explicitly. Zenodo allows only one licence field
per record, so this is a judgment call rather than a fact: if you would rather
the record read CC0, because the journal's requirement is about *data*
deposition, it is one dropdown in the Zenodo UI and nothing else needs to
change. Either reading is defensible and both are open licences.

## What is still blocking submission after this

**One, and it is what this document is for: the DOI itself.** The Funding
statement and the Acknowledgements were both written on 29 September, so the
manuscript now carries a single bracketed placeholder, in the data availability
statement, waiting for the DOI this guide produces.

One thing that is not a manuscript item and is still open: **the charge**. The APC
is $3,565 plus VAT on an fully open access journal, **Stanford Libraries lists no
Taylor & Francis agreement**, and waivers "may not be considered after
submission". Naming the funders of the research is not the same as arranging who
pays the charge.
