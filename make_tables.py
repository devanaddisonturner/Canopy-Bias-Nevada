#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# Devan Cantrell Addison-Turner, ORCID 0000-0002-2511-3680
# Department of Civil and Environmental Engineering, Stanford University
#
# From the reproduction package for "An optically independent administrative
# reference for validating built-surface products, and the tree-canopy bias it
# reveals", a manuscript prepared for GIScience & Remote Sensing. Not yet
# published; cite the repository until it is. Citation metadata: CITATION.cff.
#
# https://github.com/devanaddisonturner/Canopy-Bias-Nevada
# Code MIT, released data CC0 1.0.
# ---------------------------------------------------------------------------
"""
Regenerate every table in the manuscript, and the Figure 1 parcel selection,
directly from nevada_canopy_bias_rowlevel.csv.

    python3 make_tables.py [nevada_canopy_bias_rowlevel.csv] [--csv outdir]

WHY THIS FILE EXISTS. The manuscript's tables are typeset with literal numbers
in build_manuscript.js. This script recomputes each of those numbers from the
released data and ASSERTS that it matches what the manuscript prints, so the
typeset values are verifiable rather than trusted. If an assertion fails, the
manuscript and the data have diverged and the manuscript is wrong.

Covers:
    Figure 4 physical bound and measured impervious by canopy decile
             (a table in an earlier draft; now a figure)
    Table 1  canopy coefficient under the common specification, with HC1 and
             Conley spatial HAC at 1, 2 and 5 km
    Table 2  detection-failure rate by canopy quintile within density quartile
    Table 3  four products, four decision rules
    Table 4  validation checks and sensitivity, incl. the garage sensitivity
    Figure 3 matched-pair selection for the two illustrated parcels
    plus     the footprint identity: roof = floor/storeys + garage
    plus     the block-cluster grid-origin sensitivity reported in Section 2.4

Everything uses the analysis sample: parcels built on or before 2019, n = 21,931.
"""
# ---------------------------------------------------------------------------
# Run from anywhere. IDLE's Run Module, a double-click, and
# "python3 /path/to/make_tables.py" all leave the working directory somewhere
# other than this file's folder, and every input below is named relatively.
# Without this the run dies on the first open() with a FileNotFoundError that
# says nothing about the real cause.
#
# This block sits AFTER the docstring on purpose. It used to sit before it,
# which made the docstring not the module's first statement, so
# `help(make_tables)` and `pydoc make_tables` showed nothing at all and the
# shebang, pushed to line 12, did nothing either. Both are only meaningful in
# the first position they can occupy.
# ---------------------------------------------------------------------------
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE and _os.getcwd() != _HERE:
    _os.chdir(_HERE)

import sys
import argparse
from collections import defaultdict

import numpy as np
import numpy as _np
import pandas as pd

H = ['canopy', 'ac', 'sqft', 'slope', 'n100']   # the common covariate set
FAIL = []
SKIPPED = []

# Every passing assertion in this file reports itself on a line beginning "ok".
# The README states how many there are, and that number drifted badly once: it
# read 147 while the harness ran 296. Counting them here lets the last check in
# main() hold the README to the truth. This module-level definition shadows the
# builtin for every function below, so no call site needs to change.
# Optional dependencies. Two checks need SciPy or statsmodels and skip cleanly
# without them, which silently lowered the assertion count and made the README
# check FAIL in a minimal environment: a reviewer with neither package saw 419
# against a claimed 424 and was told the package was wrong when it was not.
# The count is now stated for both environments and asserted in both.
OPTIONAL_MISSING = []   # absent packages that REDUCE the assertion count
MISSING_TOOLS = []      # absent external tools that skip an uncounted check

OK = [0]
_print = print

# --quiet. A full run prints 642 lines, 469 of them "ok". That is the right
# default for an author checking a change, and the wrong one for a reviewer who
# wants to know whether the package verifies: they have to scroll past everything
# that worked to find out. In quiet mode the per-check detail lines are counted
# but not printed, and section headers, every failure and the closing verdict
# still are, which is about sixty lines. Nothing about what is checked changes.
QUIET = [False]


def print(*args, **kwargs):          # noqa: A001 - deliberate module-level shadow
    if args and isinstance(args[0], str) and args[0].lstrip().startswith('ok'):
        OK[0] += 1
    if QUIET[0] and args and isinstance(args[0], str):
        # Per-check detail is indented by convention; headers and verdicts are not.
        body = args[0].lstrip('\n')
        if body[:1] == ' ' and 'FAIL' not in args[0]:
            return
    _print(*args, **kwargs)


def truncate(f):
    """A cell cannot be more than wholly impervious, so the bound is truncated at
    100 per cent of cell area. This binds where a structure larger than one cell is
    charged in full to the cell holding its centroid. Applied to the bound with and
    without garages, and to every product-versus-bound breach indicator derived from
    them, so no reported quantity rests on a physically impossible bound."""
    f['imp_floor_raw'] = f.imp_floor_px.copy()
    f['imp_floor_px'] = f.imp_floor_raw.clip(upper=100)
    f['floorA_raw'] = f.floorA.copy()
    f['floorA'] = f.floorA_raw.clip(upper=100)
    f['below'] = f.nlcd < f.imp_floor_px
    f['belowA'] = f.nlcd < f.floorA
    for col, prod in [('below_dw', 'dw'), ('below_wc', 'wc'), ('below_ghsl', 'ghsl')]:
        if col in f.columns and prod in f.columns:
            f[col] = f[prod] < f.imp_floor_px
    return f


def load(path):
    d = truncate(pd.read_csv(path, dtype={'apn': str, 'px': str}))
    m = d[(d.yr.notna()) & (d.yr <= 2019)].copy()
    # local planar coordinates in km, for the spatial variance estimators
    lat0 = m.lat.mean()
    m['xk'] = (m.lon - m.lon.mean()) * 111.32 * np.cos(np.radians(lat0))
    m['yk'] = (m.lat - m.lat.mean()) * 110.57
    return d, m


# ---------------------------------------------------------------- estimation
def ols(df, y, xs=H):
    X = np.column_stack([np.ones(len(df))] + [df[v].astype(float).values for v in xs])
    Y = df[y].astype(float).values
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ (X.T @ Y)
    e = Y - X @ b
    r2 = 1 - (e @ e) / ((Y - Y.mean()) @ (Y - Y.mean()))
    return X, Y, b, e, XtXi, r2


def se_hc1(X, e, XtXi, which=1):
    n, k = X.shape
    V = XtXi @ ((X * (e ** 2)[:, None]).T @ X) @ XtXi * n / (n - k)
    return np.sqrt(np.diag(V))[which]


# The largest dense block se_conley will build, in pairs. 4 million pairs is
# about 32 MB as float64, so peak memory stays near a hundred megabytes rather
# than tracking the size of the busiest grid cell.
CONLEY_BLOCK = 4_000_000


def se_conley(X, e, XtXi, xs, ys, cutoff, which=1):
    """Conley spatial HAC, Bartlett kernel, grid-accelerated. No origin choice.

    Chunked, and the reason is measured rather than precautionary. Settlement in
    this frame is clustered: five of 47 occupied 5 km cells hold half the
    parcels. The unchunked version built one dense |I| x |J| distance matrix per
    pair of neighbouring cells, so the busiest cell alone produced an array of
    roughly 11,000 x 11,000 float64, about 968 MB, and a full harness run peaked
    at 918 MB resident. That is enough to be killed on a modest laptop, and it
    already killed one clean-unzip verification in this project.

    The rows of I are now processed in blocks sized so no intermediate exceeds
    CONLEY_BLOCK pairs. Every pair inside the cutoff is still visited exactly
    once and weighted by the same Bartlett kernel, so the estimate is unchanged:
    summation is just reordered, and the 522 assertions that depend on these
    t-values are what proves it.
    """
    n, k = X.shape
    Xe = X * e[:, None]
    gx = np.floor(xs / cutoff).astype(np.int64)
    gy = np.floor(ys / cutoff).astype(np.int64)
    idx = defaultdict(list)
    for i, (a, c) in enumerate(zip(gx, gy)):
        idx[(a, c)].append(i)
    idx = {key: np.array(v) for key, v in idx.items()}
    meat = np.zeros((k, k))
    for (a, c), I in idx.items():
        Xi, xi, yi = Xe[I], xs[I], ys[I]
        for da in (-1, 0, 1):
            for dc in (-1, 0, 1):
                J = idx.get((a + da, c + dc))
                if J is None:
                    continue
                xj, yj, Xj = xs[J], ys[J], Xe[J]
                step = max(1, CONLEY_BLOCK // max(1, len(J)))
                for b in range(0, len(I), step):
                    sl = slice(b, b + step)
                    dist = np.sqrt((xi[sl, None] - xj[None, :]) ** 2 +
                                   (yi[sl, None] - yj[None, :]) ** 2)
                    meat += Xi[sl].T @ (np.clip(1.0 - dist / cutoff, 0, None) @ Xj)
    V = XtXi @ meat @ XtXi * n / (n - k)
    return np.sqrt(np.diag(V))[which]


def se_block(X, e, XtXi, xs, ys, L, ox=0.0, oy=0.0, which=1):
    """Block cluster. NOTE the ox, oy arguments: the answer depends on them."""
    n, k = X.shape
    gid = (np.floor((xs + ox) / L).astype(np.int64) * 100003 +
           np.floor((ys + oy) / L).astype(np.int64))
    Xe = X * e[:, None]
    meat = np.zeros((k, k))
    for g in np.unique(gid):
        sm = Xe[gid == g].sum(0)
        meat += np.outer(sm, sm)
    G = len(np.unique(gid))
    V = XtXi @ meat @ XtXi * (G / (G - 1)) * ((n - 1) / (n - k))
    return np.sqrt(np.diag(V))[which], G


# ---------------------------------------------------------------- assertions
# Every value checked, as (label, the figure the manuscript prints). Used to
# build the reader's index at the end of a run: a reviewer who wants to verify
# one number in the abstract should not have to guess which of 522 lines covers
# it. Derived from the checks themselves rather than hand-kept, because a
# hand-kept index is the thing this harness has been bitten by three times.
CHECKED = []


def check(label, printed, computed, tol):
    ok = abs(float(printed) - float(computed)) <= tol
    CHECKED.append((label, float(printed)))
    if not ok:
        FAIL.append((label, printed, round(float(computed), 6)))
    print(f"   {'ok ' if ok else 'FAIL'}  {label:<46s} manuscript {printed:<11} computed {round(float(computed), 4)}")


def shipped_checklists_match_the_placeholders():
    """Do the shipped to-do lists still describe what is actually outstanding?

    They did not. An hour after the Funding statement and the Acknowledgements
    were written, `SUBMISSION_CHECKLIST.md` still listed "Funder name and grant
    number" and "Acknowledgements" as required before submission, and
    `GITHUB_AND_ZENODO.md` still opened its closing section with "Three, all
    needing you". `check_layout.py::placeholders` had the same rot in its own
    docstring, "Four are outstanding by design", a fortnight after the number
    moved.

    These are the files the author uses as a to-do list. Being told to do two
    finished tasks is worse than a stale number in prose, because it is acted on.

    **Third occurrence of the shipped-docs supersession class**, after
    `LICENSE_DECISION.md` and the author-guidelines compliance doc, and the first
    one predicted rather than stumbled on: the class was checked precisely because
    it had already bitten twice.

    The invariant is clean and self-maintaining. The bracketed placeholders in the
    manuscript **are** the machine-checkable definition of what is outstanding, so
    any shipped document that states a count of blocking items must state that
    number. No list of item names to keep in step, which is what went stale.
    """
    import os
    import re
    print('\nCHECKLISTS  the shipped to-do lists against the actual placeholders')
    try:
        import importlib.util as _u
        spec = _u.spec_from_file_location('_cl', 'check_layout.py')
        cl = _u.module_from_spec(spec)
        spec.loader.exec_module(cl)
        n = len(cl.placeholders())
    except Exception as exc:                            # noqa: BLE001
        MISSING_TOOLS.append('check_layout.py (checklist count)')
        _print('   .    could not read the placeholder count (%s)' % exc.__class__.__name__)
        return
    print('   ok   the manuscript carries %d bracketed placeholder(s)' % n)
    WORD = {'zero': 0, 'no': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
    DOCS = [
        ('SUBMISSION_CHECKLIST.md', r'## Required before you can submit(.{0,400})'),
        ('GITHUB_AND_ZENODO.md', r'## What is still blocking submission after this(.{0,400})'),
    ]
    for doc, pat in DOCS:
        if not os.path.exists(doc):
            MISSING_TOOLS.append('%s (checklist count)' % doc)
            _print('   .    %s absent, not checked' % doc)
            continue
        m = re.search(pat, open(doc, encoding='utf-8').read(), re.S)
        if not m:
            FAIL.append(('%s blocking section' % doc, 'present', 'heading not found',
                         ('expected', 'found')))
            print('   FAIL  %s no longer has the section this check reads' % doc)
            continue
        found = re.search(r'\*\*(\w+)[ ,.]', m.group(1)) or re.search(r'\b(\w+)\b', m.group(1))
        raw = found.group(1).lower() if found else ''
        stated = WORD.get(raw, int(raw) if raw.isdigit() else None)
        if stated is None:
            FAIL.append(('%s states a count of blocking items' % doc, 'a number',
                         'none parsed', ('expected', 'found')))
            print('   FAIL  %s does not open its blocking section with a count' % doc)
        else:
            check('%s blocking items' % doc, n, stated, 0)


def zenodo_description_figures(builder='build_manuscript.js'):
    """Every number in the DOI description, against the manuscript.

    `.zenodo.json`'s description is the text that goes on the Zenodo record. It
    restates the paper's findings: 21,931 parcels, a 24,088-record census, 18 to 22
    percentage points, a 31 point higher probability, the 30 m cell. Once the
    deposit exists that text is **permanent, public and harvested**, bound to a DOI
    and not revisable in the way a manuscript is during revision.

    Only the assertion count in it was pinned. The scientific numbers were checked
    against nothing at all.

    The oversight has a shape worth naming. `release_metadata_agrees_with_the_manuscript`
    was written a few passes ago to hold this same file's ORCID, email and
    affiliation to the manuscript, on the argument that a wrong value there is
    published rather than merely wrong. **The identity fields were checked and the
    science in the same file was not.** The permanence argument applies to both and
    was applied to one.

    Each figure must be either a value this harness asserts, or present in the
    manuscript source. A figure in neither is one the DOI record would state and
    the paper would not.
    """
    import json
    import os
    import re
    print('\nZENODO  every figure in the DOI description, against the manuscript')
    if not (os.path.exists('.zenodo.json') and os.path.exists(builder)):
        MISSING_TOOLS.append('.zenodo.json or the builder (DOI figures)')
        _print('   .    .zenodo.json or the builder absent, DOI figures not checked')
        return
    try:
        desc = json.load(open('.zenodo.json', encoding='utf-8')).get('description', '')
    except ValueError:
        FAIL.append(('.zenodo.json', 'valid JSON', 'unparseable',
                     ('expected', 'found')))
        print('   FAIL  .zenodo.json is not valid JSON')
        return
    src = open(builder, encoding='utf-8').read()
    # Numbers that are about the package or the licence, not about the findings.
    # Each is declared rather than skipped by a pattern, so the exemption is visible.
    NOT_A_FINDING = {
        '1.0': 'the CC0 1.0 licence version',
    }
    # The assertion count is in that description legitimately and is not a finding
    # about the county. It is already held to the README by the cross-file count
    # check, so exempt it here rather than double-pinning it. Read from the README
    # rather than written as a literal, so this exemption cannot go stale the next
    # time the count changes, which it has done on every pass for two weeks.
    if os.path.exists('README.md'):
        rc = re.search(r'([\d,]+)\s+assertions',
                       open('README.md', encoding='utf-8').read())
        if rc:
            NOT_A_FINDING[rc.group(1)] = ('the assertion count, pinned by the '
                                          'cross-file count check')
            NOT_A_FINDING[rc.group(1).replace(',', '')] = (
                'the assertion count, pinned by the cross-file count check')
    asserted = {round(abs(v), 6) for _, v in CHECKED}
    unbacked = []
    checked = 0
    for raw in sorted(set(re.findall(r'\b\d[\d,]*(?:\.\d+)?\b', desc))):
        if raw in NOT_A_FINDING:
            _print('   .    %-8s %s, not a finding' % (raw, NOT_A_FINDING[raw]))
            continue
        val = round(float(raw.replace(',', '')), 6)
        in_harness = val in asserted
        in_text = raw in src or raw.replace(',', '') in src
        if in_harness or in_text:
            checked += 1
            where = 'asserted by this harness' if in_harness else 'stated in the manuscript'
            _print('   .    %-8s %s' % (raw, where))
        else:
            unbacked.append(raw)
    if unbacked:
        FAIL.append(('the DOI description states figures the paper does not',
                     'every figure backed', ', '.join(unbacked),
                     ('expected', 'found')))
        print('   FAIL  .zenodo.json states %s, which is neither asserted here nor '
              'in the manuscript. That text becomes permanent on deposit.'
              % ', '.join(unbacked))
    elif checked < 4:
        FAIL.append(('DOI description coverage', 'at least 4 figures checked',
                     '%d' % checked, ('expected', 'found')))
        print('   FAIL  only %d figures found in the DOI description; this check is '
              'not reaching it' % checked)
    else:
        print('   ok   all %d figures in the DOI description are backed by the '
              'manuscript or this harness' % checked)


def reference_log_is_current():
    """Does REFERENCES_VERIFIED.md still describe the manuscript's reference list?

    It ships and it opens "27 of 27 verified". If a reference is added during
    revision it goes stale silently, and it is the document a reviewer would read
    to decide whether the citations were checked. Two shipped documents have
    already gone stale this way, `LICENSE_DECISION.md` and the compliance doc, so
    this one is pinned before it becomes the third.

    The headline count must equal the manuscript's reference entries, and the two
    sub-counts, entries with a DOI and entries without, must sum to it.
    """
    import os
    import re
    print('\nREFERENCE LOG  REFERENCES_VERIFIED.md against the manuscript')
    if not os.path.exists('REFERENCES_VERIFIED.md'):
        MISSING_TOOLS.append('REFERENCES_VERIFIED.md (reference log)')
        _print('   .    REFERENCES_VERIFIED.md absent, not checked')
        return
    log = open('REFERENCES_VERIFIED.md', encoding='utf-8').read()
    src = open('build_manuscript.js', encoding='utf-8').read()
    i = src.find("h1('References')")
    entries = len(re.findall(r"\n\s*'([A-Z][^']{20,})'", src[i:])) if i >= 0 else 0
    head = re.search(r'\*\*(\d+) of (\d+) verified', log) or \
        re.search(r'(\d+) of (\d+) verified', log)
    if not head:
        FAIL.append(('reference log headline', 'an "N of N verified" line',
                     'not found', ('expected', 'found')))
        print('   FAIL  REFERENCES_VERIFIED.md no longer states an N of N total')
        return
    check('reference log total matches the manuscript', entries, int(head.group(2)), 0)
    check('reference log reports all of them verified', int(head.group(2)),
          int(head.group(1)), 0)
    subs = [int(a) for a, b in re.findall(r'\((\d+) of (\d+) verified\)', log)]
    if subs:
        check('reference log sub-counts sum to the total', int(head.group(2)),
              sum(subs), 0)
    else:
        _print('   .    no sub-counts stated, nothing to sum')


def reference_implementations_agree():
    """Do the two scripts the README tells a reviewer to run print the paper's numbers?

    Nothing checked. `analyze_canopy_bias.py` and `runoff_consequence.py` are both
    listed under "Run these" in the README, and both print headline results:
    the canopy coefficient, the detection-failure coefficient, the analysis sample
    size, the breach rate. They are shipped reference implementations, written
    independently of this harness, which is exactly what makes them worth running
    and exactly why a drift between them and the manuscript would be damaging.

    A reviewer who runs the script the README points them at and sees a number
    that is not the paper's does not conclude the script is stale. They conclude
    the paper is wrong.

    Run as subprocesses and their printed values compared to the manuscript's,
    looked up in CHECKED rather than restated, so these cannot disagree with the
    values they are supposed to corroborate. Adds about 9 seconds, re-measured on
    29 September 2026: analyze_canopy_bias.py takes 8.3 s and
    runoff_consequence.py 0.4 s. The figure here read 14 seconds until then, from
    a measurement taken before both scripts' Conley implementations were chunked.
    """
    import os
    import re
    import subprocess
    print('\nREFERENCE IMPLEMENTATIONS  their printed output against the manuscript')
    want = {}
    for lab, pv in CHECKED:
        want.setdefault(lab, pv)
    need = ('T1 nlcd coefficient', '4.2 detection failure, real storeys',
            '2.2 sample size after merging extras')
    if not all(k in want for k in need):
        FAIL.append(('reference implementation comparison',
                     'the manuscript values checked first',
                     'missing %s' % ', '.join(k for k in need if k not in want),
                     ('expected', 'found')))
        print('   FAIL  the manuscript values are not available yet')
        return
    CASES = [
        ('analyze_canopy_bias.py', [
            (r'HC1\s+b=\s*(-?[\d.]+)', 'canopy coefficient',
             want['T1 nlcd coefficient'], 0.001),
            (r'below_floor, 2 km\s+b=\s*\+?(-?[\d.]+)', 'detection-failure coefficient',
             want['4.2 detection failure, real storeys'], 0.0005),
            (r'HC1\s+b=\s*-?[\d.]+\s+se=[\d.]+\s+t=\s*-?[\d.]+\s+n=(\d+)',
             'analysis sample size', want['2.2 sample size after merging extras'], 0),
        ]),
        ('runoff_consequence.py', [
            (r'n = (\d+) parcels built on or before 2019', 'analysis sample size',
             want['2.2 sample size after merging extras'], 0),
        ]),
    ]
    for script, probes in CASES:
        if not os.path.exists(script):
            MISSING_TOOLS.append('%s (reference implementation)' % script)
            _print('   .    %s absent, not run' % script)
            continue
        try:
            r = subprocess.run([sys.executable, script], capture_output=True,
                               text=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as exc:
            FAIL.append(('%s could not be run' % script, 'runs',
                         exc.__class__.__name__, ('expected', 'found')))
            print('   FAIL  %s could not be run: %s' % (script, exc))
            continue
        if r.returncode != 0:
            FAIL.append(('%s exit status' % script, 0, r.returncode,
                         ('expected', 'found')))
            print('   FAIL  %s exited %d; the README tells reviewers to run it'
                  % (script, r.returncode))
            continue
        for pat, what, target, tol in probes:
            mm = re.search(pat, r.stdout)
            if not mm:
                FAIL.append(('%s prints its %s' % (script, what), 'yes',
                             'the line was not found', ('expected', 'found')))
                print('   FAIL  %s no longer prints its %s in a form this check '
                      'can read' % (script, what))
                continue
            check('%s %s' % (script.replace('.py', ''), what),
                  round(abs(target), 4), abs(float(mm.group(1))), max(tol, 1e-9))


def footprint_file_integrity(a):
    """Is the released footprint file consistent with the released parcel data?

    Nothing checked. `ms_footprint_validation.csv` carries Section 3.6, the
    independent-footprint validation of the bound, which is among the paper's
    strongest arguments: a different sensor and vendor reproduce the same canopy
    gradient, 1.01 open against 0.54 canopied. The harness asserted the statistics
    computed **from** that file and never asked whether the file itself describes
    the same cells and the same roofs as the released parcel census. A stale file,
    a mis-joined one, or one built against an earlier frame would have sailed
    through every check and taken Section 3.6 with it.

    Measured: **seven of its eleven columns reproduce exactly** from
    nevada_canopy_bias_rowlevel.csv restricted to the analysis sample, plus
    parcel_edge_exact.csv. `i` and `j` from the edge file; `canopy`, `nlcd`,
    `roof` and `n` from the cell-level aggregation; `dec` as the cell-level canopy
    decile. That is the join, the frame and the roof arithmetic all confirmed
    against the census.

    Two columns are deliberately not asserted here. `allinside` reproduces for
    99.7 percent under a square-footprint approximation of the roof, which is
    close enough to show the column means what it says and not close enough to
    claim the original rule, so it is reported rather than pinned. `ms_m2` is the
    Microsoft Buildings footprint area and comes from Earth Engine, so no local
    check can reach it; it is the one column that genuinely cannot be verified
    from this package.
    """
    import os
    print('\nFOOTPRINT FILE  ms_footprint_validation.csv against the parcel census')
    if not (os.path.exists('ms_footprint_validation.csv')
            and os.path.exists('parcel_edge_exact.csv')):
        MISSING_TOOLS.append('the footprint or edge CSV (footprint integrity)')
        _print('   .    a required CSV is absent, footprint integrity not checked')
        return
    v = pd.read_csv('ms_footprint_validation.csv')
    e = pd.read_csv('parcel_edge_exact.csv', dtype={'apn': str})
    # The analysis sample, not the full frame. Passing the full 24,088 rows drops
    # the agreement to 98.3 percent, because the post-2019 placebo parcels change
    # the cell means and the parcel counts. That the sample boundary is what
    # restores exact agreement is itself evidence the file was built on it.
    a = a.astype({'apn': str})

    g = a.groupby('px').agg(canopy=('canopy', 'mean'), nlcd=('nlcd', 'mean'),
                            roof=('pixel_roof_m2', 'first'), n=('nlcd', 'size')).reset_index()
    g['dec'] = pd.qcut(g.canopy, 10, labels=False)
    m = v.merge(g, on='px', how='left', suffixes=('_s', '_c'))
    check('3.6 sampled cells present in the analysis sample',
          len(v), int(m.canopy_c.notna().sum()), 0)
    for col, tol in (('canopy', 1e-4), ('nlcd', 1e-4), ('roof', 1e-3), ('n', 0)):
        agree = 100 * np.isclose(m[col + '_s'], m[col + '_c'],
                                 rtol=0, atol=max(tol, 1e-9)).mean()
        check('3.6 %s reproduces from the census (%%)' % col, 100, agree, 0.01)
    check('3.6 dec is the cell-level canopy decile (%)', 100,
          100 * (m.dec_s == m.dec_c).mean(), 0.01)

    # `bound` was missed entirely in the first version of this check, and the
    # miscount went unnoticed: seven columns verified plus allinside plus ms_m2
    # plus the px key accounts for ten of eleven. The one left out is the paper's
    # central quantity. It is roof / 900 as a percentage, exactly.
    check('3.6 bound is roof over the 900 m2 cell (% agreement)', 100,
          100 * np.isclose(v.bound, v.roof / 900.0 * 100.0,
                           rtol=0, atol=1e-4).mean(), 0.01)
    # And it is NOT truncated, while Equation 2's ceiling is applied everywhere
    # the paper uses the bound. One cell of 700 exceeds 100 percent of its cell.
    # Inert for Section 3.6, whose ratios are taken against `roof`, but this is a
    # released CC0 column and a reuser could reasonably read it as the paper's
    # bound. Asserted so the difference is on the record rather than a surprise.
    check('3.6 cells whose untruncated bound exceeds 100 percent of the cell',
          1, int((v.bound > 100).sum()), 0)

    ij = a[['apn', 'px']].merge(e[['apn', 'i', 'j']], on='apn').drop_duplicates('px')
    k = v[['px', 'i', 'j']].merge(ij, on='px', suffixes=('_s', '_c'))
    check('3.6 cell indices reproduce from the edge file (%)', 100,
          100 * ((k.i_s == k.i_c) & (k.j_s == k.j_c)).mean(), 0.01)

    # Reported, not pinned: close enough to show the column means what it says,
    # not close enough to claim the original rule.
    w = a.merge(e[['apn', 'dedge']], on='apn', how='left')
    w['inside'] = w.dedge >= np.sqrt(w.roof_m2) / 2.0
    cell = w.groupby('px').agg(allinside=('inside', 'all')).reset_index()
    q = v[['px', 'allinside']].merge(cell, on='px', suffixes=('_s', '_c'))
    _print('   .    allinside agrees for %.1f%% under a square-footprint rule '
           '(reported, not asserted)'
           % (100 * (q.allinside_s == q.allinside_c).mean()))
    _print('   .    ms_m2 is the Earth Engine column and cannot be checked locally')


def edge_file_provenance(m):
    """Three claims about parcel_edge_exact.csv, two of them previously unchecked.

    The README said the exact cell indices "reproduce the released `px` for 99.99
    percent of parcels, which is the check that the two pipelines agree" and that
    recomputing from the rounded coordinates "misclassifies roughly one parcel in
    five". Neither number was asserted anywhere. The first is the only evidence
    that the edge file and the released data describe the same grid, and the
    second is the whole reason the edge file has to exist.

    Measured here. The first is exactly right. The second is one parcel in **six**,
    not five: recomputation from the released coordinates agrees for 84.33 percent.

    The third claim is new and matters more than either. `make_parcel_edge_exact.py`
    now ships as the producing script, but **the released CSV is not adequate input
    to it**, because the full-precision centroids it needs are not in this package.
    So the provenance gap for this file was never "the script was not retained". It
    was, and remains, that the input is not released. Pinning the 84.33 figure
    here is what stops that being quietly restated as reconstructible.
    """
    import os
    print('\nEDGE FILE  parcel_edge_exact.csv against the released grid')
    if not os.path.exists('parcel_edge_exact.csv'):
        MISSING_TOOLS.append('parcel_edge_exact.csv (edge provenance)')
        _print('   .    parcel_edge_exact.csv absent, provenance not checked')
        return
    e = pd.read_csv('parcel_edge_exact.csv', dtype={'apn': str})
    j = m[['apn', 'px']].astype({'apn': str}).merge(e[['apn', 'i', 'j']], on='apn')
    joined = j.i.astype(str) + '_' + j.j.astype(str)
    check('edge indices reproduce the released px (%)',
          99.99, 100 * (joined == j.px.astype(str)).mean(), 0.01)

    # The same computation from the released rounded coordinates, which is what a
    # reviewer working from the release alone would be forced to do.
    try:
        import importlib.util as _u
        spec = _u.spec_from_file_location('_mkedge', 'make_parcel_edge_exact.py')
        mk = _u.module_from_spec(spec)
        spec.loader.exec_module(mk)
    except (FileNotFoundError, ImportError, AttributeError):
        MISSING_TOOLS.append('make_parcel_edge_exact.py (edge provenance)')
        _print('   .    make_parcel_edge_exact.py absent, rounding cost not checked')
        return
    got = mk.build(m.astype({'apn': str}))
    k = e.merge(got, on='apn', suffixes=('_ship', '_new'))
    agree = 100 * ((k.i_ship == k.i_new) & (k.j_ship == k.j_new)).mean()
    check('cell indices recomputable from the RELEASED coordinates (%)',
          mk.AGREEMENT_FROM_ROUNDED, agree, 0.01)
    check('dedge recomputable from the released coordinates, within 0.1 m (%)',
          mk.DEDGE_WITHIN_TENTH_FROM_ROUNDED,
          100 * (np.abs(k.dedge_ship - k.dedge_new) < 0.1).mean(), 0.05)
    if agree < 99.0:
        print('   ok   the released coordinates are NOT adequate input, as documented')
    else:
        FAIL.append(('edge file reconstructibility',
                     'the released coordinates are inadequate, as documented',
                     'they now agree at %.2f percent' % agree,
                     ('documented', 'measured')))
        print('   FAIL  the released coordinates now reproduce the edge file at '
              '%.2f percent; the documentation says they cannot and must be '
              'updated' % agree)


def abstract_headline_forms():
    """The abstract's three headline claims, in the rounded form it prints them.

    The reader's index found this. The abstract says canopy is associated with
    "18 to 22 percentage points" less measured impervious surface and a "31 point
    higher probability" of falling below the bound. Those are the three numbers
    most people will ever read from this paper, and **none of the three was
    asserted in the form the abstract states**. The underlying coefficients were:
    minus 18.1254 net of the light layers, minus 21.8958 for the headline
    specification, plus 0.3119 for detection failure. The rounded, ranged forms
    were not, so a reader matching "22" against the output got "upward bias from a
    flat storey count" and "F4 decile 8 bound", two unrelated quantities that
    happen to equal 22, and matching "31" got two more coincidences.

    Asserted here against the already-verified coefficients rather than
    recomputed, by looking their labels up in CHECKED, so these can never
    disagree with the values they round.
    """
    print('\nABSTRACT  the three headline claims, as the abstract prints them')
    want = {'3.5 canopy, + lights and elevation': None,
            'T1 nlcd coefficient': None,
            '4.2 detection failure, real storeys': None}
    for lab, pv in CHECKED:
        if lab in want and want[lab] is None:
            want[lab] = pv
    absent = [k for k, v in want.items() if v is None]
    if absent:
        FAIL.append(('abstract headline forms', 'the three coefficients checked '
                     'before this runs', 'missing %s' % ', '.join(absent),
                     ('expected', 'found')))
        print('   FAIL  cannot build the abstract claims: %s not yet checked'
              % ', '.join(absent))
        return
    lo = abs(want['3.5 canopy, + lights and elevation'])
    hi = abs(want['T1 nlcd coefficient'])
    check('abstract range low end, net of the light layers (pts)',
          18, round(lo), 0)
    check('abstract range high end, headline specification (pts)',
          22, round(hi), 0)
    check('abstract detection-failure probability (pts)',
          31, round(100 * want['4.2 detection failure, real storeys']), 0)
    if lo < hi:
        print('   ok   the abstract states the range low to high, %.1f to %.1f'
              % (lo, hi))
    else:
        FAIL.append(('abstract range order', 'low then high',
                     '%.1f then %.1f' % (lo, hi), ('expected', 'found')))
        print('   FAIL  the abstract range is stated backwards, %.1f then %.1f'
              % (lo, hi))


def abstract_figures_are_each_verified(path='build_manuscript.js'):
    """Is every number in the abstract actually verified, and can a reader find where?

    `abstract_lint` proves each abstract figure appears somewhere in the body or a
    table. That is textual presence, not verification: a number can appear in both
    places and be checked in neither.

    This asks the stronger question and answers a reader's one at the same time.
    For each figure the abstract prints, it names the assertions whose manuscript
    value is that figure. A reviewer who reads "18 to 22 percentage points" and
    wants to see it verified currently has to guess which of 522 lines covers it;
    the two ends of that range turn out to be labelled "3.5 canopy, + lights and
    elevation" and "T1 nlcd coefficient", in different sections, and nothing said
    so. The abstract is the most-read part of the paper and was the least
    navigable part of the output.

    A figure with no covering assertion is reported, not failed: several abstract
    numbers are sample sizes and percentages carried in prose that other checks
    cover by other means. The count of covered figures is asserted so the index
    cannot quietly empty out.
    """
    import re as _re
    import os
    print('\nREADER\'S INDEX  where each figure in the abstract is verified')
    if not os.path.exists(path):
        MISSING_TOOLS.append('the manuscript builder (reader index)')
        _print('   .    %s absent, index not built' % path)
        return
    lines = open(path, encoding='utf-8').read().split('\n')
    h = [i for i, l in enumerate(lines) if "h1('Abstract'" in l]
    m = _re.search(r"body\.push\(p\('((?:[^'\\\\]|\\\\.)*)'", lines[h[0] + 1]) if h else None
    if not m:
        FAIL.append(('reader index: abstract located', 'yes', 'no',
                     ('expected', 'found')))
        print('   FAIL  the abstract could not be located, so no index was built')
        return
    figs = []
    for raw in _re.findall(r'\b\d[\d,]*(?:\.\d+)?\b', m.group(1)):
        v = float(raw.replace(',', ''))
        if (raw, v) not in figs:
            figs.append((raw, v))
    covered = 0
    for raw, v in figs:
        hits = [lab for lab, pv in CHECKED if abs(abs(pv) - v) < 1e-9]
        if hits:
            covered += 1
            # An assertion that names itself as the abstract's own claim comes
            # first; alphabetical order put two coincidental matches ahead of it.
            ranked = sorted(set(hits), key=lambda s: (not s.startswith('abstract'), s))
            _print('   %-10s %s' % (raw, '; '.join(ranked[:3])))
        else:
            _print('   %-10s (carried in prose; covered by another check, not by value)'
                   % raw)
    if covered < 5:
        FAIL.append(('reader index coverage', 'at least 5 abstract figures '
                     'mapped to an assertion', '%d of %d' % (covered, len(figs)),
                     ('expected', 'found')))
        print('   FAIL  only %d of the abstract\'s %d figures map to an assertion; '
              'the index is not doing its job' % (covered, len(figs)))
    else:
        print('   ok   %d of the abstract\'s %d figures map to a named assertion'
              % (covered, len(figs)))


# ---------------------------------------------------------------- the tables
def table1(m, csvdir=None):
    print("\nFIGURE 4  physical bound and measured impervious by canopy decile")
    m = m.copy()
    m['dec'] = pd.qcut(m.canopy, 10, labels=False)
    g = m.groupby('dec').agg(canopy=('canopy', 'mean'), bound=('imp_floor_px', 'mean'),
                             nlcd=('nlcd', 'mean'), below=('below', 'mean'),
                             zero=('zero', 'mean'), n=('nlcd', 'size'))
    g['below'] *= 100
    g['zero'] *= 100
    t = g.round({'canopy': 2, 'bound': 1, 'nlcd': 1, 'below': 1, 'zero': 1})
    print(t.to_string())
    printed = {  # exactly as typeset in the manuscript
        'canopy': [0.01, 0.09, 0.19, 0.29, 0.39, 0.48, 0.58, 0.68, 0.79, 0.94],
        'bound':  [34.6, 30.4, 26.7, 25.4, 24.5, 23.9, 23.1, 22.0, 21.0, 20.0],
        'nlcd':   [39.4, 33.4, 28.2, 25.2, 22.4, 19.1, 17.2, 15.1, 12.2, 7.9],
        'below':  [43.7, 46.1, 47.9, 51.6, 54.0, 60.3, 63.2, 65.8, 73.7, 81.6],
        'zero':   [12.5, 9.0, 10.7, 11.6, 11.1, 13.7, 15.3, 17.2, 24.2, 36.3],
    }
    for col, vals in printed.items():
        for i, v in enumerate(vals):
            check(f"F4 decile {i+1} {col}", v, g[col].iloc[i], 0.055 if col != 'canopy' else 0.006)
    print(f"   decile sizes {g.n.min()} to {g.n.max()} (manuscript says 2,189 to 2,196)")
    check("F4 min decile size", 2189, g.n.min(), 0)
    check("F4 max decile size", 2196, g.n.max(), 0)
    if csvdir:
        t.to_csv(f"{csvdir}/table1.csv")
    return t


def table2(m, csvdir=None):
    print("\nTABLE 1  canopy coefficient under the common specification")
    xs, ys = m.xk.values, m.yk.values
    rows = []
    printed = {
        'nlcd':  dict(coef=-21.8958, r2=0.320, hc1=0.4262, c1=1.4381, c2=1.9006, c5=2.2613, t5=-9.7),
        'below': dict(coef=+0.3119, r2=0.101, hc1=0.0114, c1=0.0277, c2=0.0345, c5=0.0403, t5=+7.7),
        'zero':  dict(coef=+0.1598, r2=0.059, hc1=0.0097, c1=0.0214, c2=0.0276, c5=0.0336, t5=+4.8),
    }
    labels = {'nlcd': 'Measured impervious', 'below': 'Below the physical bound',
              'zero': 'Reports exactly zero'}
    for y in ['nlcd', 'below', 'zero']:
        X, Y, b, e, XtXi, r2 = ols(m, y)
        c = b[1]
        h = se_hc1(X, e, XtXi)
        k1 = se_conley(X, e, XtXi, xs, ys, 1.0)
        k2 = se_conley(X, e, XtXi, xs, ys, 2.0)
        k5 = se_conley(X, e, XtXi, xs, ys, 5.0)
        rows.append(dict(outcome=labels[y], coef=c, r2=r2, hc1=h,
                         conley_1km=k1, conley_2km=k2, conley_5km=k5, t_5km=c / k5))
        P = printed[y]
        check(f"T1 {y} coefficient", P['coef'], c, 0.0005)
        check(f"T1 {y} R2", P['r2'], r2, 0.0006)
        check(f"T1 {y} HC1", P['hc1'], h, 0.0001)
        check(f"T1 {y} Conley 1 km", P['c1'], k1, 0.0001)
        check(f"T1 {y} Conley 2 km", P['c2'], k2, 0.0001)
        check(f"T1 {y} Conley 5 km", P['c5'], k5, 0.0001)
        check(f"T1 {y} t at 5 km", P['t5'], c / k5, 0.06)
    t = pd.DataFrame(rows)
    print(t.round(4).to_string(index=False))
    # convergence claim made in the caption and in Section 2.4
    X, Y, b, e, XtXi, _ = ols(m, 'nlcd')
    k5 = se_conley(X, e, XtXi, xs, ys, 5.0)
    k8 = se_conley(X, e, XtXi, xs, ys, 8.0)
    drift = 100 * abs(k8 - k5) / k5
    print(f"   Conley converges: 5 km {k5:.4f} vs 8 km {k8:.4f}, drift {drift:.3f}%")
    if drift >= 0.1:
        FAIL.append(("T1 convergence claim (<0.1%)", "<0.1", round(drift, 3)))
    if csvdir:
        t.to_csv(f"{csvdir}/table2.csv", index=False)
    return t


def block_origin_sensitivity(m):
    """Section 2.4 states block SEs move 30 percent with an arbitrary origin."""
    print("\nSECTION 2.4  block-cluster grid-origin sensitivity (why block SEs are not tabulated)")
    X, Y, b, e, XtXi, _ = ols(m, 'nlcd')
    xs, ys, c = m.xk.values, m.yk.values, b[1]
    vals = [se_block(X, e, XtXi, xs, ys, 2.0, ox, oy)[0]
            for ox in (0, 0.4, 0.8, 1.2, 1.6) for oy in (0, 0.4, 0.8, 1.2, 1.6)]
    lo, hi = min(vals), max(vals)
    spread = 100 * (hi - lo) / np.mean(vals)
    print(f"   25 origins, 2 km blocks: SE {lo:.4f} to {hi:.4f}, "
          f"t {c/hi:+.1f} to {c/lo:+.1f}, spread {spread:.0f}% of the mean")
    check("2.4 block SE low", 1.64, lo, 0.01)
    check("2.4 block SE high", 2.19, hi, 0.01)
    check("2.4 t at the loose end", -10.0, c / hi, 0.1)
    check("2.4 t at the tight end", -13.4, c / lo, 0.1)


def table3(m, csvdir=None):
    print("\nTABLE 2  detection-failure rate by canopy quintile within density quartile")
    m = m.copy()
    m['dq'] = pd.qcut(m.n100, 4, labels=False)
    m['cq'] = pd.qcut(m.canopy, 5, labels=False)
    rate = m.pivot_table(index='dq', columns='cq', values='below', aggfunc='mean') * 100
    cnt = m.pivot_table(index='dq', columns='cq', values='below', aggfunc='size')
    nb = m.groupby('dq').n100.mean()
    print(rate.round(1).to_string())
    printed = [[54.9, 62.7, 69.1, 74.8, 84.5],
               [52.2, 55.4, 59.8, 63.0, 80.6],
               [43.6, 47.9, 55.2, 62.6, 74.8],
               [35.5, 33.1, 40.2, 51.8, 60.5]]
    nbp = [6.7, 12.5, 16.8, 31.0]
    for i in range(4):
        check(f"T2 density Q{i+1} mean neighbours", nbp[i], nb.iloc[i], 0.06)
        for j in range(5):
            check(f"T2 density Q{i+1} canopy Q{j+1}", printed[i][j], rate.iloc[i, j], 0.06)
    print(f"   cell counts {cnt.values.min()} to {cnt.values.max()} "
          f"(manuscript says 574 to 1,702)")
    check("T2 min cell", 574, cnt.values.min(), 0)
    check("T2 max cell", 1702, cnt.values.max(), 0)
    # the monotonicity statement in Section 3.3
    mono = [all(rate.iloc[i].values[j] <= rate.iloc[i].values[j+1] for j in range(4))
            for i in range(4)]
    print(f"   monotonic by density quartile: {mono}  "
          f"(manuscript: monotonic in the three more dispersed, not the densest)")
    if mono != [True, True, True, False]:
        FAIL.append(("3.3 monotonicity pattern", "[T,T,T,F]", str(mono)))
    if csvdir:
        rate.round(1).to_csv(f"{csvdir}/table3.csv")
    return rate


def table4(m, csvdir=None):
    print("\nTABLE 3  four products, four decision rules")
    m = m.copy()
    m['q5'] = pd.qcut(m.canopy, 5, labels=False)
    spec = [('ESA WorldCover built-up', 'wc', 54.3, 0.9, -98),
            ('NLCD percentage impervious', 'nlcd', 36.4, 10.0, -72),
            ('Dynamic World built', 'dw', 61.4, 31.2, -49),
            ('GHSL built surface', 'ghsl', 20.6, 12.2, -41)]
    rows = []
    for name, col, plo, phi, pfall in spec:
        t = m.groupby('q5')[col].mean()
        fall = 100 * (t.iloc[-1] - t.iloc[0]) / t.iloc[0]
        rows.append(dict(product=name, low=t.iloc[0], high=t.iloc[-1], fall_pct=fall))
        check(f"T3 {col} lowest quintile", plo, t.iloc[0], 0.06)
        check(f"T3 {col} highest quintile", phi, t.iloc[-1], 0.06)
        check(f"T3 {col} relative fall", pfall, fall, 0.6)
    print("   same falsifiable test applied to each product:")
    # The t-values are asserted as well as the coefficients. They were not, and
    # that gap hid a wrong number: WorldCover printed t = 75.3 where HC1 gives
    # 76.6, a value no variance estimator produced (classical 74.7, HC0 to HC3
    # all 76.6) and no covariate set reproduced. The caption states these are
    # HC1, so each row is checked against HC1 and must NOT match Conley.
    for col, lab, pr, pc, pt in [('below_wc', 'ESA WorldCover', 75.9, 0.655, 76.6),
                                 ('below', 'NLCD impervious', 58.8, 0.312, 27.4),
                                 ('below_dw', 'Dynamic World', 21.6, 0.322, 32.5),
                                 ('below_ghsl', 'GHSL built surface', 72.2, 0.096, 8.7)]:
        X, _, b, e, XtXi, _ = ols(m, col)
        check(f"T3 {lab} below bound (%)", pr, 100 * m[col].mean(), 0.06)
        check(f"T3 {lab} canopy on below bound", pc, b[1], 0.0006)
        h = se_hc1(X, e, XtXi)
        c = se_conley(X, e, XtXi, m.xk.values, m.yk.values, 5.0)
        check(f"T3 {lab} HC1 t", pt, b[1] / h, 0.06)
        assert abs(b[1] / c - pt) > 0.5, (
            f'{lab}: the Conley t also matches {pt}, so this row does not '
            'discriminate between the two estimators')
    t = pd.DataFrame(rows)
    print(t.round(1).to_string(index=False))
    q = pd.qcut(m.canopy, 5, labels=False).value_counts()
    print(f"   quintile sizes {q.min()} to {q.max()} (manuscript says 4,384 to 4,390)")
    check("T3 min quintile size", 4384, q.min(), 0)
    check("T3 max quintile size", 4390, q.max(), 0)
    if csvdir:
        t.to_csv(f"{csvdir}/table4.csv", index=False)
    return t


def table5(d, m, csvdir=None):
    print("\nTABLE 4  validation checks and sensitivity")
    rows = []

    def add(label, printed_val, computed, tol, printed_t=None, computed_t=None):
        check(label, printed_val, computed, tol)
        if printed_t is not None:
            check(label + " t", printed_t, computed_t, 0.15)
        rows.append(dict(check=label, value=computed))

    X, Y, b, e, XtXi, _ = ols(m, 'nlcd', H + ['imp_floor_px'])
    add("conditioning on the physical bound", -21.15, b[1], 0.005,
        -49.5, b[1] / se_hc1(X, e, XtXi))
    X, Y, b, e, XtXi, _ = ols(m, 'imp_floor_px')
    add("canopy on the bound itself", -7.58, b[1], 0.005,
        -23.7, b[1] / se_hc1(X, e, XtXi))
    printed_q = [0.339, 0.316, 0.346, 0.316]
    for i, (lo, hi) in enumerate([(0, .25), (.25, .5), (.5, .75), (.75, 1.)]):
        g = (m[m.ac <= m.ac.quantile(hi)] if lo == 0
             else m[(m.ac > m.ac.quantile(lo)) & (m.ac <= m.ac.quantile(hi))])
        _, _, bq, _, _, _ = ols(g, 'below')
        add(f"detection failure, acres Q{i+1}", printed_q[i], bq[1], 0.001)
    nc = d[(d.yr.notna()) & (d.yr > 2019)].copy()
    X, Y, b, e, XtXi, _ = ols(nc, 'nlcd')
    add("negative control, built after 2019", -2.45, b[1], 0.005,
        -1.4, b[1] / se_hc1(X, e, XtXi))
    print(f"   negative control n = {len(nc)} (manuscript says 589)")
    check("T4 negative control n", 589, len(nc), 0)
    _, _, b, _, _, _ = ols(m, 'nlcd', ['canopy'])
    add("covariate set, minimal", -31.44, b[1], 0.005)
    _, _, b, _, _, _ = ols(m, 'nlcd', H + ['storeys', 'garage', 'improve', 'elev', 'n250'])
    add("covariate set, maximal", -21.27, b[1], 0.03)
    _, _, b, _, _, _ = ols(m, 'nlcd')
    add("canopy threshold 2 m", -21.90, b[1], 0.005)
    _, _, b, _, _, _ = ols(m.assign(canopy=m.canopy5), 'nlcd')
    add("canopy threshold 5 m", -22.67, b[1], 0.005)
    m2 = m.assign(c2=m.canopy ** 2)
    X, Y, b, e, XtXi, _ = ols(m2, 'nlcd', ['c2', 'canopy', 'ac', 'sqft', 'slope', 'n100'])
    add("quadratic in canopy", 9.07, b[1], 0.005, 6.1, b[1] / se_hc1(X, e, XtXi))
    if csvdir:
        pd.DataFrame(rows).to_csv(f"{csvdir}/table5.csv", index=False)


def matched_pair_selection(m, csvdir=None):
    """The matched pair illustrated in Figure 1, and why it is not cherry-picked."""
    print("\nFIGURE 1  matched-pair selection")
    lo_pool = m[m.canopy <= 0.05]
    hi_pool = m[m.canopy >= 0.88]
    pairs = []
    for _, h in hi_pool.iterrows():
        if not (1400 <= h.sqft <= 2200 and 0.18 <= h.ac <= 0.40):
            continue
        if h.imp_floor_px < 20:
            continue
        c = lo_pool[(abs(lo_pool.sqft - h.sqft) < 150) & (abs(lo_pool.ac - h.ac) < 0.05) &
                    (abs(lo_pool.n100 - h.n100) < 4) &
                    (abs(lo_pool.imp_floor_px - h.imp_floor_px) < 5)]
        for _, l in c.iterrows():
            pairs.append(dict(hi_apn=h.apn, lo_apn=l.apn, hi_nlcd=h.nlcd, lo_nlcd=l.nlcd,
                              hi_can=h.canopy, lo_can=l.canopy,
                              hi_floor=h.imp_floor_px, lo_floor=l.imp_floor_px,
                              hi_lat=h.lat, hi_lon=h.lon, lo_lat=l.lat, lo_lon=l.lon))
    B = pd.DataFrame(pairs)
    med_lo = lo_pool.nlcd.median()
    med_hi = hi_pool.nlcd.median()
    # rank by TYPICALITY, not by contrast: closest to each group's median NLCD
    B['typicality'] = (B.lo_nlcd - med_lo).abs() + (B.hi_nlcd - med_hi).abs()
    B = B.sort_values('typicality')
    print(f"   candidate matched pairs: {len(B)}   (manuscript says 3,530)")
    check("F1 candidate pairs", 3530, len(B), 0)
    print(f"   group median NLCD: low canopy {med_lo:.1f}, high canopy {med_hi:.1f}"
          f"   (manuscript says 38 and 1)")
    check("F1 median NLCD, low-canopy group", 38, med_lo, 0.01)
    check("F1 median NLCD, high-canopy group", 1, med_hi, 0.01)
    chosen = B[(B.lo_apn == '040050027000') & (B.hi_apn == '045300033000')]
    print(f"   the illustrated pair is present among the most typical: "
          f"{'yes' if len(chosen) else 'NO'}")
    if not len(chosen):
        FAIL.append(("F1 illustrated pair present", "yes", "no"))
    else:
        r = chosen.iloc[0]
        print(f"     open     APN {r.lo_apn}  canopy {r.lo_can:.2f}  "
              f"bound {r.lo_floor:.1f}%  NLCD {r.lo_nlcd:.0f}%  ({r.lo_lat:.5f}, {r.lo_lon:.5f})")
        print(f"     canopied APN {r.hi_apn}  canopy {r.hi_can:.2f}  "
              f"bound {r.hi_floor:.1f}%  NLCD {r.hi_nlcd:.0f}%  ({r.hi_lat:.5f}, {r.hi_lon:.5f})")
        check("F1 open parcel bound", 20.5, r.lo_floor, 0.06)
        check("F1 canopied parcel bound", 22.7, r.hi_floor, 0.06)
        check("F1 shortfall below bound", 21.7, r.hi_floor - r.hi_nlcd, 0.06)
    if csvdir:
        B.head(25).to_csv(f"{csvdir}/matched_candidate_pairs.csv", index=False)


def footprint_identity(m):
    """The bound includes the attached garage. Section 2.2 says so; verify it."""
    print("\nSECTION 2.2  footprint identity and the garage sensitivity")
    SQFT_M2 = 0.092903
    with_g = (m.sqft / m.storeys + m.garage) * SQFT_M2
    without = (m.sqft / m.storeys) * SQFT_M2
    print(f"   max |roof_m2 - (floor/storeys + garage)| = {np.abs(m.roof_m2 - with_g).max():.6f} m2")
    print(f"   max |roof_m2 - (floor/storeys)|          = {np.abs(m.roof_m2 - without).max():.1f} m2")
    if np.abs(m.roof_m2 - with_g).max() > 0.01:
        FAIL.append(("2.2 footprint identity", "floor/storeys+garage", "does not reproduce roof_m2"))
    check("2.2 parcels with a garage (%)", 82, 100 * (m.garage > 0).mean(), 0.6)
    check("2.2 mean garage (sq ft)", 531, m[m.garage > 0].garage.mean(), 1.0)
    # floorA and belowA in the released data ARE the garage-excluded bound and its
    # breach indicator. They sum roofs over EVERY parcel assigned to the cell,
    # including the post-2019 and undated ones; recomputing over the analysis
    # sample alone gives a different and wrong answer.
    check("2.2 mean bound with garages", 25.1, m.imp_floor_px.mean(), 0.06)
    check("2.2 mean bound without garages (floorA)", 19.2, m.floorA.mean(), 0.06)
    check("2.2 breach rate with garages", 58.8, 100 * m.below.mean(), 0.06)
    check("2.2 breach rate without garages (belowA)", 49.8, 100 * m.belowA.mean(), 0.06)
    X, Y, b, e, XtXi, _ = ols(m, "belowA")
    check("T4 bound excluding garages", 0.3236, b[1], 0.0005)
    check("T4 bound excluding garages, t", 27.7, b[1] / se_hc1(X, e, XtXi), 0.05)


def equations(d, m):
    """Sections 2.2 and 2.4: the four display equations must reproduce the released
    columns exactly, or the printed method does not describe the code that ran."""
    print("\nEQUATIONS 1-4  the printed method against the released data")
    K, A = 0.092903, 900.0
    # (1) a_i = ( F_i / s_i + g_i ) x kappa
    a_i = (d.sqft / d.storeys + d.garage) * K
    e1 = (a_i - d.roof_m2).abs().max()
    print(f"   {'ok ' if e1 < 1e-3 else 'FAIL'}  Eq 1 footprint identity              "
          f"max |a_i - roof_m2| = {e1:.2e} m2")
    if e1 >= 1e-3:
        FAIL.append(("Eq 1 footprint identity", 0, e1))
    # (2) B_c = min( 100 * sum_i a_i / A , 100 )
    B = (100 * d.groupby('px').roof_m2.sum() / A).clip(upper=100)
    chk = d[['px', 'imp_floor_px']].drop_duplicates('px').set_index('px').join(B.rename('B'))
    e2 = (chk.B - chk.imp_floor_px).abs().max()
    print(f"   {'ok ' if e2 < 1e-3 else 'FAIL'}  Eq 2 cell bound                      "
          f"max |B_c - imp_floor_px| = {e2:.2e} pts")
    if e2 >= 1e-3:
        FAIL.append(("Eq 2 cell bound", 0, e2))
    assert B.max() <= 100 + 1e-9, 'Eq 2 produced a bound above 100 per cent'
    # (3) D_c = 1[ P_c < B_c ]
    D = (m.nlcd < m.imp_floor_px)
    assert bool((D == m.below).all()), 'Eq 3 does not match the released breach indicator'
    check("Eq 3 breach rate PER CELL (stated in 2.2)", 56.9,
          100 * m.groupby('px').below.first().mean(), 0.05)
    check("Eq 3 breach rate", 58.8, 100 * D.mean(), 0.06)
    # (4) canopy on the unit interval, so beta_1 is the change across the full range
    assert m.canopy.min() >= 0 and m.canopy.max() <= 1, 'Eq 4: canopy is not on [0, 1]'
    print(f"   ok   Eq 4 canopy spans {m.canopy.min():.2f} to {m.canopy.max():.2f}, "
          f"so the coefficient is the full-range change")


def wealth_independence(m):
    """Section 2.1: canopy must not be a wealth proxy. Both statistics are computed on
    the same sub-sample, the analysed parcels carrying a recorded improvement value,
    because parcels with no recorded value are missing data rather than zero-value."""
    print("\nSECTION 2.1  canopy against assessed improvement value")
    x = m[m.improve > 0]
    check("2.1 parcels with a recorded improvement value", 21852, len(x), 0)
    check("2.1 corr(canopy, improvement value)", -0.054, x.canopy.corr(x.improve), 0.0006)
    q = pd.qcut(x.improve, 5, labels=False)
    mc = x.groupby(q).canopy.mean()
    check("2.1 canopy, lowest value quintile", 0.448, mc.iloc[0], 0.0006)
    check("2.1 canopy, highest value quintile", 0.427, mc.iloc[-1], 0.0006)


def truncation(m):
    """Section 2.2: the bound is truncated at 100 per cent of cell area. Verify how
    far truncation reaches, that it falls in the open rather than under canopy, and
    that dropping the affected cells does not carry the result."""
    print("\nSECTION 2.2  truncation of the bound at 100 per cent of cell area")
    hit = m.imp_floor_raw > 100
    check("2.2 parcels where truncation binds", 163, hit.sum(), 0)
    check("2.2 cells where truncation binds", 33, m.loc[hit, 'px'].nunique(), 0)
    check("2.2 share of sample truncated (%)", 0.74, 100 * hit.mean(), 0.006)
    check("2.2 mean canopy where truncation binds", 0.05, m.loc[hit, 'canopy'].mean(), 0.006)
    assert m.imp_floor_px.max() <= 100 + 1e-9, 'truncation did not apply to the bound'
    assert m.floorA.max() <= 100 + 1e-9, 'truncation did not apply to the garage-excluded bound'
    print(f"   ok   max reported bound {m.imp_floor_px.max():.1f} per cent "
          f"(raw maximum was {m.imp_floor_raw.max():.1f})")
    _, _, b, _, _, _ = ols(m[m.imp_floor_raw <= 100], 'nlcd')
    check("T4 dropping truncated cells", -21.83, b[1], 0.006)


def straddle(m):
    """Section 2.2 and 3.6: footprints are charged by parcel centroid, so a roof near a
    cell edge is charged in full to the centroid cell.

    Edge distances come from parcel_edge_exact.csv, computed from full-precision assessor
    centroids. They are NOT recomputed from the lon/lat in the released row-level file:
    those are rounded to four decimal places, a median position error of 3.9 m against a
    median edge distance of 4.4 m, which is enough to misclassify roughly one parcel in
    five. The distributional figures survive that rounding; the per-parcel classification
    does not."""
    print("\nSECTION 2.2 / 3.6  centroid assignment and the straddle-free subset")
    import os
    if not os.path.exists('parcel_edge_exact.csv'):
        SKIPPED.append('parcel_edge_exact.csv: the straddle and centroid-assignment checks')
        print("   (parcel_edge_exact.csv absent; skipping the straddle checks)")
        return
    e = pd.read_csv('parcel_edge_exact.csv', dtype={'apn': str})
    j = m.merge(e[['apn', 'dedge', 'i', 'j']], on='apn', how='inner')
    check("2.2 parcels matched to exact centroids", len(m), len(j), 0)
    pxi = j.px.str.split('_', expand=True).astype(int)
    agree = ((pxi[0] == j.i) & (pxi[1] == j.j)).mean()
    assert agree > 0.999, f'exact centroids do not reproduce px ({agree:.4f})'
    print(f"   ok   exact centroids reproduce the released px for {100*agree:.2f} per cent of parcels")
    side = np.sqrt(j.roof_m2)
    inside = j.dedge >= side / 2
    check("2.2 median roof side (m)", 12.5, side.median(), 0.06)
    check("2.2 median centroid-to-edge distance (m)", 4.4, j.dedge.median(), 0.06)
    check("2.2 roof provably inside its cell (%)", 35.2, 100 * inside.mean(), 0.06)
    check("3.6 straddle-free subset size", 7721, inside.sum(), 0)
    s = j[inside].reset_index(drop=True)
    _, _, b, e2, XtXi, _ = ols(s, 'nlcd')
    se = se_conley(X_of(s), e2, XtXi, s.xk.values, s.yk.values, 5.0)
    check("T4 straddle-free, canopy on NLCD", -22.94, b[1], 0.006)
    check("3.6 straddle-free Conley t", -10.3, b[1] / se, 0.06)
    _, _, b2, e3, Xi2, _ = ols(s, 'below')
    se2 = se_conley(X_of(s), e3, Xi2, s.xk.values, s.yk.values, 5.0)
    check("3.6 straddle-free, canopy on breach", 0.309, b2[1], 0.0006)
    check("3.6 straddle-free breach rate (%)", 53.1, 100 * s.below.mean(), 0.06)

    # The bound's cell and the NLCD pixel must be the same cell, or the
    # shared-denominator argument fails. Testing it directly: parcels that share
    # a px must report the same NLCD value. They do when the centroid sits
    # safely inside its cell, and increasingly do not as it approaches an edge,
    # which is the centroid-precision effect Section 2.2 already quantifies and
    # not a grid offset. A systematic misalignment would disagree just as often
    # deep inside a cell as at its boundary.
    mm = j.groupby('px').filter(lambda g: len(g) > 1)
    if len(mm):
        deep = mm[mm.dedge > 11]
        edge = mm[mm.dedge < 2]
        if len(deep) > 100 and len(edge) > 100:
            a_deep = 100 * (deep.groupby('px').nlcd.transform('nunique') == 1).mean()
            a_edge = 100 * (edge.groupby('px').nlcd.transform('nunique') == 1).mean()
            assert a_deep > 95, (
                'parcels sharing a cell disagree on NLCD even well inside it '
                '(%.1f per cent agreement): the bound cell and the NLCD pixel '
                'are not the same grid' % a_deep)
            assert a_deep > a_edge, (
                'NLCD agreement within a cell should improve away from the cell '
                'edge; got %.1f per cent deep against %.1f at the edge'
                % (a_deep, a_edge))
            print("   ok   the bound cell and the NLCD pixel are the same grid "
                  "(%.1f per cent agreement well inside a cell, %.1f at the edge)"
                  % (a_deep, a_edge))
    dec = pd.qcut(s.canopy, 10, labels=False)
    check("3.6 straddle-free lowest-decile breach (%)", 39.1,
          100 * s.groupby(dec).below.mean().iloc[0], 0.06)


def X_of(df, xs=H):
    return np.column_stack([np.ones(len(df))] + [df[v].astype(float).values for v in xs])


def nightlights(m):
    """Section 3.5: radiance and elevation must be reported separately, because elevation
    predicts conifer cover in a foothill county and would otherwise carry the attenuation."""
    print("\nSECTION 3.5  nighttime lights, separated from elevation")
    def coef(xs):
        X = X_of(m, xs)
        Y = m.nlcd.astype(float).values
        Xi = np.linalg.inv(X.T @ X); b = Xi @ (X.T @ Y); e = Y - X @ b
        return b[1], se_conley(X, e, Xi, m.xk.values, m.yk.values, 5.0)
    check("3.5 corr(canopy, VIIRS)", -0.298, m.canopy.corr(m.viirs), 0.0006)
    v, _ = coef(H + ['viirs']);            check("3.5 canopy, + VIIRS alone", -18.71, v, 0.006)
    e_, _ = coef(H + ['elev']);            check("3.5 canopy, + elevation alone", -20.60, e_, 0.006)
    b_, _ = coef(H + ['viirs', 'dmsp']);   check("3.5 canopy, + both light layers", -18.49, b_, 0.006)
    a, sa = coef(H + ['viirs', 'dmsp', 'elev'])
    check("3.5 canopy, + lights and elevation", -18.13, a, 0.006)
    check("3.5 Conley t on that specification", -13.2, a / sa, 0.06)
    dec = pd.qcut(m.canopy, 10, labels=False)
    r = m.groupby(dec).viirs.mean()
    check("3.5 VIIRS, lowest canopy decile", 5.48, r.iloc[0], 0.006)
    check("3.5 VIIRS, highest canopy decile", 1.19, r.iloc[-1], 0.006)


def functional_form(m):
    """Section 2.4: the linear probability model is reported, so state how far fitted
    values leave the unit interval and show a logit gives the same answer."""
    print("\nSECTION 2.4  linear probability model against logit")
    try:
        import statsmodels.api as sm
    except ImportError:
        OPTIONAL_MISSING.append('statsmodels')
        SKIPPED.append('the logit comparison (statsmodels absent)')
        print("   (statsmodels absent; skipping the logit comparison)")
        return
    X = sm.add_constant(m[H].astype(float))
    for yv, pr_out, pr_ame in [('below', 0.07, 0.305), ('zero', 5.0, 0.166)]:
        Y = m[yv].astype(float)
        o = sm.OLS(Y, X).fit()
        f = o.fittedvalues
        check(f"2.4 {yv}: fitted outside [0,1] (%)", pr_out, 100 * ((f < 0) | (f > 1)).mean(), 0.06)
        lg = sm.Logit(Y, X).fit(disp=0)
        p_ = lg.predict(X)
        check(f"2.4 {yv}: logit average marginal effect", pr_ame,
              (lg.params['canopy'] * p_ * (1 - p_)).mean(), 0.0006)


def covariate_ladder(m):
    """Section 3.6: the covariate ladder, and the share of the movement parcel area
    accounts for. Stated as a share because a 32 per cent swing is not insensitivity."""
    print("\nSECTION 3.6  covariate ladder")
    def c(xs):
        X = np.column_stack([np.ones(len(m))] + [m[v].astype(float).values for v in xs])
        Y = m.nlcd.astype(float).values
        return (np.linalg.inv(X.T @ X) @ (X.T @ Y))[1]
    alone, acres, full = c(['canopy']), c(['canopy', 'ac']), c(H)
    check("3.6 canopy alone", -31.44, alone, 0.006)
    check("3.6 reported specification", -21.90, full, 0.006)
    check("3.6 parcel area share of the movement (%)", 72,
          100 * (acres - alone) / (full - alone), 0.6)


def epochs(d):
    """Section 2.3: the analysis sample must predate every product epoch, and the negative
    control is NLCD-only because 2020-2021 construction is visible to the later products."""
    print("\nSECTION 2.3  product epochs against the sample")
    an = d[(d.yr.notna()) & (d.yr <= 2019)]
    nc = d[(d.yr.notna()) & (d.yr > 2019)]
    check("2.3 analysis sample latest year built", 2019, an.yr.max(), 0)
    check("2.3 negative control size", 589, len(nc), 0)
    check("2.3 control parcels built 2020 or 2021", 242,
          ((nc.yr >= 2020) & (nc.yr <= 2021)).sum(), 0)


def footprint_validation(d):
    """Section 3.6: the reference validated against Microsoft Building Footprints, an
    independently derived product. Read on single-parcel cells, where the recorded roof
    and the detected footprint describe the same structure, and on the MEDIAN ratio: a
    ratio of means is dragged by multi-parcel cells and by a left tail."""
    import os
    if not os.path.exists('ms_footprint_validation.csv'):
        print("\n   (ms_footprint_validation.csv absent; skipping)")
        return
    print("\nSECTION 3.6  the reference against independent building footprints")
    v = pd.read_csv('ms_footprint_validation.csv')
    npar = d.groupby('px').size().rename('npar').reset_index()
    j = v.merge(npar, on='px', how='left')
    check("3.6 cells sampled", 700, len(v), 0)
    check("3.6 cells per canopy decile", 70, v.groupby('dec').size().min(), 0)
    one = j[j.npar == 1]
    check("3.6 single-parcel cells", 569, len(one), 0)
    lo, hi = one[one.dec <= 1], one[one.dec >= 8]
    r_lo, r_hi = lo.ms_m2 / lo.roof, hi.ms_m2 / hi.roof
    check("3.6 open: median footprint-to-roof ratio", 1.01, r_lo.median(), 0.006)
    check("3.6 open: cells where the product exceeds the record (%)", 50.5,
          100 * (lo.ms_m2 > lo.roof).mean(), 0.06)
    check("3.6 open: cells with no building (%)", 2.7, 100 * (lo.ms_m2 == 0).mean(), 0.06)
    check("3.6 canopied: median footprint-to-roof ratio", 0.54, r_hi.median(), 0.006)
    check("3.6 canopied: cells where the product exceeds (%)", 24.8,
          100 * (hi.ms_m2 > hi.roof).mean(), 0.06)
    check("3.6 canopied: cells with no building (%)", 30.6, 100 * (hi.ms_m2 == 0).mean(), 0.06)
    try:
        from scipy import stats as _sc
        pval = _sc.mannwhitneyu(r_lo, r_hi, alternative='greater').pvalue
        assert pval < 1e-7, f'open-versus-canopied ratio difference is not significant (p={pval:.2e})'
        print(f"   ok   Mann-Whitney open > canopied: p = {pval:.2e} (manuscript says below 1e-7)")
    except ImportError:
        OPTIONAL_MISSING.append('SciPy')
        SKIPPED.append('the Mann-Whitney check (SciPy absent)')
        print("   (scipy absent; skipping the Mann-Whitney check)")


def robustness_ladder(m):
    """Section 3.6: no subgroup of the frame produces the result on its own, and every
    restriction that removes the least typical parcels strengthens it."""
    print("\nSECTION 3.6  frame-restriction ladder")
    k = m.groupby('px').apn.transform('size')
    for tag, s, pr in [("cells holding one parcel only", m[k == 1], -19.65),
                       ("dominant use code only", m[m.use == 100], -19.67),
                       ("lots of at least 0.05 acres", m[m.ac >= 0.05], -20.98)]:
        _, _, b, _, _, _ = ols(s, 'nlcd')
        check(f"T4 {tag}", pr, b[1], 0.006)
        _, _, bb, _, _, _ = ols(s, 'below')
        assert bb[1] > 0.312, f'{tag}: breach coefficient should strengthen, got {bb[1]:.4f}'
    print("   ok   every restriction raises the detection-failure coefficient above +0.312")


def frame_and_porch(d, m):
    """Section 2.1 and 2.2, against the county's own TotalUnits, Bedrooms, porch and
    guest-house fields (parcel_extras.csv). The frame is residential because every
    parcel carries a recorded dwelling, not because of its use code; and the roofed
    area the bound omits is what makes the reported specification conservative.
    The porch-inclusive bound is built on the FULL frame, because a cell's bound sums
    every parcel assigned to it, not only the analysed ones."""
    import os
    if not os.path.exists('parcel_extras.csv'):
        SKIPPED.append('parcel_extras.csv: the frame-composition and porch checks')
        print("\n   (parcel_extras.csv absent; skipping frame and porch checks)")
        return
    SQFT2M2 = 0.092903
    e = pd.read_csv('parcel_extras.csv', dtype={'apn': str})

    print("\nSECTION 2.1  the frame carries a recorded dwelling")
    check("2.1 frame size in the extras pull", 24088, len(e), 0)
    check("2.1 parcels with >= 1 dwelling unit", 24021, (e.units >= 1).sum(), 0)
    check("2.1 parcels recording zero units", 0, (e.units == 0).sum(), 0)
    check("2.1 bedroom or unit recorded (%)", 99.8,
          100 * ((e.units >= 1) | (e.beds >= 1)).mean(), 0.06)
    # the extras pull must be the same frame, row for row, as the analysis pull
    assert (d.garage.values == e.set_index('apn').loc[d.apn, 'veh'].fillna(0).values).all(), \
        'extras pull does not match the analysis pull on recorded garage area'
    print("   ok   extras pull matches the analysis pull row for row on garage area")

    print("\nSECTION 2.2  recorded roofed area the bound omits")
    j = m.merge(e[['apn', 'porch', 'gh']], on='apn', how='left')
    check("2.2 sample size after merging extras", len(m), len(j), 0)
    pg = j.porch.fillna(0)
    check("2.2 parcels with recorded porch (%)", 55.4, 100 * (pg > 0).mean(), 0.06)
    check("2.2 mean porch where present (sq ft)", 994, j.loc[pg > 0, 'porch'].mean(), 0.6)
    check("2.2 parcels with a guest house", 47, (j.gh.fillna(0) > 0).sum(), 0)
    om = ((pg + j.gh.fillna(0)) * SQFT2M2).sum()
    check("2.2 omitted roofed area (ha)", 112.5, om / 1e4, 0.06)
    check("2.2 omitted as % of counted roof", 32.0, 100 * om / j.roof_m2.sum(), 0.06)

    f = d.merge(e[['apn', 'porch', 'gh']], on='apn', how='left')
    f['extra_m2'] = (f.porch.fillna(0) + f.gh.fillna(0)) * SQFT2M2
    cell = f.groupby('px').agg(roof=('roof_m2', 'sum'), extra=('extra_m2', 'sum'))
    cell['b_all'] = (100 * (cell.roof + cell.extra) / 900).clip(upper=100)
    f = f.merge(cell[['b_all']], left_on='px', right_index=True)
    a = f[(f.yr.notna()) & (f.yr <= 2019)].copy()
    a['bel_all'] = (a.nlcd < a.b_all).astype(float)
    check("2.2 mean bound incl. porch", 32.3, a.b_all.mean(), 0.06)
    check("2.2 breach rate incl. porch (%)", 68.2, 100 * a.bel_all.mean(), 0.06)
    _, _, b, _, _, _ = ols(a, 'bel_all')
    check("T4 bound including porch", 0.269, b[1], 0.0006)

    # The two printed figures do not compose by multiplication, and a reviewer
    # will try: 25.1 x 1.320 = 33.2, not 32.3. The project record proposed saying
    # truncation absorbs the difference. Measured, that is only a third of it, so
    # writing it would have introduced a new error. The real decomposition, which
    # Section 2.2 now states and this asserts: the 32.0 percent is a ratio of
    # total roofed area in the ANALYSIS SAMPLE, while the bound is summed per
    # cell over the WHOLE FRAME, where the omitted share is 30.2 percent; the
    # ceiling then binds on 108 cells and costs a further 0.3.
    full_share = 100 * f.extra_m2.sum() / f.roof_m2.sum()
    check("2.2 omitted share on the full frame (%)", 30.2, full_share, 0.06)
    check("2.2 naive scale-up of the bound", 33.2,
          a.b_tr.mean() * (1 + 32.02 / 100) if 'b_tr' in a else
          m.imp_floor_px.mean() * 1.3202, 0.06)
    raw_all = (100 * (cell.roof + cell.extra) / 900)
    f2 = f.merge(raw_all.rename('raw_all'), left_on='px', right_index=True)
    a2 = f2[(f2.yr.notna()) & (f2.yr <= 2019)]
    check("2.2 porch bound before the ceiling", 32.60, a2.raw_all.mean(), 0.02)
    check("2.2 cells the ceiling binds on, incl. porch", 108, int((raw_all > 100).sum()), 0)
    gap_ceiling = a2.raw_all.mean() - a.b_all.mean()
    assert 0.25 < gap_ceiling < 0.40, (
        'the ceiling now explains %.2f of the gap; Section 2.2 says it is part of '
        'the explanation, not all of it, so re-check the wording' % gap_ceiling)
    print("   ok   the ceiling explains %.2f of the 0.9 point gap, the base the rest"
          % gap_ceiling)

    # Direction of the garage sensitivity. 0.3236 is the GARAGE-EXCLUDED
    # coefficient and 0.3119 the reported garage-inclusive one. The sentence in
    # Section 2.2 once read "lowers the estimated effect, to plus 0.3236 against
    # the plus 0.3119 reported here", which states the fall and then names the
    # higher number as its destination.
    src = open('build_manuscript.js', encoding='utf-8').read()
    if 'from the plus 0.3236 that excluding them gives to the plus 0.3119 reported here' in src:
        print("   ok   Section 2.2 names the garage sensitivity in the right direction")
    else:
        FAIL.append(('2.2 garage sensitivity direction', 'wording changed',
                     'must read from 0.3236 (excluded) to 0.3119 (reported)'))
        print("   FAIL  Section 2.2 no longer states the garage direction unambiguously")


def study_area(m, d):
    """Section 2.1 and 3.1: frame composition and land-cover characterisation.
    County figures are US Census Bureau QuickFacts V2025 and 2020-2024 ACS."""
    print("\nSECTION 2.1 / 3.1  frame composition and land cover")
    COUNTY_HU, PPH = 55074, 2.36
    check("2.1 sample as % of county housing units", 39.8, 100 * len(m) / COUNTY_HU, 0.06)
    check("2.1 dominant use code share (%)", 86.8, 100 * m.use.value_counts().iloc[0] / len(m), 0.06)
    check("2.1 single-storey (%)", 50.5, 100 * (m.storeys == 1).mean(), 0.06)
    check("2.1 two-storey (%)", 46.3, 100 * (m.storeys == 2).mean(), 0.06)
    check("2.1 median floor area (sq ft)", 1652, m.sqft.median(), 0.5)
    check("2.1 median lot (ac)", 0.30, m.ac.median(), 0.005)
    check("2.1 median year built", 1984, m.yr.median(), 0.5)
    check("2.1 with attached garage (%)", 81.8, 100 * (m.garage > 0).mean(), 0.06)
    check("2.1 distinct 30 m cells", 18102, m.px.nunique(), 0)
    check("2.1 cells holding exactly one structure (%)", 66.7,
          100 * (m.n_bldg_px == 1).mean(), 0.06)
    dev = m.lc.isin([21, 22, 23, 24])
    check("3.1 cells given a developed class (%)", 83.0, 100 * dev.mean(), 0.06)
    check("3.1 classed evergreen forest (%)", 14.0, 100 * (m.lc == 42).mean(), 0.06)
    check("3.1 not classed developed (%)", 17.0, 100 * (~dev).mean(), 0.06)
    nd = m.assign(nd=~dev, dec=pd.qcut(m.canopy, 10, labels=False)).groupby("dec").nd.mean() * 100
    check("3.1 not developed, lowest canopy decile (%)", 13.4, nd.iloc[0], 0.06)
    check("3.1 not developed, highest canopy decile (%)", 34.5, nd.iloc[-1], 0.06)



def prose_lint(path='build_manuscript.js'):
    """Two prose defects a numeric harness cannot see.

    (a) an enumeration that promises N items and lists a different number;
    (b) the same sentence emitted twice.
    Both were live in the manuscript when this check was written.
    """
    import codecs
    import re as _re
    W = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}
    src = open(path, encoding='utf-8').read()
    ps = [codecs.decode(m.group(1), 'unicode_escape') if '\\u' in m.group(1) else m.group(1)
          for m in _re.finditer(r"body\.push\(p\('((?:[^'\\]|\\.)*)'", src)]
    head = _re.compile(r'\b(Two|Three|Four|Five|Six)\s+'
                       r'(?:things|mechanisms|reasons|checks|restrictions|sources|factors|features)'
                       r'\b[^:.]{0,60}:')
    n_enum = 0
    for x in ps:
        for m in head.finditer(x):
            n_enum += 1
            promised = W[m.group(1).lower()]
            tail = x[m.end():]
            cut = _re.search(r'\.\s+(?=[A-Z(])', tail)
            tail = tail[:cut.start()] if cut else tail
            sep = ';' if ';' in tail else ','
            listed = len([t for t in tail.split(sep) if t.strip()])
            if listed != promised:
                FAIL.append(('prose lint: enumeration "%s"' % m.group(0), promised, listed))
            else:
                print('   ok   enumeration "%s" lists %d items' % (m.group(0), promised))
    # "Six checks ..." followed by First, Second, ... ordinals, which may run
    # across several paragraphs. The colon-form check cannot see this shape;
    # the manuscript said "Five checks" and then enumerated six.
    ORD = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth']
    NUM = dict(W, seven=7, eight=8)
    blocks = [(m.group(1), m.group(2)) for m in _re.finditer(
        r"body\.push\((h1|h2|p|caption)\('((?:[^'\\\\]|\\\\.)*)'", src)]
    sections, cur = [], []
    for kind, txt in blocks:
        if kind in ('h1', 'h2'):
            if cur:
                sections.append(' '.join(cur))
            cur = []
        elif kind == 'p':
            cur.append(txt)
    if cur:
        sections.append(' '.join(cur))
    for sec in sections:
        m0 = _re.search(r'\b(Two|Three|Four|Five|Six|Seven|Eight)\s+'
                        r'(checks|tests|restrictions|steps)\b', sec)
        if not m0:
            continue
        promised = NUM.get(m0.group(1).lower())
        found = [o for o in ORD if _re.search(r'\b%s,' % o.capitalize(), sec)]
        if not found:
            continue
        if len(found) != promised:
            FAIL.append(('prose lint: "%s %s" enumerates %d'
                         % (m0.group(1), m0.group(2), len(found)),
                         promised, len(found)))
        else:
            print('   ok   "%s %s" enumerates exactly %d'
                  % (m0.group(1), m0.group(2), len(found)))

    seen = {}
    for x in ps:
        for sent in _re.split(r'(?<=[.?!])\s+(?=[A-Z(])', x):
            sent = sent.strip()
            if len(sent.split()) >= 8:
                seen[sent] = seen.get(sent, 0) + 1
    # a repeated CLAUSE inside one paragraph, which a whole-sentence check
    # misses: "parcel area correlates with canopy at plus 0.283" appeared twice
    # in one paragraph of Section 2.1, in two different sentences.
    clause = []
    for x in ps:
        w = x.split()
        grams = {}
        for i in range(len(w) - 7):
            g = ' '.join(w[i:i + 8]).lower()
            grams[g] = grams.get(g, 0) + 1
        for g, c in grams.items():
            if c > 1:
                clause.append(g)
    if clause:
        FAIL.append(('prose lint: clause repeated inside one paragraph',
                     'none', clause[0][:70]))
    else:
        print('   ok   no 8-word clause repeated inside a paragraph')
    # Rates in this paper are parcel-weighted. Any "of cells" phrasing for a
    # rate is therefore wrong unless it sits in the footprint-validation
    # paragraph, which really was computed on 700 sampled cells.
    unit = []
    caps = [m.group(2) for m in _re.finditer(
        r"body\.push\((caption)\('((?:[^'\\\\]|\\\\.)*)'", src)]
    for x in ps + caps:
        if 'footprint' in x.lower():
            continue
        for mu in _re.finditer(r'(?:percent(?:age)? of cells|share of cells|'
                               r'of cells where|of cells that|cells breach)', x):
            unit.append(' '.join(x[max(0, mu.start() - 50):mu.start() + 60].split()))
    if unit:
        FAIL.append(('prose lint: rate attributed to cells, not parcels',
                     'parcels', unit[0][:70]))
    else:
        print('   ok   no rate attributed to cells outside the footprint check')
    dups = [t for t, c in seen.items() if c > 1]
    if dups:
        FAIL.append(('prose lint: sentence emitted twice', 'none', dups[0][:70]))
    else:
        print('   ok   no sentence appears twice (%d distinct sentences)' % len(seen))
    enders = [x for x in ps if x and x.rstrip()[-1] not in '.?!)]’"']
    if enders:
        FAIL.append(('prose lint: paragraph lacks terminal punctuation', 'none',
                     enders[0][-60:]))
    else:
        print('   ok   every body paragraph ends in terminal punctuation (%d)' % len(ps))
    # a content word repeated inside a short window of ONE sentence:
    # catches "Multi-Resolution Land Characteristics Consortium (MRLC) Consortium"
    STOP = {'the','a','an','of','in','on','at','to','and','or','is','are','it','that',
            'this','as','by','for','from','with','not','than','which','so','its','be',
            'per','points','percent','cent','cell','cells','canopy','bound','product',
            'products','impervious','surface','area','data','one','two','more','less',
            'minus','plus','against','decile','parcels','parcel','recorded','measured',
            'code','cover','rate','here','both','where','each','also','only','into',
            'four','three','five','six','first','second','third','same','full','half'}
    rep = []
    for x in ps:
        for sent in _re.split(r'(?<=[.?!])\s+(?=[A-Z(])', x):
            toks = sent.split()
            w = [t.strip('.,;:()\u201c\u201d\u2019').lower() for t in toks]
            for a in range(len(w) - 1):
                for b in range(a + 1, min(a + 4, len(w))):
                    if w[a] and w[a] == w[b] and w[a] not in STOP and len(w[a]) > 3:
                        rep.append(' '.join(toks[max(0, a - 2):b + 3]))
    if rep:
        FAIL.append(('prose lint: word repeated within one sentence', 'none', rep[0][:70]))
    else:
        print('   ok   no content word repeated inside a 4-word window of a sentence')
    if n_enum < 5:
        FAIL.append(('prose lint: enumerations reached', '>=5', n_enum))


def reference_lint(path='build_manuscript.js'):
    """The reference list must be alphabetical, and every in-text citation must
    lead with a token a reader can find in that list.

    Both failed when this check was written: "US Environmental Protection
    Agency" sat before "US Census Bureau", and "(USDA SCS 1986)" pointed at an
    entry filed under "United States Department of Agriculture".
    """
    import re as _re
    src = open(path, encoding='utf-8').read()
    i = src.find('const refs = [')
    block = src[i:src.find('];', i)]
    refs = [m.group(1) for m in
            _re.finditer(r"^\s*'((?:[^'\\]|\\.)*)',?\s*$", block, _re.M)]
    if len(refs) < 20:
        FAIL.append(('reference lint: entries parsed', '>=20', len(refs)))
        return

    def key(r):
        k = _re.sub(r'\s*\(.*', '', r.split('.')[0])
        return [w for w in _re.sub(r'[^A-Za-z ]', '', k).lower().split()]

    keys = [key(r) for r in refs]
    if keys != sorted(keys):
        bad = next(a for a, b in zip(keys, sorted(keys)) if a != b)
        FAIL.append(('reference lint: list is alphabetical', 'sorted', ' '.join(bad)))
    else:
        print('   ok   %d reference entries, alphabetical' % len(refs))

    leads = {' '.join(k) for k in keys}
    body = ' '.join(m.group(2) for m in _re.finditer(
        r"body\.push\((p|caption|h1|h2)\('((?:[^'\\\\]|\\\\.)*)'", src))
    # only well-formed parenthetical citations: "(Lead 1999)", "(A 2015; B 2006)"
    unfindable, n_cite = [], 0
    for grp in _re.finditer(r'\(([^()]{1,200})\)', body):
        for part in grp.group(1).split(';'):
            m = _re.match(r"\s*([A-Z][A-Za-z.\u2019'\- ]*?)"
                          r"(?:\s+et\s+al\.)?\s+((?:19|20)\d{2}[a-z]?)\s*$", part)
            if not m:
                continue
            n_cite += 1
            low = _re.sub(r'[^a-z ]', '', m.group(1).lower()).strip()
            if not low:
                continue
            if not any(l.startswith(low) or low.startswith(l.split()[0]) for l in leads):
                unfindable.append(m.group(1).strip())
    if unfindable:
        FAIL.append(('reference lint: cited name not a list entry',
                     'findable', sorted(set(unfindable))[0]))
    else:
        print('   ok   %d parenthetical citations all resolve to a list entry' % n_cite)


def heading_lint(path='build_manuscript.js'):
    """Numbered sections must run 1..N, and every subsection under section N
    must be numbered N.1, N.2, ... in order with no gap or repeat.
    Also: every "Section x.y" callout in the prose must name a heading that exists.
    """
    import re as _re
    src = open(path, encoding='utf-8').read()
    heads = [(m.group(1), m.group(2)) for m in
             _re.finditer(r"body\.push\((h1|h2)\('([^']*)'", src)]
    top, subs, cur = [], {}, None
    for lvl, t in heads:
        m1 = _re.match(r'(\d+)\.\s', t)
        m2 = _re.match(r'(\d+)\.(\d+)\.\s', t)
        if lvl == 'h1' and m1:
            cur = int(m1.group(1)); top.append(cur); subs[cur] = []
        elif lvl == 'h2' and m2:
            subs.setdefault(int(m2.group(1)), []).append(int(m2.group(2)))
    if top != list(range(1, len(top) + 1)):
        FAIL.append(('heading lint: top-level numbering', list(range(1, len(top) + 1)), top))
    else:
        print('   ok   %d numbered sections run 1..%d' % (len(top), len(top)))
    bad = []
    for sec, kids in subs.items():
        if kids and kids != list(range(1, len(kids) + 1)):
            bad.append((sec, kids))
        if sec not in top:
            bad.append((sec, 'no parent'))
    if bad:
        FAIL.append(('heading lint: subsection numbering', 'sequential', str(bad[0])))
    else:
        print('   ok   subsections sequential in every section (%s)'
              % ', '.join('%d:%d' % (k, len(v)) for k, v in sorted(subs.items()) if v))
    named = {t.split('.')[0] + '.' + t.split('.')[1] for _, t in heads
             if _re.match(r'\d+\.\d+\.\s', t)}
    body = ' '.join(m.group(2) for m in _re.finditer(
        r"body\.push\((p|caption|h1|h2)\('((?:[^'\\]|\\.)*)'", src))
    dangling = sorted({r for r in _re.findall(r'Section (\d+\.\d+)', body)
                       if r not in named})
    if dangling:
        FAIL.append(('heading lint: Section callout has no heading', 'exists', dangling[0]))
    else:
        print('   ok   every "Section x.y" callout names a real heading (%d refs)'
              % len(_re.findall(r'Section \d+\.\d+', body)))


def callout_lint(path='build_manuscript.js'):
    """Tables, figures and equations must be FIRST cited in the running text in
    numerical order. Captions are excluded: a caption may legitimately refer
    forward (Figure 1's caption points at the two parcels of Figure 3).
    """
    import re as _re
    src = open(path, encoding='utf-8').read()
    paras = [m.group(2) for m in _re.finditer(
        r"body\.push\((p)\('((?:[^'\\]|\\.)*)'", src)]
    text = ' '.join(paras)
    for kind, lo in (('Table', 1), ('Figure', 1), ('Equation', 1)):
        order, seen = [], set()
        for m in _re.finditer(kind + r's?\s+(\d+)', text):
            n = int(m.group(1))
            if n not in seen:
                seen.add(n); order.append(n)
        if order != sorted(order):
            FAIL.append(('callout lint: %s first-citation order' % kind,
                         str(sorted(order)), str(order)))
        elif order != list(range(lo, lo + len(order))):
            FAIL.append(('callout lint: %s numbering has a gap' % kind,
                         str(list(range(lo, lo + len(order)))), str(order)))
        else:
            print('   ok   %ss first cited in text in order %s'
                  % (kind, order))


def abstract_lint(path='build_manuscript.js'):
    """Every number printed in the abstract must also appear in the manuscript
    body or in a table cell. Abstract-body drift has bitten this paper before:
    the abstract was revised while the body was not, on three separate claims.
    """
    import re as _re
    src = open(path, encoding='utf-8').read()
    lines = src.split('\n')
    h = [i for i, l in enumerate(lines) if "h1('Abstract'" in l][0]
    m = _re.search(r"body\.push\(p\('((?:[^'\\\\]|\\\\.)*)'", lines[h + 1])
    if not m:
        FAIL.append(('abstract lint: abstract located', 'yes', 'no'))
        return
    abst = m.group(1)
    if any(l.startswith("body.push(p('") for l in lines[h + 2:h + 4]):
        FAIL.append(('abstract lint: single paragraph', 1, '>1'))
    rest = '\n'.join(lines[h + 2:])
    nums = _re.findall(r'\b\d[\d,]*(?:\.\d+)?\b', abst)
    miss = [n for n in nums if n not in rest]
    if miss:
        FAIL.append(('abstract lint: figure absent from body and tables',
                     'present', miss[0]))
    else:
        print('   ok   abstract is one paragraph; all %d of its figures appear '
              'in the body or tables' % len(nums))
    w = len(abst.split())
    if w > 500:
        FAIL.append(('abstract lint: word count vs venue cap', '<=500', w))
    else:
        print('   ok   abstract %d words, within the 500-word venue cap' % w)


def figure4_narrative(m):
    """Section 3.2 and the Figure 4 caption describe the same four quantities.
    They disagreed: the body said the bound falls 43 percent, the caption 42.
    The data say 42.00. Asserted here so the two can no longer drift apart.
    """
    v = m.copy()
    v['bound_t'] = v.imp_floor_px.clip(upper=100)
    v['dec'] = pd.qcut(v.canopy, 10, labels=False)
    g = v.groupby('dec').agg(canopy=('canopy', 'mean'), bound=('bound_t', 'mean'),
                             nlcd=('nlcd', 'mean'))
    x, b, n = g.canopy.values, g.bound.values, g.nlcd.values
    print("\nFIGURE 4  narrative, shared by Section 3.2 and the caption")
    check('F4 bound falls across canopy range (%)', 42, 100 * (b[0] - b[-1]) / b[0], 0.5)
    check('F4 NLCD falls across canopy range (%)', 80, 100 * (n[0] - n[-1]) / n[0], 0.5)
    check('F4 separation at highest decile (pts)', 12.1, b[-1] - n[-1], 0.05)
    i = [k for k in range(9) if (n[k] - b[k]) * (n[k + 1] - b[k + 1]) < 0][0]
    t = (b[i] - n[i]) / ((n[i + 1] - n[i]) - (b[i + 1] - b[i]))
    check('F4 series cross at canopy', 0.28, x[i] + t * (x[i + 1] - x[i]), 0.005)
    ratio = (100 * (n[0] - n[-1]) / n[0]) / (100 * (b[0] - b[-1]) / b[0])
    check('F4 NLCD falls this many times as fast as the bound', 1.9, ratio, 0.05)
    # the strapline drawn inside the figure must match that ratio. It said
    # "more than twice as fast" when the ratio is 1.90.
    try:
        src = open('make_figure_divergence.py', encoding='utf-8').read()
        claim = 'more than twice as fast' in src
        if claim and ratio < 2.0:
            FAIL.append(('F4 in-figure strapline overstates the ratio',
                         'nearly twice', 'more than twice (ratio %.2f)' % ratio))
        else:
            print('   ok   in-figure strapline agrees with the computed ratio '
                  '%.2f' % ratio)
    except FileNotFoundError:
        pass
    sz = v.groupby('dec').size()
    check('F4 smallest decile n', 2189, sz.min(), 0)
    check('F4 largest decile n', 2196, sz.max(), 0)


def settlement_clustering(m):
    """Figure 1's caption claims five of 47 occupied 5 km cells hold N percent
    of the parcels, the stated justification for spatial HAC errors. It said
    56; on the EPSG:5070 5 km grid that yields 47 occupied cells the five
    largest hold 50.3 percent. Albers is recomputed here rather than taken
    from a column, so the check does not depend on the CSV carrying one.
    """
    R, e2 = 6378137.0, 0.0066943800229
    lat0, lon0 = np.radians(23.0), np.radians(-96.0)
    p1, p2 = np.radians(29.5), np.radians(45.5)
    q = lambda t: (1 - e2) * (t / (1 - e2 * t * t) -
                              (1 / (2 * np.sqrt(e2))) *
                              np.log((1 - np.sqrt(e2) * t) / (1 + np.sqrt(e2) * t)))
    mm = lambda t: np.cos(np.arcsin(t)) / np.sqrt(1 - e2 * t * t)
    s1, s2, s0 = np.sin(p1), np.sin(p2), np.sin(lat0)
    n = (mm(s1) ** 2 - mm(s2) ** 2) / (q(s2) - q(s1))
    C = mm(s1) ** 2 + n * q(s1)
    rho0 = R * np.sqrt(C - n * q(s0)) / n
    la, lo = np.radians(m.lat.values), np.radians(m.lon.values)
    rho = R * np.sqrt(C - n * q(np.sin(la))) / n
    th = n * (lo - lon0)
    X, Y = rho * np.sin(th), rho0 - rho * np.cos(th)
    L = 5000.0
    c = (pd.Series(1, index=pd.MultiIndex.from_arrays(
            [np.floor(X / L), np.floor(Y / L)]))
         .groupby(level=[0, 1]).size().sort_values(ascending=False))
    print("\nFIGURE 1  settlement clustering (EPSG:5070 5 km grid)")
    check('F1 occupied 5 km cells', 47, len(c), 0)
    check('F1 share in the five largest (%)', 50, 100 * c.head(5).sum() / len(m), 0.5)

    vc = m.px.value_counts()
    print("\nSECTION 2.2  cell occupancy")
    check('2.2 distinct 30 m cells', 18102, len(vc), 0)
    check('2.2 cells holding exactly one parcel (%)', 83,
          100 * (vc == 1).sum() / len(vc), 0.5)
    check('2.2 parcels in single-parcel cells (%)', 68,
          100 * vc[vc == 1].sum() / len(m), 0.5)



def discussion_figures(m):
    """Every number the Discussion prints. These carried no assertion until now,
    which is how a 43 survived next to a caption saying 42.
    """
    print("\nDISCUSSION  4.3 and 4.4")
    q = m.copy()
    q['aq'] = pd.qcut(q.ac, 4, labels=False)
    c = [ols(q[q.aq == k], 'nlcd')[2][1] for k in range(4)]
    check('4.3 canopy coef, smallest area quartile', -34.06, c[0], 0.05)
    check('4.3 canopy coef, largest area quartile', -13.93, c[3], 0.05)
    x = m[m.improve > 0].copy()
    x['vq'] = pd.qcut(x.improve, 5, labels=False)
    cv = [ols(x[x.vq == k], 'nlcd')[2][1] for k in range(5)]
    check('4.4 canopy coef, lowest value quintile', -24.40, cv[0], 0.05)
    check('4.4 canopy coef, highest value quintile', -17.30, cv[4], 0.05)
    for code, printed, lbl in ((42, 3075, 'evergreen'), (41, 50, 'deciduous'),
                               (43, 67, 'mixed')):
        check('4.4 NLCD forest class, %s parcels' % lbl, printed,
              int((m.lc == code).sum()), 0)


def density_quartile_rises(m):
    """Section 3.3 prints the detection-failure rise in each density quartile as
    30, 28, 31 and 25 percentage points. Unasserted until now."""
    v = m.copy()
    v['q'] = pd.qcut(v.n100, 4, labels=False, duplicates='drop')
    v['cq'] = pd.qcut(v.canopy, 5, labels=False)
    print("\nSECTION 3.3  detection-failure rise by density quartile")
    for k, printed in zip(sorted(v['q'].unique()), (30, 28, 31, 25)):
        s = v[v['q'] == k]
        rise = 100 * (s[s.cq == s.cq.max()].below.mean() - s[s.cq == 0].below.mean())
        check('3.3 rise, density quartile %d (pts)' % (k + 1), printed, rise, 0.5)


def style_lint(path='build_manuscript.js'):
    """Three style rules the author asked for.

    (a) No sentence opens with a coordinating conjunction.
    (b) No run of three or more consecutive sentences in one paragraph opens
        with the same word, unless that word is "the" (the commonest English
        sentence opener; banning it would distort the prose).
    (c) Every figure and table caption carries a short title: the label is
        followed by a title clause closed by a full stop before the
        description begins.
    """
    import re as _re
    src = open(path, encoding='utf-8').read()
    blocks = [(m.group(1), m.group(2)) for m in _re.finditer(
        r"body\.push\((p|caption)\('((?:[^'\\]|\\.)*)'", src)]
    CONJ = _re.compile(r'^(And|But|Or|Nor|Yet|Plus|So)\b')
    bad = []
    for _, x in blocks:
        for t in _re.split(r'(?<=[.?!])\s+(?=[A-Z(])', x):
            if CONJ.match(t.strip()):
                bad.append(' '.join(t.split())[:60])
    if bad:
        FAIL.append(('style lint: sentence opens with a conjunction', 'none', bad[0]))
    else:
        print('   ok   no sentence opens with a coordinating conjunction')

    runs = []
    for _, x in blocks:
        sents = _re.split(r'(?<=[.?!])\s+(?=[A-Z(])', x)
        first = [_re.sub(r'[^A-Za-z]', '', t.split()[0]).lower() if t.split() else ''
                 for t in sents]
        run = 1
        for i in range(1, len(first) + 1):
            if i < len(first) and first[i] and first[i] == first[i - 1]:
                run += 1
            else:
                if run >= 3 and first[i - 1] and first[i - 1] != 'the':
                    runs.append('%dx "%s"' % (run, first[i - 1]))
                run = 1
    if runs:
        FAIL.append(('style lint: repetitive sentence openings', 'none', runs[0]))
    else:
        print('   ok   no run of 3+ sentences opening on the same word (the excepted)')

    caps = [x for k, x in blocks if k == 'caption']
    untitled = []
    for c in caps:
        m = _re.match(r'((?:Table|Figure)\s\d+\.)\s+(.+)', c)
        if not m:
            untitled.append(c[:40]); continue
        title = _re.split(r'(?<=[.?!])\s', m.group(2))[0]
        if (len(title.split()) > 14 or not title.endswith('.')
                or _re.search(r'\d', title) or 'sample' in title.lower()):
            untitled.append(m.group(1) + ' ' + title[:48])
    if untitled:
        FAIL.append(('style lint: caption lacks a short title', 'titled', untitled[0]))
    else:
        print('   ok   all %d captions carry a short title clause' % len(caps))


def data_availability(d, m, path='build_manuscript.js'):
    """The Data availability statement must describe the file that is actually
    released. It claimed "21,931 analysed records" while the deposited CSV
    carries 24,088 rows, the whole frame.
    """
    import re as _re
    src = open(path, encoding='utf-8').read()
    i = src.find("h1('Data availability statement'")
    blk = src[i:i + 2600]
    print("\nDATA AVAILABILITY  statement against the released file")
    for label, printed, actual in (
            ('rows in the released CSV', 24088, len(d)),
            ('analysis sample', 21931, len(m)),
            ('negative control', 589, int(((d.yr.notna()) & (d.yr > 2019)).sum())),
            ('excluded, no year built', 1568, int(d.yr.isna().sum()))):
        shown = '{:,}'.format(printed)
        if shown not in blk:
            FAIL.append(('data availability: %s not stated' % label, shown, 'absent'))
        else:
            check('DA %s' % label, printed, actual, 0)

def manuscript_lint(path='build_manuscript.js'):
    """A straight apostrophe inside a single-quoted body string silently truncates that
    string and breaks the build. Node cannot guard against it, because it fails to parse
    the file before any code in it runs, so the check lives here instead."""
    import os, re as _re
    if not os.path.exists(path):
        return
    print("\nMANUSCRIPT LINT  single-quoted body strings")
    src = open(path, encoding='utf-8').read()
    pat = _re.compile(r"body\.push\((?:p|caption|h1|h2)\('((?:[^'\\]|\\.)*)'")
    bad = []
    for m in pat.finditer(src):
        tail = src[m.end():m.end() + 2]
        if _re.match(r'[A-Za-z]', tail):
            bad.append(m.group(1)[-55:] + " <<HERE>> " + tail)
    if bad:
        for b in bad:
            print("   FAIL  truncated string near: ..." + b)
        FAIL.append(("manuscript lint: straight apostrophe in a single-quoted string",
                     0, len(bad)))
    else:
        print(f"   ok   {len(pat.findall(src))} body strings, none truncated by a straight apostrophe")



def table4_tvalues(d, m):
    """Every t-value printed in Table 4, against the estimator its caption claims.

    The harness asserted Table 4's coefficients but not its t-values, and that
    gap hid a real error: the caption read "All standard errors here are HC1"
    while six of the eleven rows that report a t were in fact Conley spatial
    HAC at 5 km. For the frame-restriction rows the HC1 t-values are around
    minus 50, not around minus 10, so the caption was not a small slip.

    Each row is checked against BOTH estimators and must match the one the
    caption now names, so a future edit cannot quietly swap one for the other.
    """
    print("\nTABLE 4  printed t-values against the estimator the caption names")
    lat0 = m.lat.mean()

    def tt(s, y, xs=H, which=1):
        X, Y, b, e, XtXi, _ = ols(s, y, xs)
        h = se_hc1(X, e, XtXi, which)
        c = se_conley(X, e, XtXi, s.xk.values, s.yk.values, 5.0, which)
        return b[which], b[which] / h, b[which] / c

    def row(tag, kind, printed, s, y, xs=H, which=1):
        _, th, tc = tt(s, y, xs, which)
        got = th if kind == 'HC1' else tc
        other = tc if kind == 'HC1' else th
        check("T4 t %s (%s)" % (tag, kind), printed, got, 0.06)
        assert abs(other - printed) > 0.5, (
            "%s: the %s t also matches %.1f, so this row does not discriminate"
            % (tag, 'Conley' if kind == 'HC1' else 'HC1', printed))

    # HC1 block
    row('conditioning on the bound', 'HC1', -49.5, m, 'nlcd',
        ['canopy', 'ac', 'sqft', 'slope', 'n100', 'imp_floor_px'])
    row('canopy on the bound itself', 'HC1', -23.7, m, 'imp_floor_px')
    nc = d[(d.yr.notna()) & (d.yr > 2019)].copy()
    nc['xk'] = (nc.lon - m.lon.mean()) * 111.32 * np.cos(np.radians(lat0))
    nc['yk'] = (nc.lat - m.lat.mean()) * 110.57
    row('negative control', 'HC1', -1.4, nc, 'nlcd')
    q = m.copy()
    q['canopy2'] = q.canopy ** 2
    row('quadratic in canopy', 'HC1', 6.1, q, 'nlcd',
        ['canopy', 'canopy2', 'ac', 'sqft', 'slope', 'n100'], which=2)
    mg = m.copy()
    mg['belowA'] = (mg.nlcd < mg.floorA).astype(float)
    row('bound excluding garages', 'HC1', 27.7, mg, 'belowA')

    # Conley block
    #
    # The detection-failure quadratic is the curvature Section 3.3 cites for the
    # delayed onset in the densest density stratum. Section 3.3 used to cite the
    # impervious quadratic above instead, whose sign implies the OPPOSITE
    # pattern: with a positive squared term on a falling outcome the marginal
    # effect weakens as canopy rises, so the impervious loss is front-loaded,
    # not delayed. The two outcomes genuinely curve in opposite directions, and
    # the cross-reference pointed at the one that contradicted the sentence.
    # Both ends of the marginal effect are asserted below so the direction
    # cannot be inverted again without the harness noticing.
    row('quadratic, detection failure', 'CONLEY', 4.3, q, 'below',
        ['canopy', 'canopy2', 'ac', 'sqft', 'slope', 'n100'], which=2)
    X, _, b, e, XtXi, _ = ols(q, 'below',
                              ['canopy', 'canopy2', 'ac', 'sqft', 'slope', 'n100'])
    check("T4 quadratic, detection failure coefficient", 0.3063, b[2], 0.0006)
    check("3.3 marginal effect on detection failure at no canopy", 0.03, b[1], 0.006)
    check("3.3 marginal effect on detection failure at closed canopy",
          0.64, b[1] + 2 * b[2], 0.006)
    assert b[1] + 2 * b[2] > 4 * abs(b[1]), (
        'Section 3.3 says the effect on detection failure activates late, running '
        'from plus 0.03 at no canopy to plus 0.64 under closed canopy; it does not')

    # Table 4 calls the impervious quadratic convex under HC1 and not separable
    # from zero under spatial HAC. That is a claim about an absence, so it is
    # checked as one: the Conley t must stay below 2 at the 5 km cutoff the
    # caption names. It degrades with the cutoff (2.5, 2.0, 1.7 at 1, 2 and
    # 5 km), so this is not an artefact of the widest kernel.
    _, th_q, tc_q = tt(q, 'nlcd', ['canopy', 'canopy2', 'ac', 'sqft', 'slope', 'n100'], 2)
    if th_q > 2 and abs(tc_q) < 2:
        print('   ok   the impervious quadratic is significant under HC1 (t = %.1f) '
              'and not under Conley (t = %.1f), as Table 4 states' % (th_q, tc_q))
    else:
        FAIL.append(('Table 4 impervious quadratic robustness',
                     'HC1 t %.1f, Conley t %.1f' % (th_q, tc_q),
                     'HC1 above 2 and Conley below 2'))
        print('   FAIL  Table 4 calls the impervious quadratic convex under HC1 only, '
              'but HC1 t = %.1f and Conley t = %.1f' % (th_q, tc_q))

    k = m.groupby('px').apn.transform('size')
    row('dropping truncated cells', 'CONLEY', -9.7, m[m.imp_floor_raw <= 100], 'nlcd')
    row('cells holding one parcel', 'CONLEY', -9.0, m[k == 1], 'nlcd')
    row('dominant use code only', 'CONLEY', -11.1, m[m.use == 100], 'nlcd')
    row('lots of at least 0.05 ac', 'CONLEY', -10.0, m[m.ac >= 0.05], 'nlcd')
    print("   ok   every checked t-value matches the estimator the caption names, "
          "and not the other one")



def oehha_reference(m):
    """Section 3.7: NLCD against the published OEHHA full-impervious reference.

    These figures ran in analyze_canopy_bias.py but were asserted nowhere, so a
    coverage audit of every printed number found them uncovered. That is the
    same class of gap that let a wrong t-value stand in Table 3: a number the
    analysis produces, the manuscript prints, and nothing checks.

    ISC = 0.2449 + 0.352 log10(dwelling units per acre), valid over 1 to 50
    du/ac (OEHHA 2010). The 100 m neighbour radius encloses 7.76 acres, close
    to the 9-acre boxes the coefficients were digitised in.
    """
    print("\nSECTION 3.7  NLCD against the OEHHA published reference")
    ac100 = np.pi * 100 ** 2 / 4046.86
    v = m.assign(du_ac=(m.n100 + 1) / ac100)
    inrange = v[(v.du_ac >= 1) & (v.du_ac <= 50)].copy()
    check("3.7 parcels in the valid 1-50 du/ac range", 19545, len(inrange), 0)
    check("3.7 parcels outside that range", 2386, len(v) - len(inrange), 0)
    assert len(inrange) + (len(v) - len(inrange)) == len(m), 'the two parts must sum to the sample'
    inrange['isc'] = 100 * (0.2449 + 0.352 * np.log10(inrange.du_ac))
    inrange['gap'] = inrange.nlcd - inrange.isc
    dec = pd.qcut(inrange.canopy, 10, labels=False)
    t = inrange.groupby(dec).agg(gap=('gap', 'mean'),
                                 above=('gap', lambda s: 100 * (s > 0).mean()))
    lo, hi = t.iloc[0], t.iloc[-1]
    check("3.7 lowest-decile gap from the reference", 0.84, lo.gap, 0.006)
    check("3.7 highest-decile gap from the reference", -25.87, hi.gap, 0.006)
    check("3.7 highest-decile share above the reference (%)", 3.2, hi.above, 0.06)
    check("3.7 swing against the published reference", 26.7, lo.gap - hi.gap, 0.06)
    assert 49 <= lo.above <= 51, (
        'the manuscript says half of parcels sit above the reference at low '
        'canopy; got %.1f per cent' % lo.above)
    print("   ok   calibration holds at low canopy and fails at high canopy")


def figure3_pair_arithmetic(d=None, m=None):
    """Section 3.1 and the Figure 3 caption: the matched pair's stated
    floor-area difference must equal the difference of the two stated areas.

    The Figure 2 caption walks Equations 1 and 2 through the canopied parcel of
    the pair in full: "1,470 square feet of floor area, one storey, a 725 square
    foot attached garage, built in 1998", giving "204 square metres of roofed
    ground". A fresh numeric coverage audit at 396 assertions found every one of
    those inputs uncovered: only the 51 square foot difference below was checked.
    They are the most legible numbers in the paper, because a reader can follow
    the arithmetic by hand, and nothing tied them to the parcel's own record.
    All five verified correct against the released row. Also asserted here is
    Section 2.1's floor-area filter, which the frame must not violate.
    """
    a, b = 1521, 1470
    check("F3 matched-pair floor-area difference (sq ft)", 51, a - b, 0)
    if m is None:
        return
    r = m[m.apn == '045300033000']
    if not len(r):
        SKIPPED.append('the Figure 2 worked example (illustrated parcel absent)')
        print('   (the illustrated parcel is not in the frame; skipping)')
        return
    r = r.iloc[0]
    check("F2 illustrated parcel floor area (sq ft)", 1470, float(r.sqft), 0)
    check("F2 illustrated parcel storeys", 1, float(r.storeys), 0)
    check("F2 illustrated parcel garage (sq ft)", 725, float(r.garage), 0)
    check("F2 illustrated parcel year built", 1998, float(r.yr), 0)
    check("F2 illustrated parcel roofed ground (sq m)", 204,
          (r.sqft / r.storeys + r.garage) * 0.092903, 0.5)   # Equation 1
    if d is not None:
        check("2.1 smallest floor area in the frame (sq ft)", 400, float(d.sqft.min()), 0)



def released_data_consistency(path):
    """The released CSV must be self-consistent with the paper's own definitions.

    It was not. Every breach indicator in the file had been computed before the
    100 per cent ceiling of Equation 2 was applied, so a reviewer analysing the
    released data directly would have found WorldCover failing on 76.3 per cent
    of parcels where the paper prints 75.9, and reported that the data do not
    reproduce the manuscript. The paper was right: load() re-derives every one
    of these columns from the truncated bound, so no published number was ever
    affected. The stale columns have been recomputed in the released file, and
    this check keeps them that way.

    imp_floor_px and floorA stay UNTRUNCATED in the release, because the
    truncation diagnostics need the raw values; the ceiling belongs to the
    breach indicators derived from them.
    """
    print("\nRELEASED DATA  breach indicators against the stated definition")
    raw = pd.read_csv(path, dtype={'apn': str, 'px': str})
    tb = raw.imp_floor_px.clip(upper=100)
    ta = raw.floorA.clip(upper=100)
    for col, prod, bound in [('below', 'nlcd', tb), ('belowA', 'nlcd', ta),
                             ('below_dw', 'dw', tb), ('below_wc', 'wc', tb),
                             ('below_ghsl', 'ghsl', tb)]:
        if col not in raw.columns or prod not in raw.columns:
            continue
        expected = (raw[prod] < bound).astype(int)
        bad = int((expected != raw[col].astype(int)).sum())
        check(f"released {col} matches {prod} < truncated bound", 0, bad, 0)
    assert (raw.imp_floor_px > 100).any(), (
        'imp_floor_px looks truncated in the release; the truncation '
        'diagnostics need the raw bound')
    check("released row count", 24088, len(raw), 0)
    check("released column count", 39, raw.shape[1], 0)
    assert raw.apn.is_unique, 'APN is not unique in the released file'

    # Relations that must hold between columns. These would catch a partially
    # regenerated or corrupted release, which a row count alone would not.
    SQFT2M2 = 0.092903
    rel = [
        ('roof_m2 == (sqft/storeys + garage) x 0.092903',
         np.isclose(raw.roof_m2, (raw.sqft / raw.storeys + raw.garage.fillna(0)) * SQFT2M2,
                    rtol=1e-6, atol=1e-4)),
        ('imp_floor_px == 100 x pixel_roof_m2 / 900',
         np.isclose(raw.imp_floor_px, 100 * raw.pixel_roof_m2 / 900, rtol=1e-6, atol=1e-4)),
        ('pixel_roof_m2 == sum of roof_m2 over the cell',
         np.isclose(raw.pixel_roof_m2, raw.groupby('px').roof_m2.transform('sum'),
                    rtol=1e-6, atol=1e-3)),
        ('n_bldg_px == parcels sharing the cell',
         raw.n_bldg_px == raw.groupby('px').apn.transform('size')),
        ('canopy5 <= canopy', raw.canopy5 <= raw.canopy + 1e-9),
        ('n100 <= n250', raw.n100 <= raw.n250),
        ('floorA <= imp_floor_px', raw.floorA <= raw.imp_floor_px + 1e-9),
    ]
    for lab, ok in rel:
        check(f"released {lab}", 0, int((~np.asarray(ok)).sum()), 0)
    # the three subsets must partition the file exactly
    n_an = int(((raw.yr.notna()) & (raw.yr <= 2019)).sum())
    n_nc = int(((raw.yr.notna()) & (raw.yr > 2019)).sum())
    check("released analysis sample", 21931, n_an, 0)
    check("released negative control", 589, n_nc, 0)
    check("released parcels with no year built", 1568, int(raw.yr.isna().sum()), 0)
    assert n_an + n_nc + int(raw.yr.isna().sum()) == len(raw), (
        'the analysis sample, the negative control and the undated parcels must '
        'partition the released file')
    check("negative control built in 2020 or 2021", 242,
          int(raw.loc[(raw.yr > 2019), 'yr'].isin([2020, 2021]).sum()), 0)
    print("   ok   the release reproduces the paper's definitions exactly")



def causal_language_lint():
    """The paper states that its language is associational. This holds it to that.

    Section 4.1 says plainly "It is not a demonstration that canopy causes it"
    and "these data cannot separate the first two, which is why the language
    throughout is associational". A causal verb attached to canopy anywhere else
    would contradict the paper's own stated standard, and is exactly the error
    that had to be corrected once already in the graphical abstract title, which
    read that canopy "hides" buildings.

    A sentence that disclaims causation may of course name it, so sentences
    carrying a negation are exempt.
    """
    import re
    print("\nPROSE  causal language about canopy")
    src = open('build_manuscript.js', encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda m: chr(int(m.group(1), 16)), s).replace("\\'", "'")
    text = ' '.join(unesc(m.group(2)) for m in
                    re.finditer(r"body\.push\((p|caption)\('((?:[^'\\\\]|\\\\.)*)'", src))
    verbs = ['causes', 'caused', 'causing', 'hides', 'hiding', 'obscures', 'obscuring',
             'blocks', 'blocking', 'conceals', 'concealing', 'prevents', 'preventing',
             'leads to', 'results in', 'drives', 'driving', 'produces', 'producing']
    NEG = re.compile(r'\b(not|cannot|never|no\b|rather than|without)\b', re.I)
    bad = []
    for v in verbs:
        for m in re.finditer(r'[^.]*\b%s\b[^.]*\.' % re.escape(v), text):
            s = ' '.join(m.group(0).split())
            if re.search(r'\bcanop', s, re.I) and not NEG.search(s):
                bad.append('%r: %s' % (v, s[:110]))
    for b in bad:
        FAIL.append(('causal language about canopy', b, 'none allowed'))
        print('   FAIL  %s' % b)
    if not bad:
        print("   ok   no unhedged causal verb attached to canopy")



def hypothesis_containment(path='build_manuscript.js'):
    """Two recorded decisions about what the paper may claim, held in place.

    First, the sign-change reading. Combining this paper's canopy gradient with
    the metropolitan pattern in Wickham et al. (2020) suggests the sign of the
    error turns with settlement density, and that would reconcile Nowak and
    Greenfield (2010) against that literature. Nothing here tests it: a test
    needs a reference capturing all impervious surface, not roofs alone. The
    project record is explicit, "Present it as a hypothesis the data motivate,
    never as a result", so the idea is confined to one paragraph at the end of
    Section 4.4, that paragraph must carry its own disclaimer, and none of its
    language may appear in the abstract, the results or the conclusions.

    Second, the canopy threshold. An earlier note claimed "the 2 m definition
    fits best, which favours spectral mixing over occlusion". On the census that
    is not supported: the two thresholds differ by about 0.005 in R-squared and
    the 5 m threshold fits better on the below-floor outcome. The record directs
    reporting the comparison as a sensitivity and dropping the claim. The row
    must therefore keep both thresholds in its own label, so a reader can see
    the span over which "robust" is asserted, and no mechanism may be inferred
    from the threshold anywhere.
    """
    import re
    print("\nPROSE  the sign-change reading stays a hypothesis; the threshold "
          "stays a sensitivity")
    src = open(path, encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), s).replace("\\'", "'")
    blocks = [(k, unesc(t)) for k, t in re.findall(
        r"body\.push\((h1|h2|p|caption)\('((?:[^'\\]|\\.)*)'", src)]

    HYP = 'as a hypothesis rather than as a result'
    idx = [i for i, (k, t) in enumerate(blocks) if HYP in t]
    if len(idx) != 1:
        FAIL.append(('sign-change hypothesis paragraph', '%d found' % len(idx),
                     'exactly 1, at the end of Section 4.4'))
        print('   FAIL  %d paragraph(s) carry the hypothesis framing, expected 1'
              % len(idx))
        return
    i = idx[0]
    para = blocks[i][1]

    # The paragraph must disclaim itself, not merely hedge with "if".
    for phrase in ('Nothing measured here tests that',
                   'all impervious surface rather than roofs alone'):
        if phrase in para:
            print('   ok   hypothesis paragraph states %r' % phrase[:46])
        else:
            FAIL.append(('hypothesis paragraph', 'missing', phrase))
            print('   FAIL  hypothesis paragraph does not say %r' % phrase[:46])

    # Placement: last block of Section 4.4, immediately before the conclusions.
    head = next((t for k, t in reversed(blocks[:i]) if k in ('h1', 'h2')), '')
    nxt = next((t for k, t in blocks[i + 1:] if k in ('h1', 'h2')), '')
    check_str('hypothesis sits under', head, '4.4. External validity and the urban extension')
    check_str('hypothesis is followed by', nxt, '5. Conclusions')

    # Containment. None of the hypothesis language may appear anywhere else,
    # and the abstract and conclusions are checked by name as well as by index.
    # Cues are written with a straight apostrophe and both sides are normalised,
    # because the fourth one used to carry a curly apostrophe matching the
    # manuscript's. That worked only while the manuscript kept that exact
    # character: a switch to a straight apostrophe anywhere in the toolchain
    # would have left this cue matching nothing, silently, while the other three
    # kept passing and hid the gap.
    def _flat(s):
        return (s.replace('’', "'").replace('‘', "'")
                 .replace('“', '"').replace('”', '"'))

    cues = ['sign of the error', 'consistent rather than contradictory',
            'all impervious surface', "stormwater utility's measured"]
    leaks = []
    for j, (k, t) in enumerate(blocks):
        if j == i:
            continue
        for c in cues:
            if c in _flat(t):
                leaks.append('%s block %d: %r' % (k, j, c))
    # A containment check asserts an absence, so it passes for free the moment the
    # cue stops existing anywhere. Three of these four were never verified to be
    # in the paragraph they are supposed to be confined to: reword one in the
    # manuscript and its containment check keeps saying ok while guarding nothing.
    # Anchor every cue in the paragraph first, then assert it appears nowhere else.
    absent = [c for c in cues if c not in _flat(para)]
    if absent:
        FAIL.append(('hypothesis cues not in the paragraph they confine',
                     'all present', ', '.join(repr(c) for c in absent),
                     ('expected', 'missing')))
        print('   FAIL  %s no longer in the hypothesis paragraph, so confining '
              'them checks nothing' % ', '.join(repr(c) for c in absent))
    else:
        print('   ok   all %d hypothesis cues are in the paragraph they confine' % len(cues))
    for L in leaks:
        FAIL.append(('hypothesis language outside Section 4.4', L, 'none allowed'))
        print('   FAIL  %s' % L)
    if not leaks:
        print('   ok   no hypothesis language in the abstract, results or conclusions')

    # The retracted threshold justification must not return, in any wording.
    text = ' '.join(t for k, t in blocks if k in ('p', 'caption'))
    bad = []
    for m2 in re.finditer(r'[^.]*\b(2 m|5 m|threshold)\b[^.]*\.', text):
        s = ' '.join(m2.group(0).split())
        if re.search(r'fits (best|better)|best.fitting|favours (spectral|occlusion)'
                     r'|supports (spectral|occlusion)|which favours', s, re.I):
            bad.append(s[:120])
    for b in bad:
        FAIL.append(('threshold justification', b, 'report as a sensitivity only'))
        print('   FAIL  threshold claim: %s' % b)
    if not bad:
        print('   ok   no claim that either threshold fits best or favours a mechanism')

    # The Table 4 row must keep both thresholds in its label, so the scope of
    # "robust" is visible. The census carries 2 m and 5 m only, not 10 m.
    row = "'Canopy threshold, 2 m against 5 m'"
    if row in src:
        print('   ok   Table 4 names the two thresholds compared')
    else:
        FAIL.append(('Table 4 threshold row', 'label changed', row))
        print('   FAIL  Table 4 no longer names both thresholds: %s' % row)


def cover_letter_claims(path='build_cover_letter.js'):
    """Every figure the cover letter quotes to the editor must come from the paper.

    The letter is the first thing an editor reads and the last thing anyone
    re-checks. It repeats a dozen of the manuscript's numbers from memory, so a
    revision to the paper can silently leave the letter asserting a figure the
    paper no longer prints, and the editor has no way to tell which is current.

    Every number in the letter must therefore appear in the manuscript. The one
    exception is the assertion count, which describes the harness rather than
    the paper and is checked against the README separately.
    """
    import os
    import re
    print("\nCOVER LETTER  every quoted figure against the manuscript")
    if not os.path.exists(path):
        _print("   (%s is absent; not part of the reproduction package)" % path)
        return
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), s).replace("\\'", "'")
    js = open(path, encoding='utf-8').read()
    letter = re.sub(r'\*+', '', ' '.join(unesc(m.group(1)) for m in re.finditer(
        r"body\.push\((?:p|tight)\('((?:[^'\\]|\\.)*)'", js)))
    # Compare against the whole builder source, not parsed blocks: the ORCID
    # and other front-matter values live in run arrays that a block parser
    # scoped to p/caption does not return, and a first version of this check
    # reported them as unsourced.
    ms = unesc(open('build_manuscript.js', encoding='utf-8').read())
    claim = re.search(r'([\d,]+)\s+assertions', letter)
    allowed = {claim.group(1)} if claim else set()
    missing = []
    for n in dict.fromkeys(re.findall(r'\d[\d,]*\.?\d*', letter)):
        if n not in allowed and n not in ms:
            missing.append(n)
    if missing:
        FAIL.append(('cover letter quotes figures the manuscript does not',
                     ', '.join(missing), 'every figure must be in the paper'))
        _print('   FAIL  the letter quotes %s, which the manuscript does not print'
               % ', '.join(missing))
    else:
        _print('   .    every figure the letter quotes is in the manuscript (not counted)')

    # The letter's header block reproduces the manuscript's title and the author
    # line. A comment in build_manuscript.js records that the title was once
    # truncated at "built-surface products", losing its second half, so this is a
    # drift that has actually happened. A cover letter naming a title the
    # manuscript does not carry is the first thing an editor notices.
    hdr = re.search(r"\*\*Manuscript:\*\*\s*((?:[^'\\]|\\.)*?)'", js)
    # Anchor on the document-metadata title, the one followed by description.
    # A first version matched the bare pattern title:, which found a figure's
    # alt-text title instead and reported a mismatch against "Figure 1. Study
    # area". Three checks in this file have now failed by matching the first
    # thing that looked right rather than the thing meant.
    ttl = re.search(r"title:\s*'((?:[^'\\]|\\.)*)',\s*\n\s*description:",
                    open('build_manuscript.js', encoding='utf-8').read())
    if hdr and ttl:
        a, b = unesc(hdr.group(1)).strip(), unesc(ttl.group(1)).strip()
        if a == b:
            _print('   .    the letter names the manuscript title exactly (not counted)')
        else:
            FAIL.append(('cover letter title', a[:60], b[:60]))
            _print('   FAIL  the letter and the manuscript disagree on the title')
    else:
        FAIL.append(('cover letter title', 'not found', 'a Manuscript: line and a title'))
        _print('   FAIL  could not locate the title in one of the two files')


def literature_figures(path='build_manuscript.js'):
    """The quoted literature figures, pinned to what the source papers say.

    These are the only numbers in the manuscript that no computation can check,
    because they come from other people's papers. The project record carried
    them as the last unverified material and set 8.5 as the honest ceiling for
    Section 1 until they were read out of the sources. They have now been read.

    Nowak and Greenfield (2010), Environmental Management 46 (3): 378-390,
    doi:10.1007/s00267-010-9536-9.
      Abstract: "Impervious cover was also underestimated in 44 zones with an
      average underestimation of 1.4% (SE = 0.4%)".
      Results: "NLCD estimates in developed land also significantly
      underestimated impervious cover in 14 mapping zones, overestimated
      impervious cover in three zones, and had an overall impervious cover
      underestimation of 5.2% (SE = 4.8%)".
      Scope: 65 mapping zones across the conterminous United States.

    Wickham et al. (2020), Int. J. Appl. Earth Obs. Geoinf. 84: 101955.
      18 metropolitan areas; 1st and 99th percentile deviations of -29.21 and
      +25.31 percent at the 1 ha assessment unit, confirmed against the
      publisher's record in an earlier pass.

    What this check can and cannot do: it cannot re-read the papers, so it
    asserts that the manuscript still prints the values that were read. If
    someone edits one, the run fails and the source has to be consulted again
    rather than the number quietly changed.
    """
    import re
    print("\nLITERATURE  quoted figures against the source papers")
    src = open(path, encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), s).replace("\\'", "'")
    text = ' '.join(unesc(m.group(2)) for m in re.finditer(
        r"body\.push\((p|caption)\('((?:[^'\\]|\\.)*)'", src))
    claims = [
        ('N&G 2010 national impervious underestimate', r'1\.4 percentage points'),
        ('N&G 2010 its standard error', r'standard error 0\.4'),
        ('N&G 2010 developed-land underestimate', r'5\.2 points'),
        ('N&G 2010 its standard error', r'standard error of 4\.8'),
        ('N&G 2010 mapping zones', r'65 mapping zones'),
        ('Wickham 2020 metropolitan areas', r'18 metropolitan areas'),
        ('Wickham 2020 1st percentile', r'minus 29\.2'),
        ('Wickham 2020 99th percentile', r'plus 25\.3'),
        ('Wickham 2020 assessment unit', r'1 ha assessment unit'),
    ]
    for label, pat in claims:
        if re.search(pat, text):
            print('   ok   %-42s as the source gives it' % label)
        else:
            FAIL.append((label, 'not found in the manuscript', pat))
            print('   FAIL  %s no longer appears as %s' % (label, pat))


def mechanism_claim_lint(path='build_manuscript.js'):
    """Section 4 says these data cannot separate occlusion from spectral mixing.
    Titles and keywords are asserted by nature, so they must not name one.

    The keyword "tree canopy occlusion" was caught and changed to "tree canopy"
    for exactly this reason. The same claim then survived in two places the
    keyword pass did not look: Figure 3's caption title read "Canopy occlusion
    at two matched parcels", and Figure 1's map legend labelled the two sites
    "parcels in the occlusion figure". Both asserted the mechanism the paper
    disclaims, in the most quotable line each element has.

    Running prose is not the target. "The bound cannot inherit the occlusion it
    is used to detect" is a property of the reference, conditional on occlusion
    existing, and is fine. This checks the caption title clause, which is the
    sentence a reader takes as the figure's claim, and the keyword list.
    """
    import re
    print("\nPROSE  mechanism named in a caption title or keyword")
    src = open(path, encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), s).replace("\\'", "'")
    MECH = re.compile(r'occlusion|occluded|occluding|spectral mixing|shadowing', re.I)
    bad = []
    for m in re.finditer(r"body\.push\(caption\('((?:[^'\\]|\\.)*)'", src):
        cap = unesc(m.group(1))
        # the title clause: what follows the "Figure n." label, up to its own stop
        t = re.match(r'\s*(?:Figure|Table)\s+\d+\.\s*([^.]*)\.', cap)
        if t and MECH.search(t.group(1)):
            bad.append('caption title: %r' % t.group(1)[:80])
    # The keyword list is built as a run array, not a plain string, so it is
    # located by the bold "Keywords: " run and read from the run that follows.
    # A first draft searched for a 'Keywords:...' string literal, found nothing,
    # and passed silently, which is the vacuous-check failure this project has
    # already been bitten by once. A missing list is now a failure, not a pass.
    kw = re.search(r"\{\s*t:\s*'Keywords:\s*',\s*b:\s*true\s*\}\s*,\s*\n?\s*"
                   r"\{\s*t:\s*'((?:[^'\\]|\\.)*)'", src)
    if not kw:
        FAIL.append(('keyword list', 'not found', 'a Keywords run must exist'))
        print('   FAIL  could not locate the keyword list, so it went unchecked')
    elif MECH.search(unesc(kw.group(1))):
        bad.append('keyword list: %r' % unesc(kw.group(1))[:80])
    # The same claim survived a third time, in a place neither the caption pass
    # nor the keyword pass looked: SUBMISSION_CHECKLIST.md's figure table still
    # called Figure 3 "Canopy occlusion", the pre-rename title. A shipped
    # document naming a figure is naming it as the figure's claim, exactly as a
    # caption title does, so the figure-naming tables of the shipped docs are
    # read the same way. Only the first cell of a row in a table whose header
    # names Figure is read: running prose in these files uses the word
    # legitimately, and the README's discussion of what the bound cannot inherit
    # must stay untouched.
    import os
    for doc in ('SUBMISSION_CHECKLIST.md', 'README.md'):
        if not os.path.exists(doc):
            continue
        in_fig_table = False
        for line in open(doc, encoding='utf-8'):
            if not line.lstrip().startswith('|'):
                in_fig_table = False
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cells and cells[0].lower() == 'figure':
                in_fig_table = True
                continue
            if in_fig_table and cells and MECH.search(cells[0]):
                bad.append('%s figure table: %r' % (doc, cells[0][:60]))

    for b in bad:
        FAIL.append(('mechanism asserted in a title', b, 'Section 4 disclaims it'))
        print('   FAIL  %s' % b)
    if not bad:
        print('   ok   no caption title, keyword or shipped figure table names a '
              'mechanism the paper disclaims')


def journal_limits(path='build_manuscript.js'):
    """The journal's hard bounds, and the element order a desk check reads.

    `canopy-bias-author-guidelines-compliance.md` records these as PASS from the
    journal's own Instructions for Authors: an unstructured abstract within 500
    words, between 4 and 6 keywords, and the Research Article element order. All
    three were verified by hand once and then left to drift. The abstract has
    been rewritten several times since, and nothing would have caught it crossing
    500 words, which is the kind of thing a desk editor bounces rather than
    queries.

    The element order is checked as a subsequence, not an exact list, so adding a
    numbered section or a new back-matter block does not fail it; only an element
    appearing out of order or going missing does.

    The body word count is deliberately NOT asserted. The journal offers
    format-free submission with no length requirement for a Research Article, so
    a number here would be a gate on nothing. It is recorded in the compliance
    doc for the separate argument about article type, where the count only has to
    be large enough, and it has grown from 6,277 to about 6,900 since.
    """
    import re
    print("\nJOURNAL  abstract length, keyword count and element order")
    src = open(path, encoding='utf-8').read()
    unesc = lambda t: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), t).replace("\\'", "'")

    seq = [(m.group(1), unesc(m.group(2))) for m in
           re.finditer(r"body\.push\((h1|h2|p|caption)\('((?:[^'\\]|\\.)*)'", src)]

    # the abstract is the first paragraph after the Abstract heading
    abstract = None
    for i, (kind, txt) in enumerate(seq):
        if kind == 'h1' and txt.strip().lower().startswith('abstract'):
            for kind2, txt2 in seq[i + 1:]:
                if kind2 == 'p':
                    abstract = txt2
                    break
            break
    if abstract is None:
        FAIL.append(('abstract', 'not found', 'a paragraph after the Abstract heading'))
        print('   FAIL  could not locate the abstract, so it went unchecked')
    else:
        n = len(abstract.split())
        check("abstract words", 337, n, 0)
        if n <= 500:
            print('   ok   the abstract is %d words, within the 500 word limit' % n)
        else:
            FAIL.append(('abstract over the journal limit', n, 'at most 500 words'))
            print('   FAIL  the abstract is %d words, over the 500 word limit' % n)

    kw = re.search(r"\{\s*t:\s*'Keywords:\s*',\s*b:\s*true\s*\}\s*,\s*\n?\s*"
                   r"\{\s*t:\s*'((?:[^'\\]|\\.)*)'", src)
    if not kw:
        FAIL.append(('keyword list', 'not found', 'a Keywords run must exist'))
        print('   FAIL  could not locate the keyword list, so it went unchecked')
    else:
        words = [k.strip() for k in re.split(r'[;,]', unesc(kw.group(1))) if k.strip()]
        check("keywords", 6, len(words), 0)
        if 4 <= len(words) <= 6:
            print('   ok   %d keywords, within the range of 4 to 6' % len(words))
        else:
            FAIL.append(('keyword count outside the journal range', len(words),
                         'between 4 and 6'))
            print('   FAIL  %d keywords, outside the range of 4 to 6' % len(words))

    REQUIRED = ['Abstract', '1. Introduction', '2. Materials and methods',
                '3. Results', '4. Discussion', 'Acknowledgements', 'Funding',
                'Disclosure statement', 'Data availability statement', 'References']
    h1s = [t.strip() for k, t in seq if k == 'h1']
    pos, missing, i = [], [], 0
    for want in REQUIRED:
        found = None
        for j in range(i, len(h1s)):
            if h1s[j].lower().startswith(want.lower()):
                found = j
                break
        if found is None:
            missing.append(want)
        else:
            pos.append(found)
            i = found + 1
    if missing:
        FAIL.append(('element order', 'missing or out of order: ' + ', '.join(missing),
                     'the Research Article element order'))
        print('   FAIL  element(s) missing or out of order: %s' % ', '.join(missing))
    else:
        print('   ok   all %d required elements appear in the Research Article order'
              % len(REQUIRED))


def rendered_matches_source():
    """The .docx files the author submits must carry the text the sources hold.

    This was the largest remaining hole. The harness asserts the SOURCE is right,
    `check_layout.py` inspects the RENDERED PDF, and nothing tied the two
    together: edit `build_manuscript.js`, forget to rerun node, and every gate
    stays green while the shipped document is a version behind. A reviewer's
    clean unzip carries both files, so a disagreement between them undermines
    the whole package.

    Checked by content, never by timestamp. Modification times are worthless
    here: restoring a byte-identical file from a backup, which this project does
    to prove a check fires, updates the mtime and would report a false staleness
    every time.

    Two normalisations are required and both were needed in practice. The
    markdown copy of the letter uses straight apostrophes so it survives being
    pasted into a submission form while the .docx uses typographic ones, and
    `word/document.xml` XML-escapes ampersands, so "GIScience & Remote Sensing"
    arrives as "GIScience &amp; Remote Sensing" and the To: line appeared to be
    missing until the entities were unescaped.
    """
    import html
    import os
    import re
    import zipfile
    print("\nRENDERED  the submitted .docx against the source it is built from")

    def docx_text(f):
        x = zipfile.ZipFile(f).read('word/document.xml').decode('utf-8')
        x = re.sub(r'</w:p>', '\n', x)
        return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', x)))

    norm = lambda t: ' '.join(re.sub(r'\*+', '', t)
                              .replace('’', "'").replace('‘', "'")
                              .replace('“', '"').replace('”', '"').split())
    unesc = lambda t: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), t).replace("\\'", "'")

    # The cover letter is a submission document and is NOT in the reproduction
    # package, so its result reports through _print and does not add to the "ok"
    # tally. Counting it made the total 413 in the working tree and 412 from a
    # clean unzip, and the README cannot state a number true in both. The
    # existing cover-letter checks are reported the same way for the same reason.
    jobs = []
    if os.path.exists('canopy_bias_manuscript_GIScienceRS.docx') and \
            os.path.exists('build_manuscript.js'):
        js = open('build_manuscript.js', encoding='utf-8').read()
        src = [unesc(m.group(1)) for m in
               re.finditer(r"body\.push\((?:p|caption)\('((?:[^'\\]|\\.)*)'", js)]
        jobs.append(('the manuscript', 'canopy_bias_manuscript_GIScienceRS.docx',
                     src, 80, True))
    if os.path.exists('COVER_LETTER.docx') and os.path.exists('COVER_LETTER.md'):
        md = open('COVER_LETTER.md', encoding='utf-8').read()
        jobs.append(('the cover letter', 'COVER_LETTER.docx',
                     re.split(r'\n\s*\n', md), 60, False))

    if not jobs:
        SKIPPED.append('the rendered-against-source check (a .docx is absent)')
        print('   (no .docx and source pair present; skipping)')
        return
    for label, docx, paras, floor, counted in jobs:
        body = norm(docx_text(docx))
        want = [p for p in paras if len(norm(p)) > floor]
        missing = [p for p in want if norm(p) not in body]
        if missing:
            FAIL.append(('%s .docx is behind its source' % label,
                         norm(missing[0])[:70],
                         'rebuild it before submitting'))
            print('   FAIL  %s .docx is missing %d of %d source paragraph(s); rebuild '
                  'it. First: %r' % (label, len(missing), len(want),
                                     norm(missing[0])[:70]))
        elif counted:
            print('   ok   %s .docx carries all %d source paragraphs'
                  % (label, len(want)))
        else:
            _print('   .    %s .docx carries all %d source paragraphs (not counted)'
                   % (label, len(want)))

    # The PDF is produced from the .docx by a SEPARATE LibreOffice conversion, so
    # a current .docx does not imply a current PDF: rebuild the document, forget
    # to reconvert, and the file a journal ingests is a version behind while the
    # check above passes.
    #
    # Comparing against extracted PDF text needs two normalisations, both found
    # the hard way. Justified text hyphenates across lines, so "moderate-
    # resolution" extracts with a space inside it and 15 of 62 paragraphs looked
    # missing; collapsing to lowercase alphanumerics removes that, and word order
    # is still enforced because this stays a substring test on a sequence. Then
    # 10 still looked missing, because pdftotext emits the page number inside any
    # paragraph that spans a page break, so standalone digit lines are dropped
    # first, which is the same filter check_layout.py applies for the same reason.
    import shutil
    import subprocess
    # poppler is not standard on Windows, where IDLE is most used, and its
    # absence used to end the whole run in a raw FileNotFoundError traceback
    # that named 'pdftotext' and nothing about the cause.
    if shutil.which('pdftotext') is None:
        MISSING_TOOLS.append('poppler')
        SKIPPED.append('the PDF-currency check (pdftotext absent; install '
                       'poppler-utils, or poppler for Windows)')
        _print('   .    pdftotext is not installed, so the rendered PDFs were '
               'not checked against their sources')
        return
    squash = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())

    def pdf_text(f):
        raw = subprocess.run(['pdftotext', '-layout', f, '-'],
                             capture_output=True, text=True).stdout
        return '\n'.join(l for l in raw.split('\n') if not l.strip().isdigit())

    for label, docx, paras, floor, counted in jobs:
        pdf = docx[:-5] + '.pdf'
        if not os.path.exists(pdf):
            SKIPPED.append('%s .pdf (rendered-against-source check)' % label)
            print('   (%s absent; skipping)' % pdf)
            continue
        body = squash(pdf_text(pdf))
        want = [p for p in paras if len(squash(p)) > floor]
        missing = [p for p in want if squash(p) not in body]
        if missing:
            FAIL.append(('%s .pdf is behind its source' % label,
                         ' '.join(missing[0].split())[:70],
                         'reconvert it from the .docx'))
            print('   FAIL  %s .pdf is missing %d of %d source paragraph(s); '
                  'reconvert it. First: %r' % (label, len(missing), len(want),
                                               ' '.join(missing[0].split())[:70]))
        else:
            # Never counted, for either document. A failure is still a failure,
            # but counting a success would make the assertion total depend on
            # whether poppler happens to be installed, and the README cannot
            # state a number true on both a Linux CI box and a Windows laptop.
            _print('   .    %s .pdf carries all %d source paragraphs (not counted)'
                   % (label, len(want)))


def manuscript_figures(path='build_manuscript.js'):
    """Which figures the manuscript embeds, read from the manuscript.

    Three checks used to hand-list the same four PNGs. A fifth figure added to
    the paper would have been checked by none of them, silently, which is the
    stale-hand-kept-list failure this package has now hit four times: the README
    file list, the assertion-count list, the cross-file count scan, and this.

    The rule that came out of the third one applies here: if a check names
    files, it should be deriving them. The manuscript is the right authority,
    because the question every one of these checks asks is about the figures
    that appear in the paper, not the files that happen to sit in the folder.
    """
    import os
    import re
    if not os.path.exists(path):
        return []
    src = open(path, encoding='utf-8').read()
    names = re.findall(r"readFileSync\(path\.join\(HERE,\s*'(figure_[\w-]+\.png)'\)\)", src)
    # order-preserving unique
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def figure_title_style():
    """The four figure titles, styled the same way.

    They were not. Sizes ran 9.2, 9.6, 10.0 and 10.2 with no pattern, none was
    bold, and Figure 3's alone was in italic, which read as an aside rather than
    as the figure's claim and was also the smallest of the four. Now all four are
    11.5 pt bold and upright.

    Only the TOP-LEVEL title is checked, located as the fig.text at a y above
    0.94. The italic annotations inside Figure 2, "no imagery of any kind" in
    panel 1 and the footnote beneath, are deliberate and are left alone.

    Figure 2's title is the one that cannot sit on a single line: at 11.5 pt bold
    it measures 8.04 in against a 7.4 in figure, so it carries an explicit
    newline at its own comma. A title with no newline that would overflow is what
    this check cannot see, so the widths were measured in the font the figures
    use, Liberation Serif, rather than assumed.

    The graphical abstract is deliberately excluded. It is sized for a 525 px
    listing thumbnail, not for a 7.2 in page, and its own title is already bold
    at 10.4 pt.
    """
    import os
    import re
    print("\nFIGURES  title styling, uniform across the four")
    figs = manuscript_figures()
    SCRIPTS = ['make_' + f[:-4] + '.py' for f in figs]
    if len(SCRIPTS) < 4:
        FAIL.append(('figure list derivation', '%d figures found' % len(SCRIPTS),
                     'at least the 4 the manuscript embeds'))
        print('   FAIL  only %d figure(s) derived from the manuscript, so this '
              'check would look at almost nothing' % len(SCRIPTS))
        return
    bad = []
    for f in SCRIPTS:
        if not os.path.exists(f):
            SKIPPED.append('%s (figure title styling)' % f)
            print('   (%s absent; skipping)' % f)
            continue
        src = open(f, encoding='utf-8').read()
        # the title is the fig.text whose y sits above 0.94
        call = None
        for m in re.finditer(r'fig\.text\(\s*0\.5\s*,\s*(0\.9[4-9]\d*)', src):
            j = src.find(')\n', m.end())
            call = src[m.start():j + 1]
            break
        if call is None:
            bad.append('%s: no top-level title found' % f)
            continue
        size = re.search(r'fontsize\s*=\s*([\d.]+)', call)
        if not size or abs(float(size.group(1)) - 11.5) > 1e-9:
            bad.append('%s: title is %s pt, not 11.5'
                       % (f, size.group(1) if size else 'unset'))
        if "fontweight='bold'" not in call:
            bad.append('%s: title is not bold' % f)
        if "style='italic'" in call:
            bad.append('%s: title is italic' % f)
    for b in bad:
        FAIL.append(('figure title styling', b, '11.5 pt bold, upright'))
        print('   FAIL  %s' % b)
    if not bad:
        print('   ok   all four figure titles are 11.5 pt bold and upright')


def service_record_count(builder='build_manuscript.js'):
    """The one figure in the paper that nothing can ever recompute.

    Section 2.1 states that the county's ArcGIS REST parcel service carried
    64,401 records on 26 September 2026. It is a live service, so that number is
    not derivable from the released files and no other check in this harness can
    reach it. Three further shipped files state the same count, in three
    different phrasings, because each documents a different stage of the pull.

    Nothing tied the four together. A figure that cannot be recomputed and is
    not cross-checked is the one a reader is most exposed to: they can verify
    every other number in the paper against the data and would still have no way
    to notice that the pipeline note and the manuscript disagreed about the size
    of the layer they were both drawn from. This is the reduced-count defect
    again, in the class of figures where it is permanent rather than merely
    undetected.

    Each anchor must match exactly once. A phrasing that has been reworded is
    reported as stale and fails, rather than passing by matching nothing, which
    is how a check on four files quietly becomes a check on one.
    """
    import os
    import re
    print('\nSECTION 2.1  the live parcel service count, across every file that states it')
    if not os.path.exists(builder):
        MISSING_TOOLS.append('the manuscript builder (service count)')
        _print('   .    %s absent, service count not checked' % builder)
        return
    src = open(builder, encoding='utf-8').read()
    m = re.search(r'carried ([\d,]+) records', src)
    if not m:
        FAIL.append(('service record count', 'not stated in the manuscript',
                     'a count with an access date'))
        print('   FAIL  the manuscript no longer states the service record count')
        return
    canon = m.group(1).replace(',', '')
    print('   ok   the manuscript states the service count with an access date, %s'
          % m.group(1))
    ANCHORS = [
        ('canopy_bias_pipeline.md', r'([\d,]+) polygon features'),
        ('canopy_bias_extraction.js', r'esriGeometryPolygon, ([\d,]+) features'),
        ('stage1_pull_nevada_parcels.js', r'total parcels in layer\s+([\d,]+)'),
    ]
    # Only a file that ships may contribute to the tally. stage1 is the superseded
    # staged-route pull, deliberately not in the package, so it exists in the
    # working tree and not in a reviewer's unzip. Counting its pass made the
    # assertion total differ between the two trees by one, which is the
    # environment-dependence rule this harness already learned twice, arrived at
    # from a third direction. It is still checked here, just not counted.
    shipped = set()
    if os.path.exists('build_package.sh'):
        blk = re.search(r'FILES=\((.*?)\n\)',
                        open('build_package.sh', encoding='utf-8').read(), re.S)
        if blk:
            for line in blk.group(1).split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    shipped.update(line.split())
    for f, pat in ANCHORS:
        say = print if f in shipped else _print
        tail = '' if f in shipped else ' (not shipped, not counted)'
        if not os.path.exists(f):
            MISSING_TOOLS.append('%s (service count)' % f)
            _print('   .    %s absent, not checked' % f)
            continue
        hits = re.findall(pat, open(f, encoding='utf-8').read())
        if len(hits) != 1:
            FAIL.append(('%s service count anchor' % f,
                         'exactly one match', '%d matches' % len(hits),
                         ('expected', 'found')))
            say('   FAIL  %s: the service-count phrasing matched %d times, not once; '
                'this check has gone stale' % (f, len(hits)))
        elif hits[0].replace(',', '') != canon:
            FAIL.append(('%s service count' % f, m.group(1), hits[0],
                         ('manuscript', 'this file')))
            say('   FAIL  %s states %s records; the manuscript states %s'
                % (f, hits[0], m.group(1)))
        else:
            say('   %s   %s states the same service count%s'
                % ('ok' if f in shipped else '. ', f, tail))


def docs_name_only_shipped_files():
    """Does every file the shipped documentation tells the reader to use ship?

    Found the hard way. `canopy_bias_pipeline.md` ships, and its Stage 1 read
    "Run `stage1_pull_nevada_parcels.js`". That script is superseded by
    `run_full_analysis_browser.js` and is deliberately not in the package, so
    step one of the replication instructions named a file the reviewer does not
    have, and the route it described was the dead one. Every number in the paper
    reproduced; the instructions for regenerating the data from source did not
    survive first contact.

    Nothing could have caught it. The forward check asks whether every shipped
    file is documented. This is the other direction: whether everything the
    documentation points at is shipped. A package can pass the first and still
    hand a reviewer a dead end.

    URLs are skipped, since a reference is not a shipped file. A file genuinely
    absent on purpose must be named in DECLARED_ABSENT, so that "not shipped" is
    always a recorded decision rather than an oversight.
    """
    import os
    import re
    print('\nPACKAGE  every file the shipped docs name is in the package')
    if not os.path.exists('build_package.sh'):
        MISSING_TOOLS.append('build_package.sh (reverse docs check)')
        _print('   .    build_package.sh absent, reverse docs check skipped')
        return
    blk = re.search(r'FILES=\((.*?)\n\)',
                    open('build_package.sh', encoding='utf-8').read(), re.S)
    shipped = set()
    if blk:
        for line in blk.group(1).split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                shipped.update(line.split())
    # Deliberately absent, each for a stated reason.
    DECLARED_ABSENT = set()
    ref = re.compile(r'`([\w./-]+\.(?:js|py|R|sh|csv|json|cff|yml|yaml|txt|docx|pdf))`')
    url = re.compile(r'(?:://|\.(?:com|gov|org|net|edu|io)/)')
    scanned, bad = 0, []
    for md in sorted(f for f in shipped if f.endswith('.md')):
        if not os.path.exists(md):
            continue
        for name in sorted(set(ref.findall(open(md, encoding='utf-8').read()))):
            if url.search(name):
                continue
            scanned += 1
            if name not in shipped and name not in DECLARED_ABSENT:
                bad.append('%s names %s' % (md, name))
    if scanned < 10:
        FAIL.append(('reverse docs check', 'at least 10 references',
                     '%d scanned' % scanned, ('expected', 'found')))
        print('   FAIL  only %d file reference(s) found in the shipped docs; '
              'this check is not reaching them' % scanned)
    elif bad:
        FAIL.append(('shipped docs name a file the package does not contain',
                     'every named file shipped', '; '.join(bad),
                     ('expected', 'found')))
        print('   FAIL  %s. Ship it, or declare it absent.' % '; '.join(bad))
    else:
        print('   ok   all %d file references in the %d shipped .md files resolve '
              'inside the package' % (scanned, len([f for f in shipped
                                                    if f.endswith('.md')])))

    scripts_name_only_shipped_scripts(shipped)


def scripts_name_only_shipped_scripts(shipped):
    """The same dead-end check, for the shipped SCRIPTS rather than the docs.

    The check above was written after `canopy_bias_pipeline.md` told a reviewer to
    "Run `stage1_pull_nevada_parcels.js`", a script deliberately not in the package.
    It scans `.md` files. The identical sentence was sitting in
    `canopy_bias_extraction.js`, one file away and out of scope, together with a
    second reference telling the reader to upload a CSV that script produces. Anyone
    who opened the Earth Engine extraction script, which is the obvious file to open
    when the question is what runs in Earth Engine, met a dead end at step one.

    So the scope now includes shipped scripts. Two differences from the docs check:

    * Only SCRIPT names are flagged (.js, .py, .R, .sh). A script naming a data file
      is usually naming something it writes, or an input it explains how to obtain,
      and make_parcel_edge_exact.py deliberately documents an input that is not
      here. Sending a reader to RUN something absent is the failure worth catching.
    * Only comment lines are scanned, because that is where instructions to a reader
      live, and a filename inside code is usually an output path.

    DECLARED_ABSENT records the ones named on purpose, each with a reason, so "not
    shipped" stays a decision rather than becoming a silent exemption.
    """
    import os
    import re
    print('\nPACKAGE  every script the shipped scripts name is in the package')
    DECLARED_ABSENT = {
        # Named as superseded provenance, not as an instruction: signal_check_v3.js
        # opens "Supersedes v1 ... and v2 ...", which is history the package keeps.
        'placer_county_signal_check.js':
            'v1, superseded by signal_check_v3.js, named only as provenance',
        'signal_check_v2_corrected.js':
            'v2, superseded by signal_check_v3.js, named only as provenance',
        # canopy_bias_extraction.js names it only where its header says it is absent
        # and points the reader at run_full_analysis_browser.js instead.
        'stage1_pull_nevada_parcels.js':
            'superseded by run_full_analysis_browser.js; named only where the '
            'header says so and gives the shipped route',
        # Written and deleted by test_harness.py at run time.
        'perturbed_build_manuscript.js':
            'a deliberately broken copy test_harness.py writes and removes',
    }
    SCRIPT = re.compile(r'\b([\w.-]+\.(?:js|py|R|sh))\b')
    COMMENT = re.compile(r'^\s*(?://|#)')
    scanned, bad = 0, []
    files = sorted(f for f in shipped
                   if f.endswith(('.js', '.py', '.R', '.sh')) and os.path.exists(f))
    for src in files:
        for line in open(src, encoding='utf-8', errors='replace').read().split('\n'):
            if not COMMENT.match(line):
                continue
            for name in set(SCRIPT.findall(line)):
                if name == os.path.basename(src):
                    continue
                scanned += 1
                if name not in shipped and name not in DECLARED_ABSENT:
                    bad.append('%s names %s' % (src, name))
    if scanned < 20:
        FAIL.append(('reverse scripts check', 'at least 20 references',
                     '%d scanned' % scanned, ('expected', 'found')))
        print('   FAIL  only %d script reference(s) found in the shipped scripts; '
              'this check is not reaching them' % scanned)
    elif bad:
        FAIL.append(('shipped scripts name a script the package does not contain',
                     'every named script shipped', '; '.join(sorted(set(bad))),
                     ('expected', 'found')))
        print('   FAIL  %s. Ship it, or declare it absent with a reason.'
              % '; '.join(sorted(set(bad))))
    else:
        print('   ok   all %d script references across the %d shipped scripts '
              'resolve, or are declared absent with a reason (%d declared)'
              % (scanned, len(files), len(DECLARED_ABSENT)))


def every_shipped_script_is_attributed():
    """Does each shipped script say who wrote it and what it belongs to?

    None of them did. Not one of the seven Earth Engine scripts, nor the Python or
    the R, carried the author's name, the paper's title, the ORCID, the repository
    or the licence. The attribution lived entirely in README.md, CITATION.cff and
    LICENSE, which is fine for a file read inside the package and useless for one
    that leaves it.

    The Earth Engine scripts leave it by design. They are pasted into a Code Editor
    at code.earthengine.google.com, saved into someone's account, and shared from
    there as a link to a script. Nothing in that path carries the README along. A
    reader who receives one has no way to tell whose work it is, which paper it
    belongs to, or that it is MIT rather than all-rights-reserved, which is the
    default for a file with no licence statement.

    The same is true of any script copied out on its own, so every shipped script
    carries the header, not just the Earth Engine ones.

    Each header is checked against the metadata rather than against a copy of the
    expected text: the author name comes from the manuscript byline, the ORCID from
    the same place the release-metadata check uses, and the repository URL from
    CITATION.cff. A header that drifts from the citation it is supposed to mirror
    fails.
    """
    import os
    import re
    print('\nATTRIBUTION  every shipped script names its author and its paper')
    # .yml is in scope because the CI workflow is an executable file that ships and
    # runs, and the first version of this check missed it purely because its scope
    # was written as a list of script extensions rather than as "files that run".
    # The other ungated shipped files are data or metadata: .gitignore,
    # requirements.txt, CHECKSUMS.sha256 and figure_boundaries.json, which is JSON
    # and cannot carry a comment at all. LICENSE, CITATION.cff and .zenodo.json
    # already name the author because that is what they are for.
    scripts = sorted(f for f in _manifest_files()
                     if f.endswith(('.js', '.py', '.R', '.sh', '.yml'))
                     and os.path.exists(f))
    if len(scripts) < 20:
        FAIL.append(('attribution check', 'at least 20 shipped scripts',
                     '%d found' % len(scripts), ('expected', 'found')))
        print('   FAIL  only %d shipped script(s) found; this check is not reaching '
              'them' % len(scripts))
        return

    want = {}
    if os.path.exists('build_manuscript.js'):
        bm = open('build_manuscript.js', encoding='utf-8').read()
        m = re.search(r"creator:\s*'([^']+)'", bm)
        if m:
            want['the author name'] = m.group(1)
        o = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])', bm)
        if o:
            want['the ORCID'] = o.group(1)
    if os.path.exists('CITATION.cff'):
        rc = re.search(r'^repository-code:\s*"([^"]+)"',
                       open('CITATION.cff', encoding='utf-8').read(), re.M)
        if rc:
            want['the repository URL'] = rc.group(1)
    if len(want) < 3:
        _print('   .    the expected header values could not all be derived, so '
               'attribution was checked only for the author name')
    bad = []
    for f in scripts:
        txt = open(f, encoding='utf-8', errors='replace').read()
        # Only the head of the file counts: an attribution buried at line 400 is
        # not what someone sees when a script is pasted somewhere else.
        head = '\n'.join(txt.split('\n')[:40])
        for label, value in want.items():
            if value not in head:
                bad.append('%s is missing %s' % (f, label))
    if bad:
        FAIL.append(('shipped scripts are unattributed',
                     'every script carries the header', '; '.join(bad[:4]) +
                     ('; and %d more' % (len(bad) - 4) if len(bad) > 4 else ''),
                     ('expected', 'found')))
        print('   FAIL  %s%s' % ('; '.join(bad[:4]),
                                 '; and %d more' % (len(bad) - 4) if len(bad) > 4 else ''))
    else:
        print('   ok   all %d shipped scripts carry the author, the ORCID and the '
              'repository URL in their first 40 lines' % len(scripts))


def shipped_javascript_parses():
    """Does every shipped .js file actually parse?

    Nothing checked. The Earth Engine scripts are the part of this package that
    CANNOT be executed here: they need the Earth Engine runtime and an
    authenticated account, so the harness has never run one, and the only thing it
    asserted about any of them was that canopy_bias_extraction.js quotes the right
    service record count. A stray brace introduced while editing a comment would
    have shipped, and the reader would find out by pasting it into the Code Editor
    and reading a parse error.

    `node --check` parses without executing, which is exactly the right amount:
    it needs no Earth Engine, touches no account, and catches the one class of
    defect that makes a script worthless on arrival. It is not a claim that the
    script RUNS; see the README on what is and is not verified about Earth Engine.

    Skipped, not failed, when node is absent, like the other external-tool checks.
    """
    import os
    import shutil
    import subprocess
    print('\nEARTH ENGINE  every shipped .js parses')
    if not shutil.which('node'):
        MISSING_TOOLS.append('node (JavaScript syntax check)')
        _print('   .    node is not installed, so the .js files were not parsed')
        return
    js = sorted(f for f in _manifest_files()
                if f.endswith('.js') and os.path.exists(f))
    if len(js) < 5:
        FAIL.append(('javascript syntax check', 'at least 5 shipped .js files',
                     '%d found' % len(js), ('expected', 'found')))
        print('   FAIL  only %d shipped .js file(s) found; this check is not '
              'reaching them' % len(js))
        return
    broken = []
    for f in js:
        p = subprocess.run(['node', '--check', f], capture_output=True, text=True)
        if p.returncode != 0:
            # node puts "<absolute path>:<line>" on the first stderr line and the
            # actual SyntaxError several lines down. Reporting the first line gives
            # a truncated path and no diagnosis, so pull the error and pair it with
            # the line number, which is what a reader needs to find the brace.
            err = p.stderr.strip().split('\n')
            msg = next((l.strip() for l in err if 'Error' in l), 'did not parse')
            lineno = ''
            if err and ':' in err[0]:
                tail = err[0].rsplit(':', 1)[-1]
                if tail.isdigit():
                    lineno = ' at line %s' % tail
            broken.append('%s%s: %s' % (f, lineno, msg[:70]))
    if broken:
        FAIL.append(('shipped JavaScript does not parse', 'all parse',
                     '; '.join(broken), ('expected', 'found')))
        print('   FAIL  %s' % '; '.join(broken))
    else:
        print('   ok   all %d shipped .js files parse (syntax only; Earth Engine '
              'scripts cannot be executed here)' % len(js))


def _manifest_files():
    """The shipped-file list, read from the packaging script."""
    import os
    import re
    out = []
    if not os.path.exists('build_package.sh'):
        return out
    blk = re.search(r'FILES=\((.*?)\n\)',
                    open('build_package.sh', encoding='utf-8').read(), re.S)
    if blk:
        for line in blk.group(1).split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                out += line.split()
    return out


def figures_carry_no_provenance_manifest():
    """Do the shipped figures carry an embedded content-credentials manifest?

    They did. Every one of the nine shipped figure images, PNG and TIFF alike,
    carried a C2PA content-credentials manifest: a JUMBF box holding a
    `urn:c2pa:` identifier, 5,770 bytes in the PNGs as a `caBX` chunk. The
    project record described those bytes as "matplotlib's caBX XMP chunk". That
    was wrong twice over. `caBX` is not XMP, it is C2PA, and matplotlib does not
    write it; something in the environment that produced the figures did.

    Two consequences, and the second is the one that matters.

    First, each manifest carries a UUID minted at write time, so those files
    could never have been byte-reproducible. Regenerating them from the shipped
    scripts gives pixel-identical images 5,770 bytes shorter. Any byte-level
    check on a figure would have been permanently unstable, and a reviewer who
    regenerated and ran `cmp` would have found a difference the package never
    explained.

    Second, this is provenance metadata about the tooling, embedded in figures
    bound for a journal and for a public GitHub and Zenodo release. Whether to
    ship it is the author's decision, not a detail. The figures now shipped are
    the regenerated ones, which carry none, and this check holds that state so
    it cannot come back silently from a later run in a different environment.

    To reverse the decision, invert this check; do not simply delete it.
    """
    import os
    print('\nFIGURES  no embedded content-credentials manifest')
    EXT = ('.png', '.tif', '.tiff', '.jpg', '.jpeg')
    # _manifest_files() reads build_package.sh's explicit FILES list, which names
    # matched_parcel_panels as a DIRECTORY. So for a long time this check scanned
    # nine images and reported "none of the 9 shipped images carries a C2PA
    # manifest" while the package shipped fifteen, and all six it could not see
    # carried one: the Earth Engine panel exports Figure 3 is composed from, each
    # holding an "Anthropic Files / Claude" claim generator and the description
    # "Claude provided this file at the request of a user and may have created
    # it". That is a false provenance claim about exports of public NAIP and NLCD
    # imagery, in a package about to be deposited publicly under the author's
    # name, and the check that was supposed to catch it was true of a scope that
    # excluded exactly the files that failed. It walks the directory now, and
    # .jpg is in scope, because two of the six were JPEGs.
    imgs = sorted(f for f in _manifest_files()
                  if f.lower().endswith(EXT) and os.path.exists(f))
    for root, _dirs, files in os.walk('matched_parcel_panels'):
        # figure_panels/ is the duplicate directory build_package.sh excludes.
        if 'figure_panels' in root.split(os.sep):
            continue
        for fn in files:
            if fn.lower().endswith(EXT):
                imgs.append(os.path.join(root, fn))
    imgs = sorted(set(imgs))
    if not imgs:
        FAIL.append(('figure provenance scan', 'at least one shipped image',
                     'none found', ('expected', 'found')))
        print('   FAIL  no shipped images found to scan; this check is vacuous')
        return
    carrying = []
    for f in imgs:
        blob = open(f, 'rb').read()
        if b'jumb' in blob or b'urn:c2pa' in blob or b'caBX' in blob:
            carrying.append(f)
    if carrying:
        FAIL.append(('figures carry a content-credentials manifest',
                     'none', ', '.join(carrying), ('expected', 'found')))
        print('   FAIL  %s %s an embedded C2PA manifest. Regenerate, or invert '
              'this check if shipping it is intended.'
              % (', '.join(carrying), 'carries' if len(carrying) == 1 else 'carry'))
    else:
        print('   ok   none of the %d shipped images carries a C2PA manifest' % len(imgs))


def figure_formats_and_resolution():
    """Every figure in the same three formats, at the dpi its own script asks for.

    WHY THIS EXISTS
    ---------------
    Figures 2 and 4 shipped with a vector PDF and Figures 1 and 3 did not, and the
    stated reason was that 1 and 3 are "photographic raster content, where 300 dpi
    for colour is the journal's requirement". Half of that was false.

    **Figure 1 draws everything except its colourbar.** Saving it as a PDF and counting
    image objects gives exactly one, a 648x39 greyscale colourbar strip; the
    21,931-point scatter, the outline, the inset and all the type are vector. It is
    line or combination art, the class the journal rates at 1200 dpi, and it was
    sitting at 300 with no vector form on the strength of a classification that did
    not describe it. Now 600 dpi with a PDF, matching Figures 2 and 4.

    **Figure 3 really is photographic, and 300 dpi is its ceiling rather than a
    concession.** Its grid spans (0.985 - 0.075) x 7.2 = 6.552 in across three
    panels at wspace=0.055, so each panel prints 2.107 in wide, and the Earth
    Engine exports behind them are 633 px. 633 / 2.1068 = 300.5 dpi. A 300 dpi
    save renders each panel at 632 px, within one pixel of its input. A 600 dpi
    save would render 1264 px from a 633 px source: twice the bytes, no new detail.

    So the two figures differ in dpi for a measured reason, not an arbitrary one,
    and this check holds both halves: the FORMAT SET must be uniform across all
    four, while the dpi may differ and must match what each script requests.

    Reading the requested dpi out of each script rather than hard-coding it here is
    the point. A script edited to 1200 without its TIFF being regenerated fails,
    and so does a TIFF regenerated by something other than its script.
    """
    import os
    import re
    print('\nFIGURE FORMATS  the same three for every figure, at each script\'s dpi')
    figs = manuscript_figures()
    if len(figs) != 4:
        FAIL.append(('figure format audit', '%d figures' % len(figs), '4',
                     ('found', 'expected')))
        print('   FAIL  expected four manuscript figures, found %d' % len(figs))
        return

    EXPECT = ('.png', '.tif', '.pdf')
    missing, bases = [], []
    for f in figs:
        base = os.path.splitext(f)[0]
        bases.append(base)
        for ext in EXPECT:
            if not os.path.exists(base + ext):
                missing.append(base + ext)
    if missing:
        FAIL.append(('figures do not all ship the same formats',
                     ', '.join(missing), 'png, tif and pdf for each of the four',
                     ('absent', 'expected')))
        print('   FAIL  %d figure file(s) absent, so the format set is not '
              'uniform: %s' % (len(missing), ', '.join(missing)))
    else:
        print('   ok   all %d figures ship .png, .tif and .pdf, the same three '
              'each' % len(figs))

    # The dpi each script asks for, read from its own `DPI = N` assignment, against
    # the dpi tag in the TIFF and the PNG it produced.
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    for base in bases:
        script = 'make_' + base + '.py'
        if not os.path.exists(script):
            continue
        m = re.search(r'^DPI = (\d+)$', open(script, encoding='utf-8').read(),
                      re.M)
        if not m:
            FAIL.append(('%s states no DPI constant' % script, 'none',
                         'a single `DPI = N` line the outputs are saved at',
                         ('found', 'expected')))
            print('   FAIL  %s has no `DPI = N` line, so the dpi its outputs '
                  'carry cannot be checked against what it asks for' % script)
            continue
        want = int(m.group(1))
        for ext in ('.tif', '.png'):
            f = base + ext
            if not os.path.exists(f):
                continue
            got = Image.open(f).info.get('dpi', (None,))[0]
            if got is None or abs(got - want) > 0.5:
                FAIL.append(('%s dpi' % f, got, want, ('the file', script)))
                print('   FAIL  %s is tagged %s dpi; %s saves at %d. Regenerate.'
                      % (f, got, script, want))
        print('   ok   %-26s %d dpi in the script and in both rasters'
              % (base, want))

    # What each PDF actually is. Not a pass or fail: a uniform format set does not
    # make the PDFs equivalent, and a reader choosing what to send needs to know
    # which ones are vector. Reported so the distinction cannot quietly disappear
    # now that every figure has one.
    for base in bases:
        f = base + '.pdf'
        if not os.path.exists(f):
            continue
        b = open(f, 'rb').read()
        # Count image OBJECTS, requiring the object to close after the Image
        # declaration. Matching /Subtype /Image alone double-counts: each image
        # with transparency carries an /SMask that is itself an image object, so a
        # looser pattern reported 2 for Figure 1 and 8 for Figure 3 where the real
        # figures are 1 and 6.
        n = len(re.findall(
            rb'\d+ 0 obj(?:.{0,700}?)/Subtype\s*/Image(?:.{0,700}?)(?:stream|endobj)',
            b, re.S))
        _print('   .    %-26s pdf carries %d embedded raster image object(s)%s'
               % (base, n, '' if n else ', fully vector'))


def shipped_tiffs_are_well_formed():
    """Are the shipped TIFFs structurally sound, not merely readable by Pillow?

    WHY THIS EXISTS
    ---------------
    strip_provenance.py's first TIFF path blanked the C2PA tag in place: it rewrote
    the IFD entry as tag 0 and zeroed the payload, so the file kept its length and
    no offset moved. It looked right. Pillow read the files, the colour checks
    passed against the PNGs, the C2PA byte scan came up clean, and the figures were
    about to ship.

    They were malformed. TIFF6 requires IFD entries to be sorted in ASCENDING TAG
    ORDER, and blanking the last entry to tag 0 leaves a directory ending below
    every tag before it. Worse, each strip-then-recontaminate cycle added another
    dead entry: the shipped TIFFs had accumulated two apiece. Pillow is lenient and
    never complained. A stricter reader in a publisher's production workflow has no
    obligation to be, and a figure that fails at the far end of that process is the
    worst place to discover it.

    So this reads each shipped TIFF's directory itself rather than asking whether a
    library can open it:

      * entries sorted ascending, which is the rule that was broken;
      * no tag 0, which is the residue the old method left;
      * no C2PA tag 52545, which is the tag the whole exercise is about;
      * every offset inside the file, which catches a botched splice.

    "Pillow opened it" is not the question. Pillow opened the broken ones.
    """
    import os
    import struct
    print('\nTIFF  the shipped TIFF directories are well formed')
    SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4,
             12: 8}
    tiffs = sorted(f for f in _manifest_files()
                   if f.lower().endswith(('.tif', '.tiff')) and os.path.exists(f))
    if len(tiffs) < 4:
        FAIL.append(('tiff structure check', 'at least 4 shipped TIFFs',
                     '%d found' % len(tiffs), ('expected', 'found')))
        print('   FAIL  only %d shipped TIFF(s) found; this check is not reaching '
              'them' % len(tiffs))
        return
    bad = []
    for f in tiffs:
        b = open(f, 'rb').read()
        if b[:2] not in (b'II', b'MM'):
            bad.append('%s is not a TIFF' % f)
            continue
        e = '<' if b[:2] == b'II' else '>'
        try:
            off = struct.unpack(e + 'I', b[4:8])[0]
            n = struct.unpack(e + 'H', b[off:off + 2])[0]
            tags = []
            for i in range(n):
                p = off + 2 + i * 12
                tag, typ, cnt = struct.unpack(e + 'HHI', b[p:p + 8])
                val = struct.unpack(e + 'I', b[p + 8:p + 12])[0]
                tags.append(tag)
                if SIZES.get(typ, 1) * cnt > 4 and val + SIZES.get(typ, 1) * cnt > len(b):
                    bad.append('%s tag %d points past the end of the file' % (f, tag))
        except Exception as exc:                           # noqa: BLE001
            bad.append('%s directory could not be read (%s)' % (f, exc))
            continue
        if tags != sorted(tags):
            bad.append('%s IFD tags are not in ascending order, which TIFF6 '
                       'requires' % f)
        if 0 in tags:
            bad.append('%s carries %d dead tag-0 entr%s' %
                       (f, tags.count(0), 'y' if tags.count(0) == 1 else 'ies'))
        if 52545 in tags:
            bad.append('%s still carries C2PA tag 52545' % f)
    if bad:
        FAIL.append(('shipped TIFFs are malformed', 'well formed',
                     '; '.join(bad), ('expected', 'found')))
        print('   FAIL  %s' % '; '.join(bad))
    else:
        print('   ok   all %d shipped TIFF directories are ascending, free of dead '
              'entries and of tag 52545, with every offset inside the file'
              % len(tiffs))


def graphical_abstract_meets_journal_spec():
    """The graphical abstract against the journal's own four rules for one.

    The rules, quoted from the Instructions for Authors PDF the author supplied,
    updated 14 September 2026, item 3 of "Checklist: What to Include":

        "Graphical abstract (optional). ... It should be a maximum width of 525
        pixels. If your image is narrower than 525 pixels, please place it on a
        white background 525 pixels wide to ensure the dimensions are maintained.
        Save the graphical abstract as a .jpg, .png, or .tif. Please do not embed
        it in the manuscript file but save it as a separate file, labelled
        GraphicalAbstract1."

    Four rules, and each was prose in a checklist until now, which is how a
    reasonable question gets answered from memory instead of from the source.

    TWO THINGS THIS ENCODES THAT ARE EASY TO GET BACKWARDS
    ------------------------------------------------------
    **The permitted formats are .jpg, .png and .tif. PDF is not one of them.**
    The instinct to supply a vector PDF comes from Figures 2 and 4, which have
    one, and it does not transfer. A figure is governed by a DPI rule (1200 line
    art, 600 grayscale, 300 colour) where the vector form sidesteps a
    classification argument. The graphical abstract is governed by a PIXEL-WIDTH
    rule, because it is a listing thumbnail rather than print artwork, and a
    vector PDF has no pixel width to satisfy it with.

    **The width rule is an equality here, not an inequality.** 525 px is a
    maximum, but anything narrower must be padded onto a 525 px white background,
    so a compliant file is 525 px wide either way. This asserts equality and says
    so, rather than passing anything under the cap.

    A .tif would be permitted. It is not supplied, because .png is on the same
    list, is lossless, is what the abstract was designed at, and the guidelines
    say to label the file GraphicalAbstract1, singular. Two files under that name
    would leave a production editor guessing which is the graphical abstract.
    """
    import os
    print('\nGRAPHICAL ABSTRACT  the journal\'s four rules for one')
    PERMITTED = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
    WIDTH = 525
    found = [f for f in os.listdir('.')
             if os.path.splitext(f)[0] == 'GraphicalAbstract1'
             and os.path.splitext(f)[1].lower() in PERMITTED]

    # Rule 4, the filename, and the format rule in one: a file named
    # GraphicalAbstract1 with a permitted extension has to exist.
    check_str('the graphical abstract is named and formatted as required',
              ', '.join(sorted(found)), 'GraphicalAbstract1.png')

    # A file under that stem with a format the guidelines do not list would be
    # sent to the journal as a graphical abstract in a format it did not ask for.
    # .pdf is the one to expect here, so name it in the message.
    wrong = sorted(f for f in os.listdir('.')
                   if os.path.splitext(f)[0] == 'GraphicalAbstract1'
                   and os.path.splitext(f)[1].lower() not in PERMITTED)
    if wrong:
        FAIL.append(('graphical abstract format', ', '.join(wrong),
                     'only .jpg, .png or .tif are permitted',
                     ('found', 'the guidelines allow')))
        print('   FAIL  %s: the guidelines permit .jpg, .png or .tif only, so a '
              '.pdf or .eps under this name would be sent in a format the journal '
              'did not ask for' % ', '.join(wrong))
    else:
        print('   ok   no GraphicalAbstract1 file in a format the guidelines exclude')

    if not found:
        return
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(sorted(found)[0])
    # Rule 1 and 2 together. See the docstring: narrower than 525 must be padded
    # to 525, so compliance is equality. Written out rather than passed to
    # check(), whose "manuscript N computed N" framing is for a quoted value and
    # reads wrongly for a file property.
    if im.width == WIDTH:
        print('   ok   the graphical abstract is %d px wide, the permitted '
              'maximum, and %d px high' % (im.width, im.height))
    else:
        FAIL.append(('graphical abstract width', im.width, WIDTH,
                     ('the file', 'the guidelines')))
        print('   FAIL  the graphical abstract is %d px wide. The maximum is %d, '
              'and anything narrower must be padded onto a %d px white '
              'background, so a compliant file is exactly %d.'
              % (im.width, WIDTH, WIDTH, WIDTH))

    # Rule 3, the half of it that says do not embed. The manuscript embeds four
    # figures and the harness already checks those four against their files; this
    # asserts the graphical abstract is not a fifth.
    ms = 'canopy_bias_manuscript_GIScienceRS.docx'
    if os.path.exists(ms):
        import zipfile
        ga = open(sorted(found)[0], 'rb').read()
        with zipfile.ZipFile(ms) as z:
            embedded = [n for n in z.namelist() if n.startswith('word/media/')]
            hit = [n for n in embedded if z.read(n) == ga]
        if hit:
            FAIL.append(('graphical abstract embedded in the manuscript',
                         ', '.join(hit), 'not embedded; submit it separately',
                         ('found at', 'the guidelines require')))
            print('   FAIL  the graphical abstract is embedded in the manuscript '
                  'at %s; the guidelines say to submit it as a separate file'
                  % ', '.join(hit))
        else:
            print('   ok   the graphical abstract is not embedded in the '
                  'manuscript, which the guidelines require (%d images checked)'
                  % len(embedded))


def ci_covers_every_shipped_script():
    """Does the CI workflow actually run everything the package ships?

    The workflow names five figure scripts and five verification steps, as a
    hand-kept list. It matched the manifest when written, and nothing held it
    there. Add a sixth figure script and CI silently stops regenerating it while
    the step keeps its name, "Figures regenerate identically", which is then a
    claim about five of six. This harness has been bitten by a hand-kept list
    three times; this is the one place a hand-kept list survived.

    Exemptions are declared with a reason, so a script outside CI is a recorded
    decision rather than an omission.
    """
    import os
    print('\nCI  the workflow runs every shipped figure and verification script')
    wf = os.path.join('.github', 'workflows', 'verify.yml')
    if not os.path.exists(wf):
        FAIL.append(('CI workflow', 'present', 'missing', ('expected', 'found')))
        print('   FAIL  %s is missing' % wf)
        return
    body = open(wf, encoding='utf-8').read()
    EXEMPT = {
        # Its five steps are each run individually above, so running it too would
        # double the longest job for no new coverage. It is exercised instead by
        # the clean-unzip check before every release.
        'run_all.py',
        # Earth Engine Code Editor script. It needs the Earth Engine client and
        # an authenticated session, so no CI runner can execute it, with or
        # without Node.
        'verify_support.js',
    }
    shipped = _manifest_files()
    groups = [
        ('figure scripts',
         [f for f in shipped if f.startswith(('make_figure_', 'make_graphical'))]),
        ('verification scripts',
         [f for f in shipped
          if f.startswith(('check_', 'test_', 'verify_', 'run_all'))
          or f == 'make_tables.py']),
    ]
    for label, members in groups:
        members = sorted(set(members))
        if not members:
            FAIL.append(('CI coverage, %s' % label, 'at least one', 'none found',
                         ('expected', 'found')))
            print('   FAIL  no %s found in the manifest; this check is vacuous' % label)
            continue
        missing = [f for f in members if f not in EXEMPT and f not in body]
        if missing:
            FAIL.append(('CI does not run every shipped %s' % label,
                         'all of them', ', '.join(missing), ('expected', 'missing')))
            print('   FAIL  the workflow never runs %s. Add it, or exempt it with a '
                  'reason.' % ', '.join(missing))
        else:
            print('   ok   all %d shipped %s run in CI (%d exempted with a reason)'
                  % (len(members), label,
                     len([f for f in members if f in EXEMPT])))


def release_metadata_agrees_with_the_manuscript():
    """Author identity is stated in three files and was verified in one.

    The manuscript carries the ORCID and the corresponding-author email, and
    `author_identifiers()` pins those. `CITATION.cff` and `.zenodo.json` carry
    the same identity independently, and nothing compared them to anything.

    That asymmetry is worse than an ordinary cross-file drift, because of where
    those two files go. `CITATION.cff` is what GitHub's "Cite this repository"
    widget reads, and `.zenodo.json` is what the deposit is built from. A wrong
    ORCID or a stale affiliation in either does not sit in a working file waiting
    to be noticed: it is published, attached to a DOI, and harvested. Correcting
    an ORCID in the manuscript during revision while these two keep the old one
    is an ordinary thing to do and nothing here would have said so.

    Checked against the manuscript, which is the authority: the ORCID digits,
    the surname, the email, and the affiliation stem. The manuscript byline
    carries a city and country that release metadata conventionally omits, so
    the affiliation is compared on the department-and-institution stem rather
    than on the whole string.
    """
    import json
    import os
    import re
    print('\nRELEASE METADATA  CITATION.cff and .zenodo.json against the manuscript')
    src = open('build_manuscript.js', encoding='utf-8').read() \
        if os.path.exists('build_manuscript.js') else ''
    if not src:
        MISSING_TOOLS.append('the manuscript builder (release metadata)')
        _print('   .    build_manuscript.js absent, release metadata not checked')
        return
    orc = re.search(r'0000-000[\dX]-\d{4}-\d{3}[\dX]', src)
    mail = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', src)
    stem = re.search(r'(Department of [^\',]+, [A-Za-z ]*University)', src)
    if not (orc and mail and stem):
        FAIL.append(('manuscript identity', 'ORCID, email and affiliation',
                     'one or more absent', ('expected', 'found')))
        print('   FAIL  the manuscript no longer states an ORCID, an email and an '
              'affiliation, so there is nothing to check the release files against')
        return
    want = {'orcid': orc.group(0), 'email': mail.group(0), 'affiliation': stem.group(1)}
    print('   ok   the manuscript states one ORCID, one email and one affiliation')

    if os.path.exists('CITATION.cff'):
        cff = open('CITATION.cff', encoding='utf-8').read()
        # Minimal CFF conformance, without adding a dependency. The file was also
        # validated against the CFF 1.2.0 schema with cffconvert 2.0.0 on
        # 29 September 2026; that tool is not a package dependency, so what ships
        # is this field check, which is what a reviewer without it can run.
        bad = [k for k, pat in (
            ('cff-version', r'(?m)^cff-version:\s*1\.2\.0'),
            ('message', r'(?m)^message:\s*\S'),
            ('title', r'(?m)^title:\s*\S'),
            ('authors', r'(?m)^authors:'),
            ('family-names', r'family-names:\s*\S'),
            ('given-names', r'given-names:\s*\S'),
        ) if not re.search(pat, cff)]
        if bad:
            FAIL.append(('CITATION.cff required fields', 'all present',
                         ', '.join(bad), ('expected', 'missing')))
            print('   FAIL  CITATION.cff is missing %s, so GitHub will not render a '
                  'citation' % ', '.join(bad))
        else:
            print('   ok   CITATION.cff carries every field CFF 1.2.0 requires')
        for label, value in want.items():
            if value in cff:
                print('   ok   CITATION.cff carries the manuscript %s' % label)
            else:
                FAIL.append(('CITATION.cff %s' % label, value, 'absent or different',
                             ('manuscript', 'this file')))
                print('   FAIL  CITATION.cff does not carry the manuscript %s (%s)'
                      % (label, value))
    else:
        FAIL.append(('CITATION.cff', 'present', 'missing', ('expected', 'found')))
        print('   FAIL  CITATION.cff is missing')

    if os.path.exists('.zenodo.json'):
        try:
            zj = json.dumps(json.load(open('.zenodo.json', encoding='utf-8')))
        except ValueError as exc:
            FAIL.append(('.zenodo.json', 'valid JSON', str(exc)[:60],
                         ('expected', 'found')))
            print('   FAIL  .zenodo.json is not valid JSON, so the deposit metadata '
                  'will be empty: %s' % exc)
            return
        # The affiliation is compared on the stem; the email is not in Zenodo's
        # creator schema, so it is not expected there.
        for label in ('orcid', 'affiliation'):
            if want[label] in zj:
                print('   ok   .zenodo.json carries the manuscript %s' % label)
            else:
                FAIL.append(('.zenodo.json %s' % label, want[label],
                             'absent or different', ('manuscript', 'this file')))
                print('   FAIL  .zenodo.json does not carry the manuscript %s (%s)'
                      % (label, want[label]))
    else:
        FAIL.append(('.zenodo.json', 'present', 'missing', ('expected', 'found')))
        print('   FAIL  .zenodo.json is missing')

    citation_is_complete_and_not_overclaiming()


def citation_is_complete_and_not_overclaiming():
    """Does the repository cite the paper, and does it avoid claiming publication?

    `CITATION.cff` said "please cite the paper" and then gave no paper. What
    GitHub's "Cite this repository" widget rendered was the repository entry, with
    no year in it, because `date-released` was absent: a title and a URL, which is
    not something a reader can put in a reference list. Both are fixed; this holds
    them fixed.

    THE PART THAT MATTERS MOST IS THE OVERCLAIM GUARD. A `preferred-citation` with
    `type: article` and a `journal:` key renders, in that widget and in every
    harvester downstream of it, a formatted citation asserting the paper is
    published in that journal. The paper has not been submitted. Writing the venue
    into `journal:` at preparation time and forgetting to revisit it is the obvious
    way to publish a false citation from a file nobody rereads, so the two states
    are held against each other here:

        placeholder DOI still in the manuscript  ->  entry must be `unpublished`
        placeholder gone, article DOI in place   ->  entry must not be `unpublished`

    That second direction is the one that earns this check. When the paper is
    accepted, the harness stops passing until the citation is updated, rather than
    leaving a repository that describes an accepted paper as unpublished forever.
    """
    import datetime
    import json
    import os
    import re
    print('\nCITATION  the repository cites the paper, and claims no more than is true')

    if not os.path.exists('CITATION.cff'):
        FAIL.append(('CITATION.cff', 'present', 'missing', ('expected', 'found')))
        print('   FAIL  CITATION.cff is missing')
        return
    cff = open('CITATION.cff', encoding='utf-8').read()
    # Comment lines are stripped: this file documents the acceptance-time change in
    # prose that names `journal:` and `type: article`, and a naive scan would read
    # its own instructions as the current state.
    live = '\n'.join(l for l in cff.split('\n') if not l.lstrip().startswith('#'))

    # WHICH ENTRY THE WIDGET RENDERS, AND WHETHER IT IS HONEST
    #
    # GitHub renders `preferred-citation` INSTEAD OF the top-level entry when one
    # exists. While the paper is unpublished it has no DOI and no URL, so a
    # preferred-citation would make the "Cite this repository" button show a
    # citation with nothing a reader can resolve, and would hide the Zenodo DOI,
    # which lives on the top-level entry. So the paper's entry stays commented out
    # until the paper is published, and the button shows the repository.
    #
    # THE EARLIER VERSION OF THIS CHECK WAS A TRAP, and the trap would have sprung
    # on the author's first real action. It inferred "the paper is published" from
    # the absence of the Zenodo DOI placeholder in the manuscript, and demanded a
    # preferred-citation with a journal and an article DOI the moment that
    # placeholder was filled. But filling that placeholder is step one of
    # DEPOSITING, months before any acceptance: the two events are unrelated, and a
    # check cannot tell them apart from inside the package. Simulating the deposit
    # is what surfaced it, which is the argument for simulating a process before
    # writing instructions for it.
    #
    # So publication is no longer inferred from anything. The rule is about the
    # entry's CONTENT: whenever a preferred-citation exists it must be a complete,
    # honest citation of a published paper, because that is the only state in which
    # having one is right. Its absence is reported, never failed.
    has_pref = 'preferred-citation:' in live
    if not has_pref:
        _print('   .    no preferred-citation, so the Cite button shows the '
               'resolvable repository entry. Restore the commented block in '
               'CITATION.cff when the paper is published (not counted)')
    else:
        pc = live.split('preferred-citation:', 1)[1]
        problems = []
        if re.search(r'^\s+type:\s*unpublished\s*$', pc, re.M):
            problems.append('it is marked unpublished, so it should not be here at '
                            'all yet')
        for key, what in (('journal:', 'the journal'), ('doi:', 'the article DOI')):
            if not re.search(r'^\s+%s' % key, pc, re.M):
                problems.append('it does not give %s' % what)
        if problems:
            FAIL.append(('CITATION.cff preferred-citation is not a published paper',
                         '; '.join(problems),
                         'type article, with the journal and the article DOI',
                         ('this file', 'expected')))
            print('   FAIL  preferred-citation is present, which tells GitHub to '
                  'show the paper instead of the repository, but %s'
                  % '; and '.join(problems))
        else:
            print('   ok   preferred-citation names a published paper with its '
                  'journal and article DOI, so the Cite button should show it')

    # 2. The top-level entry has to be worth rendering, since it is what the widget
    #    shows while the paper is unpublished: a version and something resolvable.
    for key, why in (('repository-code:', 'the widget would show no link at all'),
                     ('version:', 'the citation would not say which release')):
        if re.search(r'^%s' % key, live, re.M):
            print('   ok   CITATION.cff carries %s' % key.rstrip(':'))
        else:
            FAIL.append(('CITATION.cff %s' % key.rstrip(':'), 'absent',
                         'present, because %s' % why, ('found', 'expected')))
            print('   FAIL  CITATION.cff has no %s, so %s' % (key.rstrip(':'), why))

    # 4. The venue is named somewhere, and spelled as the cover letter spells it.
    VENUE = 'GIScience & Remote Sensing'
    if VENUE in live:
        print('   ok   the citation names the venue, %r' % VENUE)
    else:
        FAIL.append(('CITATION.cff venue', 'not named', VENUE,
                     ('this file', 'expected')))
        print('   FAIL  CITATION.cff does not name %r anywhere' % VENUE)
    # .zenodo.json ships and is counted. COVER_LETTER.md does NOT ship, so it is
    # reported through _print and never counted. Counting it put the total at 522 in
    # the working tree and 522 from a clean unzip: the tree-dependent-total defect
    # this project has now hit four times, a check on a file that is present where
    # the work happens and absent where the package is verified. The cover-letter
    # checks further down avoid it the same way, and this one was written without
    # looking at them.
    if os.path.exists('.zenodo.json'):
        if VENUE in open('.zenodo.json', encoding='utf-8').read():
            print('   ok   .zenodo.json      names the venue the same way')
        else:
            FAIL.append(('.zenodo.json venue', 'not named', VENUE,
                         ('this file', 'expected')))
            print('   FAIL  .zenodo.json does not name the venue as %r' % VENUE)
    if os.path.exists('COVER_LETTER.md'):
        if VENUE in open('COVER_LETTER.md', encoding='utf-8').read():
            _print('   .    COVER_LETTER.md names the venue the same way '
                   '(not counted, it does not ship)')
        else:
            _print('   FAIL  COVER_LETTER.md does not name the venue as %r' % VENUE)

    # 5. The repository URL, which is what the widget renders as the citation's
    #    locator until the DOI exists.
    rc = re.search(r'^repository-code:\s*"([^"]+)"', live, re.M)
    if rc and rc.group(1).startswith('https://github.com/'):
        print('   ok   CITATION.cff carries repository-code, %s' % rc.group(1))
    else:
        FAIL.append(('CITATION.cff repository-code',
                     rc.group(1) if rc else 'absent', 'the GitHub URL',
                     ('this file', 'expected')))
        print('   FAIL  CITATION.cff has no usable repository-code')

    # 6. The author's full name, in EVERY author block, against the manuscript
    #    byline. The byline is the authority.
    #
    #    This used to scan each file's whole text for the two name strings, which
    #    passed on a file whose PAPER citation block had been truncated to "Devan"
    #    while the top-level block still read "Devan Cantrell". The paper block is
    #    the one a reader copies, so the weaker form checked the wrong thing and
    #    said so reassuringly. Each block is now checked on its own.
    byline = None
    if os.path.exists('build_manuscript.js'):
        bm = open('build_manuscript.js', encoding='utf-8').read()
        mb = re.search(r"creator:\s*'([^']+)'", bm)
        if mb:
            byline = mb.group(1)
    if not byline:
        _print('   .    the manuscript byline could not be read, so the author '
               'name was not checked')
    else:
        parts = byline.split()
        want_family, want_given = parts[-1], ' '.join(parts[:-1])
        if os.path.exists('CITATION.cff'):
            cff_txt = open('CITATION.cff', encoding='utf-8').read()
            blocks = re.findall(
                r'family-names:\s*"([^"]+)"\s*\n\s*given-names:\s*"([^"]+)"',
                cff_txt)
            if not blocks:
                FAIL.append(('CITATION.cff author blocks', 'none readable',
                             'family-names followed by given-names',
                             ('found', 'expected')))
                print('   FAIL  no author block in CITATION.cff could be read')
            else:
                wrong = ['%s, %s' % (f, g) for f, g in blocks
                         if f != want_family or g != want_given]
                if wrong:
                    FAIL.append(('CITATION.cff author name', '; '.join(wrong),
                                 '%s, %s' % (want_family, want_given),
                                 ('this file', 'the manuscript byline')))
                    print('   FAIL  %d of %d author block(s) in CITATION.cff give '
                          'the name as %s; the manuscript byline is %r'
                          % (len(wrong), len(blocks), '; '.join(wrong), byline))
                else:
                    print('   ok   all %d author block(s) in CITATION.cff give the '
                          'full name, %s, %s' % (len(blocks), want_family, want_given))
        if os.path.exists('.zenodo.json'):
            creators = json.load(open('.zenodo.json', encoding='utf-8')).get(
                'creators', [])
            want_z = '%s, %s' % (want_family, want_given)
            wrong = [c.get('name', '') for c in creators if c.get('name') != want_z]
            if not creators:
                FAIL.append(('.zenodo.json creators', 'none', 'at least one',
                             ('found', 'expected')))
                print('   FAIL  .zenodo.json lists no creators')
            elif wrong:
                FAIL.append(('.zenodo.json author name', '; '.join(wrong), want_z,
                             ('this file', 'the manuscript byline')))
                print('   FAIL  .zenodo.json gives the creator as %s; expected %r'
                      % ('; '.join(wrong), want_z))
            else:
                print('   ok   .zenodo.json gives the full name, %s' % want_z)

    if os.path.exists('.zenodo.json'):
        zj = json.load(open('.zenodo.json', encoding='utf-8'))
        for k in ('version', 'publication_date'):
            if zj.get(k):
                print('   ok   .zenodo.json carries %s, %s' % (k, zj[k]))
            else:
                FAIL.append(('.zenodo.json %s' % k, 'absent', 'set at deposit',
                             ('found', 'expected')))
                print('   FAIL  .zenodo.json has no %s' % k)
        v = re.search(r'^version:\s*"([^"]+)"', live, re.M)
        if v and zj.get('version') and v.group(1) != zj['version']:
            FAIL.append(('version disagrees', v.group(1), zj['version'],
                         ('CITATION.cff', '.zenodo.json')))
            print('   FAIL  CITATION.cff says version %s; .zenodo.json says %s'
                  % (v.group(1), zj['version']))
        elif v:
            print('   ok   both metadata files agree on version %s' % v.group(1))


def gitignore_excludes_nothing_shipped():
    """Could `git add .` silently drop a file the package ships?

    `.gitignore` and the shipped-file manifest are maintained separately and had
    never been compared. A pattern that happens to match a shipped file makes
    `git add .` skip it without a word, and the pushed repository is then missing
    something the zip contains. Nothing downstream notices: CI checks out the
    repository, so it verifies whatever survived, and every check passes on a
    package that is quietly incomplete.

    The present `.gitignore` is correct. This holds it correct, because the
    failure is silent and the pattern that would cause it is an ordinary thing to
    add: `*.png` to keep a scratch plot out, and the figures leave the repository.
    """
    import fnmatch
    import os
    print('\nGIT  .gitignore excludes nothing the package ships')
    if not os.path.exists('.gitignore'):
        FAIL.append(('.gitignore', 'present', 'missing', ('expected', 'found')))
        print('   FAIL  .gitignore is missing')
        return
    pats = [l.strip() for l in open('.gitignore', encoding='utf-8')
            if l.strip() and not l.strip().startswith('#')]
    shipped = sorted(set(_manifest_files()))
    if not pats or not shipped:
        FAIL.append(('gitignore cross-check', 'patterns and a manifest',
                     '%d patterns, %d shipped files' % (len(pats), len(shipped)),
                     ('expected', 'found')))
        print('   FAIL  nothing to compare, so this check is vacuous')
        return
    clashes = []
    for f in shipped:
        for pat in pats:
            if pat.startswith('!'):
                continue
            base = pat.rstrip('/')
            segs = f.split('/')
            if (fnmatch.fnmatch(f, base) or fnmatch.fnmatch(segs[-1], base)
                    or any(fnmatch.fnmatch(s, base) for s in segs)):
                clashes.append('%s by %r' % (f, pat))
    if clashes:
        FAIL.append(('.gitignore excludes shipped files', 'none',
                     '; '.join(clashes), ('expected', 'found')))
        print('   FAIL  git would not track %s. Narrow the pattern or negate it '
              'with a ! line.' % '; '.join(clashes))
    else:
        print('   ok   none of the %d shipped files matches any of the %d '
              '.gitignore patterns' % (len(shipped), len(pats)))


def repository_metadata():
    """The files a public release needs, which this package had none of.

    The package shipped 50 files of substance and no LICENSE, CITATION.cff,
    .gitignore or requirements.txt. That is fine for a zip attached to a
    submission and not fine for a GitHub repository feeding a Zenodo deposit,
    where an unlicensed repository is all rights reserved by default and Zenodo
    will not take a deposit without a licence.

    The licence itself is deliberately NOT written here. It is the author's
    choice, it has consequences this harness cannot weigh, and a guessed licence
    on someone else's research code is worse than an absent one. What is checked
    is that the decision is recorded and that the three places a licence has to
    appear stay consistent with each other once it is made.
    """
    import os
    import re
    print("\nREPOSITORY  the metadata a public release needs")
    for f, why in (('requirements.txt', 'pinned dependencies'),
                   ('CITATION.cff', 'citation metadata'),
                   ('.gitignore', 'a clean repository'),
                   ('CHECKSUMS.sha256', 'the released data, hashed'),
                   ('.github/workflows/verify.yml', 'the gates run on every push'),
                   ('LICENSE_DECISION.md', 'the licence decision, recorded')):
        if os.path.exists(f):
            print('   ok   %s is present (%s)' % (f, why))
        else:
            FAIL.append(('repository metadata', '%s absent' % f, why))
            print('   FAIL  %s is absent (%s)' % (f, why))

    # The released data, against a known-good hash of itself.
    #
    # Every other check reads the CSV and tests it against the paper's
    # definitions, so a file that was edited or corrupted in a way that still
    # satisfies those definitions would pass. The manuscript's numbers are
    # asserted against this data, not the other way round, so the data being
    # what it was is the assumption underneath all 522 assertions and it was the
    # one thing nothing verified.
    if os.path.exists('CHECKSUMS.sha256'):
        import hashlib
        bad, missing, n = [], [], 0
        for line in open('CHECKSUMS.sha256', encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            want, _, f = line.partition('  ')
            if not os.path.exists(f):
                missing.append(f)
                continue
            n += 1
            got = hashlib.sha256(open(f, 'rb').read()).hexdigest()
            if got != want:
                bad.append(f)
        if bad:
            FAIL.append(('released data does not match its checksum',
                         ', '.join(bad), 'the hash in CHECKSUMS.sha256'))
            print('   FAIL  %d released file(s) do not match their recorded hash: %s'
                  % (len(bad), ', '.join(bad)))
            print('         Do not update the hash. Find out why the file changed.')
        elif missing:
            FAIL.append(('CHECKSUMS.sha256 lists absent files', ', '.join(missing),
                         'every listed file shipped'))
            print('   FAIL  CHECKSUMS.sha256 lists %d file(s) that are not here: %s'
                  % (len(missing), ', '.join(missing)))
        else:
            print('   ok   all %d released input files match their recorded SHA-256' % n)
    else:
        FAIL.append(('CHECKSUMS.sha256', 'absent', 'the released data must be hashed'))
        print('   FAIL  CHECKSUMS.sha256 is absent, so the released data is unverified')

    # requirements.txt must pin, not float: an unpinned environment cannot
    # reproduce assertions carried to four decimal places.
    if os.path.exists('requirements.txt'):
        reqs = [l.strip() for l in open('requirements.txt', encoding='utf-8')
                if l.strip() and not l.startswith('#')]
        loose = [r for r in reqs if '==' not in r]
        if loose:
            FAIL.append(('unpinned dependency', ', '.join(loose), 'every line pinned with =='))
            print('   FAIL  %d dependency line(s) are not pinned: %s'
                  % (len(loose), ', '.join(loose)))
        else:
            print('   ok   all %d dependencies are pinned to an exact version' % len(reqs))
        # and the versions named must be the ones this run actually used
        import numpy
        import pandas
        for mod, name in ((numpy, 'numpy'), (pandas, 'pandas')):
            want = [r for r in reqs if r.lower().startswith(name)]
            if want and want[0].split('==')[1] != mod.__version__:
                # Deliberately neutral. This fires in two opposite situations:
                # the pin was not updated after an upgrade, or the reader's
                # environment does not match a correct pin. Asserting the file
                # is stale told a reviewer running an older pandas the wrong
                # thing entirely.
                FAIL.append(('pinned version and installed version differ',
                             want[0], '%s %s is installed' % (name, mod.__version__)))
                print('   FAIL  requirements.txt pins %s; this run used %s %s. '
                      'Update whichever is wrong.'
                      % (want[0], name, mod.__version__))
            elif want:
                print('   ok   %s matches the version this run used' % want[0])

    # Every Python script must run from a working directory other than its own.
    # Two did not: analyze_canopy_bias.py and runoff_consequence.py defaulted the
    # CSV to a bare relative name and died on FileNotFoundError for a file
    # sitting beside them. That breaks IDLE's Run Module, a double-click and any
    # absolute-path invocation, which is how most readers who are not at a
    # terminal will try this.
    #
    # Checked statically rather than by executing twelve scripts: a script is
    # portable if it anchors on __file__, which is what every fixed one now does.
    import glob as _glob
    unportable = []
    for pyf in sorted(_glob.glob('*.py')):
        if pyf in ('conley.py', 'run_all.py'):
            continue   # conley.py is a library with no inputs; run_all anchors
        body = open(pyf, encoding='utf-8').read()
        reads_input = re.search(r"open\(\s*['\"]|read_csv\(|imread\(|Image\.open\(", body)
        anchored = '_os.path.abspath(__file__)' in body or 'os.path.abspath(__file__)' in body
        if reads_input and not anchored:
            unportable.append(pyf)
    if unportable:
        FAIL.append(('scripts that only run from their own directory',
                     ', '.join(unportable), 'anchor paths on __file__'))
        print('   FAIL  %d script(s) resolve inputs relative to the working '
              'directory, so they break in IDLE: %s'
              % (len(unportable), ', '.join(unportable)))
    else:
        print('   ok   every script that reads an input anchors it on __file__')

    # Provenance of every released dataset. The Open Materials claim is that the
    # code behind the released data ships with it, and an audit found that true
    # for two of six: signal_check_v3.js and nlcd_vs_ghsl_check.js existed in the
    # working tree but were never added to the manifest, while two more datasets
    # were produced in interactive sessions whose scripts were not retained.
    #
    # The two that existed now ship. The two that do not are declared here and in
    # the README rather than left to be discovered, because the guidelines make
    # authors accountable for disclosure accuracy and a claim that quietly
    # covered four of six would not be accurate.
    #
    # Every released CSV must appear below, so a new dataset cannot ship without
    # a provenance decision being made about it.
    PROVENANCE = {
        'nevada_canopy_bias_rowlevel.csv': 'run_full_analysis_browser.js',
        'parcel_extras.csv': 'run_full_analysis_browser.js',
        'ca_county_scan.csv': 'signal_check_v3.js',
        'nlcd_vs_ghsl_check.csv': 'nlcd_vs_ghsl_check.js',
        # method documented in the README, script not retained
        'parcel_edge_exact.csv': None,
        'ms_footprint_validation.csv': None,
    }
    if os.path.exists('build_package.sh'):
        manifest = open('build_package.sh', encoding='utf-8').read()
        block = re.search(r'FILES=\((.*?)\n\)', manifest, re.S)
        listed = set()
        if block:
            for line in block.group(1).split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    listed.update(line.split())
        released = sorted(f for f in listed if f.endswith('.csv'))
        undeclared = [f for f in released if f not in PROVENANCE]
        if undeclared:
            FAIL.append(('released data with no provenance decision',
                         ', '.join(undeclared), 'an entry in PROVENANCE'))
            print('   FAIL  %d released dataset(s) have no provenance entry: %s'
                  % (len(undeclared), ', '.join(undeclared)))
        else:
            missing_code = [(d, sc) for d, sc in PROVENANCE.items()
                            if sc and sc not in listed]
            if missing_code:
                FAIL.append(('a named producing script does not ship',
                             ', '.join('%s (for %s)' % (sc, d)
                                       for d, sc in missing_code),
                             'add it to the manifest'))
                print('   FAIL  %d producing script(s) are named but not shipped: %s'
                      % (len(missing_code), ', '.join(sc for _, sc in missing_code)))
            else:
                have = sum(1 for v in PROVENANCE.values() if v)
                print('   ok   all %d released datasets have a provenance decision; '
                      '%d ship their producing script' % (len(released), have))
                _print('   .    %d were produced in interactive sessions whose '
                       'scripts were not retained, declared in the README'
                       % (len(PROVENANCE) - have))

    # The R reimplementation must exist and must still run. It is the third
    # independent implementation of the headline numbers, after the browser
    # JavaScript and this harness, and its value is entirely in being written
    # from the paper's definitions rather than translated from this file. An R
    # script that shipped broken would be worse than none.
    if not os.path.exists('verify_in_r.R'):
        FAIL.append(('verify_in_r.R', 'absent', 'the R reimplementation must ship'))
        print('   FAIL  verify_in_r.R is absent')
    else:
        import shutil
        import subprocess
        if shutil.which('Rscript') is None:
            _print('   .    R is not installed here, so verify_in_r.R was not run. '
                   'CI runs it on every push.')
        else:
            r = subprocess.run(['Rscript', 'verify_in_r.R'],
                               capture_output=True, text=True)
            if r.returncode == 0:
                # Never counted. A failure is still a failure, but counting the
                # pass would make the assertion total depend on whether R is
                # installed, and the README cannot state a number true both on
                # CI and on a machine without R. Same contract as the
                # PDF-currency check.
                _print('   .    verify_in_r.R reproduces the headline results in R '
                       '(not counted)')
            else:
                tail = (r.stdout + r.stderr).strip().split('\n')[-1:]
                FAIL.append(('verify_in_r.R disagrees', ' '.join(tail),
                             'the R implementation must agree'))
                print('   FAIL  verify_in_r.R exited %d: %s'
                      % (r.returncode, ' '.join(tail)))

    # Once a licence exists it must be stated in every place that claims one.
    has_license = os.path.exists('LICENSE') or os.path.exists('LICENSE.md')
    cff = open('CITATION.cff', encoding='utf-8').read() if os.path.exists('CITATION.cff') else ''
    cff_license = re.search(r'^license:\s*(\S+)', cff, re.M)
    if not has_license:
        # Reported as a note, not a skip and not a failure. The licence is a
        # real release blocker and it is tracked in LICENSE_DECISION.md and the
        # submission checklist, but making the whole harness red for an open
        # author decision would stop the package building at all, and the
        # submission zip is a different artefact from a public GitHub release.
        _print('   NOTE  no LICENSE file yet. This blocks the Zenodo deposit, the '
               'Open Materials badge\n         and any GitHub release. See '
               'LICENSE_DECISION.md.')
        if cff_license:
            FAIL.append(('CITATION.cff names a licence', cff_license.group(1),
                         'no LICENSE file exists to match it'))
            print('   FAIL  CITATION.cff declares license %s with no LICENSE file present'
                  % cff_license.group(1))
    elif not cff_license:
        FAIL.append(('CITATION.cff licence', 'not set',
                     'a LICENSE file exists, so CITATION.cff must name it'))
        print('   FAIL  a LICENSE file exists but CITATION.cff does not name a licence')
    else:
        print('   ok   LICENSE and CITATION.cff both name a licence')

    # A shipped document that describes a finished decision as open. LICENSE_DECISION.md
    # read "Status: open" and "There is no LICENSE file in this package" for several
    # passes after MIT was chosen and LICENSE was written. Every mechanical check
    # passed, because they look at LICENSE and CITATION.cff, and neither has anything
    # to say about a prose file next to them going stale. A reviewer opening it was
    # told the package is unlicensed, which is the one thing that would stop them
    # reusing it. Found only because the author asked why MIT rather than Apache.
    if os.path.exists('LICENSE_DECISION.md'):
        dec = open('LICENSE_DECISION.md', encoding='utf-8').read()
        stale = [s for s in ('Status: open',
                             'There is no LICENSE file',
                             'Nothing licenses the') if s in dec]
        if os.path.exists('LICENSE') and stale:
            FAIL.append(('LICENSE_DECISION.md describes a decision that is made',
                         'the decision recorded as in force',
                         ', '.join(repr(s) for s in stale),
                         ('expected', 'found')))
            print('   FAIL  LICENSE exists but LICENSE_DECISION.md still says %s'
                  % ', '.join(repr(s) for s in stale))
        elif os.path.exists('LICENSE'):
            print('   ok   LICENSE_DECISION.md records the licence decision as settled')


def alt_text_and_caption_counts(d, m, path='build_manuscript.js'):
    """Numbers in the figure alt text, and captions that count their own rows.

    Alt text is PUBLISHED content: Taylor & Francis serve it as the image
    description, and the guidelines say they will generate it with AI if the
    author does not. The author wrote all four by hand, and they carry figures
    that the numeric coverage audit could not distinguish from coincidental
    matches elsewhere in this file. Two were reaching nothing:

    - Figure 1: "five of 47 occupied 5 km grid cells hold 50 percent of the
      parcels". Computed by make_figure_studyarea.py and printed into the map,
      then repeated in the alt text, and asserted nowhere.
    - Figure 4: "the bound falls 42 percent across the canopy range".

    THE GRID MATTERS AND THE FIRST CHECK OF IT WAS WRONG. Counting occupied
    cells on an equirectangular kilometre grid gives 43 cells and 54.3 percent,
    which looks like a defect and is not one: the statistic is origin and
    projection dependent, and make_figure_studyarea.py computes it on the
    EPSG:5070 Albers grid, explicitly rejecting a degree graticule because at
    this latitude 0.05 degrees is 4.3 km by 5.5 km and so is not a 5 km cell.
    On the grid the figure actually uses, the numbers are 47 and 50.3. The
    Albers forward projection is reproduced here rather than imported, so this
    check does not pass merely because it shares a bug with the figure script.
    """
    import re
    print("\nALT TEXT  published image descriptions, and captions that count rows")

    R, e2 = 6378137.0, 0.0066943800229
    lat0, lon0 = np.radians(23.0), np.radians(-96.0)
    p1, p2 = np.radians(29.5), np.radians(45.5)
    qq = lambda t: (1 - e2) * (t / (1 - e2 * t * t) - (1 / (2 * np.sqrt(e2))) *
                               np.log((1 - np.sqrt(e2) * t) / (1 + np.sqrt(e2) * t)))
    mmf = lambda t: np.cos(np.arcsin(t)) / np.sqrt(1 - e2 * t * t)
    s1, s2, s0 = np.sin(p1), np.sin(p2), np.sin(lat0)
    nn = (mmf(s1) ** 2 - mmf(s2) ** 2) / (qq(s2) - qq(s1))
    C = mmf(s1) ** 2 + nn * qq(s1)
    rho0 = R * np.sqrt(C - nn * qq(s0)) / nn
    rho = R * np.sqrt(C - nn * qq(np.sin(np.radians(m.lat.values)))) / nn
    th = nn * (np.radians(m.lon.values) - lon0)
    X, Y = rho * np.sin(th), rho0 - rho * np.cos(th)
    cells = pd.Series(list(zip(np.floor(X / 5000.0), np.floor(Y / 5000.0))))
    check("F1 alt text: occupied 5 km Albers cells", 47, cells.nunique(), 0)
    check("F1 alt text: share in the five largest cells (%)", 50,
          100 * cells.value_counts().head(5).sum() / len(m), 0.5)

    q = pd.qcut(m.canopy, 10, labels=False)
    b = m.groupby(q).imp_floor_px.mean().values
    check("F4 alt text: bound falls across the canopy range (%)", 42,
          100 * (b[0] - b[-1]) / b[0], 0.5)

    # A caption that counts its own rows is a claim about the table beside it,
    # and it goes stale the moment a row is added. Table 4's caption said three
    # when the detection-failure quadratic made it four.
    src = open(path, encoding='utf-8').read()
    unesc = lambda t: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm2: chr(int(mm2.group(1), 16)), t).replace("\\'", "'")
    WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
             'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
    cap = None
    for mm2 in re.finditer(r"body\.push\(caption\('((?:[^'\\]|\\.)*)'", src):
        t = unesc(mm2.group(1))
        if t.startswith('Table 4.'):
            cap = t
            break
    claim = re.search(r'the (\w+) rows reporting coefficients to three or four '
                      r'decimal places', cap or '')
    if not claim:
        FAIL.append(("Table 4 caption row-count claim", 'not found',
                     'the caption must state how many rows use the other outcome'))
        print('   FAIL  Table 4 caption no longer states its row count, so this is vacuous')
        return
    i = src.find("['Quadratic in canopy'")
    seg = src[max(0, i - 3000):i + 3000]
    rows = re.findall(r"\n\s*\['[^']{3,80}',\s*'([^']{1,40})'", seg)
    deep = [r for r in rows if re.search(r'\d\.\d{3,4}\b', r)]
    check("Table 4 caption: rows at three or four decimal places",
          WORDS[claim.group(1)], len(deep), 0)


def embedded_figures_are_current():
    """The four figures inside the .docx, against the figure files on disk.

    `rendered_matches_source()` compares TEXT. The manuscript also embeds four
    images, and nothing compared those: regenerate a figure, forget to rerun
    node, and the document carries the old picture while every check passes.
    That was a live risk this session, when all four figure titles were restyled.

    Compared by pixels, not by bytes, and the difference matters. The embedded
    copies are each exactly 5,770 bytes smaller than the files on disk, which is
    matplotlib's caBX XMP metadata chunk (5,758 bytes plus 12 of framing) that
    docx-js strips on embed. A byte comparison would report all four as stale
    every single time. The pixels are identical.
    """
    import hashlib
    import io
    import os
    import zipfile
    print("\nFIGURES  the images inside the .docx against the files on disk")
    docx = 'canopy_bias_manuscript_GIScienceRS.docx'
    if not os.path.exists(docx):
        SKIPPED.append('the embedded-figure check (%s absent)' % docx)
        print('   (%s absent; skipping)' % docx)
        return
    try:
        from PIL import Image
    except ImportError:
        MISSING_TOOLS.append('Pillow')
        SKIPPED.append('the embedded-figure check (Pillow absent)')
        _print('   .    Pillow is not installed, so embedded figures were not checked')
        return
    Image.MAX_IMAGE_PIXELS = None

    z = zipfile.ZipFile(docx)
    embedded = {}
    for n in z.namelist():
        if not (n.startswith('word/media/') and n.lower().endswith('.png')):
            continue
        im = Image.open(io.BytesIO(z.read(n))).convert('RGB')
        embedded.setdefault(im.size, set()).add(
            hashlib.sha256(im.tobytes()).hexdigest())

    stale = []
    figs = manuscript_figures()
    if len(figs) < 4:
        FAIL.append(('figure list derivation', '%d figures found' % len(figs),
                     'at least the 4 the manuscript embeds'))
        print('   FAIL  only %d figure(s) derived from the manuscript, so this '
              'check would look at almost nothing' % len(figs))
        return
    for f in figs:
        if not os.path.exists(f):
            stale.append('%s is absent' % f)
            continue
        im = Image.open(f).convert('RGB')
        h = hashlib.sha256(im.tobytes()).hexdigest()
        if h not in embedded.get(im.size, ()):
            stale.append(f)
    if stale:
        FAIL.append(('the .docx embeds a stale figure', ', '.join(stale),
                     'rebuild the manuscript with node build_manuscript.js'))
        print('   FAIL  %d figure(s) on disk are not the ones embedded in the '
              '.docx: %s' % (len(stale), ', '.join(stale)))
        print('         Rerun: node build_manuscript.js, then reconvert the PDF.')
    else:
        print('   ok   all %d figures in the .docx are pixel-identical to the '
              'files on disk' % len(figs))


def declared_fonts():
    """The .docx must name exactly one font family, and it must be the intended one.

    docx-js applies a font per run. A run created without one inherits whatever
    the reader's Word defaults to, which on a modern install is Calibri, and a
    single Calibri paragraph in a Times New Roman manuscript is the kind of thing
    a production editor sends back. Nothing checked it.

    Checked on the .docx rather than the builder, because the builder is where a
    run gets its font and the document is where the mistake shows up.

    Note for anyone reading the rendered PDF's font table: it lists Liberation
    Serif, not Times New Roman. That is LibreOffice substituting a
    metric-compatible clone during conversion on a machine without the real
    font. The .docx asks for Times New Roman, which is what matters, and the
    substitution is metric-for-metric so pagination is identical either way.
    """
    import os
    import re
    import zipfile
    print("\nFONTS  the font the .docx asks for")
    docx = 'canopy_bias_manuscript_GIScienceRS.docx'
    if not os.path.exists(docx):
        SKIPPED.append('the declared-font check (%s absent)' % docx)
        print('   (%s absent; skipping)' % docx)
        return
    z = zipfile.ZipFile(docx)
    body = z.read('word/document.xml').decode('utf-8')
    named = set(re.findall(r'w:ascii="([^"]+)"', body))
    styles = z.read('word/styles.xml').decode('utf-8')
    named |= set(re.findall(r'w:ascii="([^"]+)"', styles))
    if named == {'Times New Roman'}:
        print('   ok   every run and style asks for Times New Roman, and nothing else')
    else:
        FAIL.append(('the .docx names more than one font', ', '.join(sorted(named)),
                     'Times New Roman only'))
        print('   FAIL  the .docx names %d font(s): %s'
              % (len(named), ', '.join(sorted(named))))


def author_identifiers(path='build_manuscript.js'):
    """The ORCID checksum, and one email across the submitted documents.

    Never checked. An ORCID with a bad check digit is accepted by a submission
    form's format validator and then silently misattributes the paper, or fails
    to attribute it at all. The check digit is ISO 7064 MOD 11-2, computable
    offline, so there is no reason to take it on trust.
    """
    import os
    import re
    print("\nAUTHOR  ORCID checksum and contact consistency")
    ids, mails = {}, {}
    for f in ('build_manuscript.js', 'build_cover_letter.js', 'COVER_LETTER.md'):
        if not os.path.exists(f):
            continue
        t = open(f, encoding='utf-8').read()
        for m in re.finditer(r'\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b', t):
            ids.setdefault(m.group(1), []).append(f)
        for m in re.finditer(r'[\w.+-]+@[\w-]+\.[\w.]+', t):
            mails.setdefault(m.group(0), []).append(f)
    if not ids:
        FAIL.append(('ORCID', 'not found', 'the manuscript must carry one'))
        print('   FAIL  no ORCID found in the submitted documents')
        return
    if len(ids) > 1:
        FAIL.append(('more than one ORCID', ', '.join(sorted(ids)), 'exactly one'))
        print('   FAIL  the documents carry %d different ORCIDs: %s'
              % (len(ids), ', '.join(sorted(ids))))
        return
    o = next(iter(ids))
    d = re.sub(r'[^0-9X]', '', o.upper())
    total = 0
    for ch in d[:15]:
        total = (total + int(ch)) * 2
    expect = 'X' if (12 - total % 11) % 11 == 10 else str((12 - total % 11) % 11)
    if d[15] == expect:
        print('   ok   ORCID %s has a valid ISO 7064 MOD 11-2 check digit' % o)
    else:
        FAIL.append(('ORCID check digit', d[15], expect))
        print('   FAIL  ORCID %s has check digit %s; MOD 11-2 gives %s'
              % (o, d[15], expect))
    if len(mails) == 1:
        print('   ok   one corresponding email across the submitted documents')
    else:
        FAIL.append(('corresponding email', ', '.join(sorted(mails)), 'exactly one'))
        print('   FAIL  %d different email addresses appear: %s'
              % (len(mails), ', '.join(sorted(mails))))


def citation_reference_pairing(path='build_manuscript.js'):
    """Every reference entry is cited, and every citation has an entry.

    Nothing checked this. `callout_lint()` covers the first-citation ORDER of
    tables, figures and equations, which is a different thing: a reference list
    with an uncited entry, or a citation with no entry, is a standard copyedit
    failure and neither was tested. Both directions came back clean at 408
    assertions, 27 entries all cited and every parsed citation resolved, so this
    is a guard against the next edit rather than a repair.

    The matching is deliberately loose in one direction and strict in the other.
    Forward, an entry counts as cited when its leading surname appears within 90
    characters before its year somewhere in the prose, which tolerates the styles
    the manuscript actually uses: "Wickham et al. 2021, 2023" cites two entries
    off one surname, and "Connecticut DEP 2006" and "USDA SCS 1986" are
    institutional. Backward, only real author-date shapes are read, so "NLCD
    2019", "VIIRS 2016" and "Equation 2" are not mistaken for citations.

    Surname plus year is the key, so two entries sharing both would collapse.
    The list has no such pair, and the count assertion below would notice if a
    future edit introduced one.
    """
    import re
    print("\nREFERENCES  every entry cited, every citation entered")
    src = open(path, encoding='utf-8').read()
    unesc = lambda t: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), t).replace("\\'", "'")
    seg = src[src.find('const refs = ['):]
    seg = seg[:seg.find('\n];')]
    refs = [unesc(m.group(1)) for m in
            re.finditer(r"^\s*'((?:[^'\\]|\\.)*)',?\s*$", seg, re.M)]
    if not refs:
        FAIL.append(('reference list', 'not found', 'a refs array must exist'))
        print('   FAIL  could not locate the reference list, so it went unchecked')
        return

    def entry_key(r):
        m = re.match(r'(.+?)\.?\s(\d{4})\.', r)
        if not m:
            return None
        auth, yr = m.group(1), m.group(2)
        acro = re.match(r'([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*)\s*\(', auth)
        if acro:
            name = acro.group(1).strip()
        else:
            a = re.match(r'([A-Z][A-Za-z\u2019\'-]+)', auth)
            if not a:
                return None
            name = a.group(1)
        return name.split()[0], yr

    keys = [entry_key(r) for r in refs]
    if None in keys:
        FAIL.append(('reference entry unparseable',
                     refs[keys.index(None)][:60], 'Author. YEAR. form'))
        print('   FAIL  a reference entry does not parse as Author. YEAR.')
        return
    check("references parsed", len(refs), len(set(keys)), 0)

    prose = ' '.join(unesc(m.group(1)) for m in
                     re.finditer(r"body\.push\((?:p|caption)\('((?:[^'\\]|\\.)*)'", src))
    prose += ' ' + ' '.join(unesc(m.group(1)) for m in
                            re.finditer(r"\{\s*t:\s*'((?:[^'\\]|\\.)*)'", src))
    prose = re.sub(r'\s+', ' ', prose)

    uncited = []
    for (surname, yr) in keys:
        hit = False
        for m in re.finditer(r'\b' + re.escape(yr) + r'[a-z]?\b', prose):
            if re.search(r'\b' + re.escape(surname), prose[max(0, m.start() - 90):m.start()]):
                hit = True
                break
        if not hit:
            uncited.append('%s %s' % (surname, yr))
    if uncited:
        FAIL.append(('reference entries never cited', ', '.join(uncited),
                     'every entry cited in the text'))
        print('   FAIL  %d reference entry(ies) are never cited: %s'
              % (len(uncited), ', '.join(uncited)))
    else:
        print('   ok   all %d reference entries are cited in the text' % len(refs))

    NAME = r'[A-Z][A-Za-z\u2019\'-]+'
    found = set()
    for m in re.finditer('(' + NAME + r')(?:\s+et\s+al\.|\s+and\s+' + NAME
                         + r')?\s*\((\d{4})[a-z]?\)', prose):
        found.add((m.group(1), m.group(2)))
    for g in re.finditer(r'\(([^()]{4,160})\)', prose):
        inner = g.group(1)
        if not re.search(r'\b(19|20)\d{2}\b', inner):
            continue
        for part in inner.split(';'):
            mm = re.match(r'\s*(' + NAME + r'(?:\s+[A-Z]{2,6})*)(?:\s+et\s+al\.)?'
                          r'(?:\s+and\s+' + NAME + r')?\s+'
                          r'((?:\d{4}[a-z]?)(?:\s*,\s*\d{4}[a-z]?)*)', part)
            if mm:
                for y in re.findall(r'\d{4}', mm.group(2)):
                    found.add((mm.group(1).split()[0], y))
    entries = set(keys)
    orphan = sorted('%s %s' % c for c in found if c not in entries)
    if orphan:
        FAIL.append(('citations with no reference entry', ', '.join(orphan),
                     'every citation has an entry'))
        print('   FAIL  %d citation(s) have no reference entry: %s'
              % (len(orphan), ', '.join(orphan)))
    else:
        print('   ok   all %d author-date citations resolve to an entry' % len(found))


def spelling_consistency(path='build_manuscript.js'):
    """Consistent British spelling, which SUBMISSION_CHECKLIST.md claims is done.

    Tested rather than assumed, and one deviation was real: "attenuates the
    estimate toward zero" in Section 4.3, the only instance of either form in the
    manuscript, in running prose with no proper noun or quotation to excuse it.

    Most of what a naive scan flags here is legitimate and must not be "fixed":

    - Quoted source text. The MRLC metadata says "suburban centers" and a
      quotation is reproduced as published, so quotations are stripped first.
    - Proper nouns. Defense Meteorological Satellite Program, 3D Elevation
      Program, National Agriculture Imagery Program, the NLCD program, and the
      EnviroAtlas "meter-scale" land cover are named as their owners spell them.
      The words program, center, defense and meter are therefore not scanned;
      every occurrence of each was read and all are proper nouns or quotations.
    - The noun and verb split. British English writes the noun "licence" and the
      verb "licensed", and the manuscript has exactly one of each, correctly.

    Also held: one percent form across the three documents a reader sees. The
    manuscript uses "percent" 74 times and "per cent" never, the cover letter
    matches, and the README mixed 10 against 8 until this check was written.
    """
    import os
    import re
    print("\nPROSE  British spelling, and one percent form across the documents")
    src = open(path, encoding='utf-8').read()
    unesc = lambda t: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), t).replace("\\'", "'")
    prose = ' '.join(unesc(m.group(1)) for m in
                     re.finditer(r"body\.push\((?:p|caption)\('((?:[^'\\]|\\.)*)'", src))
    # strip direct quotations: they are reproduced as published
    prose = re.sub(r'\u201c[^\u201d]*\u201d', ' ', prose)
    US = [r'\bcolor', r'\bbehavior', r'\bfavor(?!ite)', r'\bneighbor',
          r'\banaly[sz]?z', r'\borganiz', r'\brecogniz', r'\bmodeling',
          r'\blabeled', r'\bcatalog\b', r'\bsummariz', r'\bcharacteriz',
          r'\bminimiz', r'\bmaximiz', r'\butiliz', r'\bnormaliz',
          r'\btoward\b', r'\bgray\b', r'\bfiber', r'\bliter\b']
    hits = []
    for pat in US:
        for m in re.finditer(pat, prose, re.I):
            hits.append('%r in "...%s..."' % (m.group(),
                        ' '.join(prose[max(0, m.start() - 40):m.end() + 30].split())))
    if hits:
        for h in hits:
            FAIL.append(('US spelling in manuscript prose', h, 'British form'))
            print('   FAIL  %s' % h)
    else:
        print('   ok   no US spelling in manuscript prose outside quotations and '
              'proper nouns')

    # Every shipped document, derived from the manifest, not three hand-named
    # ones. The hand-kept version checked the manuscript, the letter and the
    # README, and so never looked at REFERENCES_VERIFIED.md, which used "per
    # cent" once where every other document in the package uses "percent".
    #
    # Two questions are asked, and the second is the one the old version could
    # not ask at all: no document may mix the forms, AND the package must settle
    # on one form across documents. Quoted spans are stripped first, because a
    # source that writes "per cent" is reproduced as published.
    docs = [(path, 'the manuscript')]
    if os.path.exists('build_package.sh'):
        blk = re.search(r'FILES=\((.*?)\n\)',
                        open('build_package.sh', encoding='utf-8').read(), re.S)
        if blk:
            for line in blk.group(1).split('\n'):
                for f in line.strip().split():
                    if f.endswith('.md'):
                        docs.append((f, f))
    if os.path.exists('COVER_LETTER.md'):
        docs.append(('COVER_LETTER.md', 'the cover letter'))
    forms = {}
    for f, label in docs:
        if not os.path.exists(f):
            continue
        t = re.sub(r'\u201c[^\u201d]*\u201d|"[^"\n]{0,400}"', ' ',
                   open(f, encoding='utf-8').read())
        forms[label] = (len(re.findall(r'\bpercent\b', t)),
                        len(re.findall(r'\bper cent\b', t)))
    mixed = [l for l, (a, b) in forms.items() if a and b]
    used = set()
    for a, b in forms.values():
        if a:
            used.add('percent')
        if b:
            used.add('per cent')
    if mixed:
        FAIL.append(('two percent forms in one document', ', '.join(mixed),
                     'one form per document'))
        print('   FAIL  %s use both "percent" and "per cent"' % ', '.join(mixed))
    elif len(used) > 1:
        split = ', '.join('%s uses "%s"' % (l, 'percent' if a else 'per cent')
                          for l, (a, b) in sorted(forms.items()) if a or b)
        FAIL.append(('the package uses two percent forms', split, 'one form throughout'))
        print('   FAIL  the shipped documents do not agree on one form: %s' % split)
    else:
        print('   ok   all %d shipped documents use one percent form, "%s"'
              % (len([1 for v in forms.values() if any(v)]),
                 (used or {'percent'}).pop()))


def first_person_lint(path='build_manuscript.js'):
    """A sole-authored paper that says "we" once.

    The manuscript is impersonal throughout: "this paper", "the author reports",
    never "I". It carried exactly one first-person plural, and it sat on the
    novelty claim, where "we are aware of no published accuracy assessment"
    asserts the awareness of a group that does not exist. One slip is worse than
    a consistent editorial "we" would have been, because the disclosure sections
    a few pages later say "the author".

    Case matters. "US" as in United States appears six times and is not a
    pronoun, so this matches lower case only.
    """
    import re
    print("\nPROSE  first person in a sole-authored manuscript")
    src = open(path, encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda mm: chr(int(mm.group(1), 16)), s).replace("\\'", "'")
    text = ' '.join(unesc(m.group(2)) for m in re.finditer(
        r"body\.push\((p|caption)\('((?:[^'\\]|\\.)*)'", src))
    # Case is handled per pronoun, not globally. Matching lower case only, which
    # this did, was the right guard against "US" meaning United States and the
    # wrong rule for everything else: it could not see "We" or "Our" at the
    # start of a sentence, which is exactly where a first-person plural appears
    # in academic prose. Measured on the current manuscript, "we", "our", "ours"
    # and "ourselves" have zero case-insensitive hits, so matching them either
    # way costs nothing, while "us" has five, every one of them "US" the country.
    # Found by test_harness.py: the lint passed on a reintroduced "We make a
    # methodological contribution".
    bad = []
    for pron, flags in (('we', re.I), ('our', re.I), ('ours', re.I),
                        ('ourselves', re.I), ('us', 0)):
        for m in re.finditer(r'(?<![A-Za-z])%s(?![A-Za-z])' % pron, text, flags):
            bad.append('%r: ...%s...' % (pron, ' '.join(
                text[max(0, m.start() - 60):m.end() + 60].split())))
    for b in bad:
        FAIL.append(('first person in a sole-authored paper', b[:90], 'none allowed'))
        print('   FAIL  %s' % b[:130])
    if not bad:
        print('   ok   no first-person plural anywhere in the body or captions')


def shipped_docs_consistency():
    """The two working documents the package ships as Documentation.

    `canopy_bias_results.md` and `canopy_bias_pipeline.md` are the working record
    of the analysis, shipped so a reviewer can see how the result was arrived at.
    They predate the 100 percent ceiling of Equation 2 being applied to the
    derived breach indicators, so they print the below-floor coefficient as
    +0.3113 where the manuscript prints +0.3119.

    Rewriting their numbers would destroy what they are for, which is a record.
    The invariant instead is that a document carrying the superseded value must
    also carry a status note naming it, so a reviewer who meets the discrepancy
    meets its explanation in the same file. The eleven headline values the
    manuscript prints were checked against both documents term by term when the
    note was written, and only that one differed.
    """
    import os
    import re
    print("\nSHIPPED DOCS  superseded values carry their explanation")
    for f in ('canopy_bias_results.md', 'canopy_bias_pipeline.md'):
        if not os.path.exists(f):
            SKIPPED.append('%s (shipped-doc consistency check)' % f)
            print('   (%s absent; skipping)' % f)
            continue
        s = open(f, encoding='utf-8').read()
        if '0.3113' not in s:
            print('   ok   %s carries no superseded coefficient' % f)
            continue
        m = re.search(r'Status note.*?\n\n', s, re.S)
        if m and '0.3113' in m.group() and '0.3119' in m.group():
            print('   ok   %s explains its superseded coefficient in a status note' % f)
        else:
            FAIL.append(('%s superseded value unexplained' % f, '+0.3113 present',
                         'a status note naming both values'))
            print('   FAIL  %s prints +0.3113 with no status note explaining it' % f)

    # The same class, in the reference log. REFERENCES_VERIFIED.md recorded
    # "Nowak and Greenfield 2010 - NOT VERIFIED" with three failed access routes
    # and an instruction to fetch the paper by hand. Fifteen lines later a newer
    # section reads all three figures out of the publisher's full text. Read top
    # down, the file told the author to go and do work that was already done,
    # and it is the file the generative-AI declaration's claim that citations
    # were verified against primary sources rests on.
    #
    # The failed routes are worth keeping, so the invariant is the one above: a
    # superseded label must sit under a status note that says so.
    f = 'REFERENCES_VERIFIED.md'
    if not os.path.exists(f):
        SKIPPED.append('%s (reference-log supersession check)' % f)
        print('   (%s absent; skipping)' % f)
    else:
        s = open(f, encoding='utf-8').read()
        label = re.search(r'NOT VERIFIED', s)
        if not label:
            print('   ok   %s carries no superseded verification label' % f)
        else:
            note = re.search(r'Status note(?:(?!Status note).)*?superseded',
                             s[:label.start()], re.S)
            if note:
                print('   ok   %s marks its superseded verification label as '
                      'superseded' % f)
            else:
                FAIL.append(('%s superseded label unexplained' % f,
                             'NOT VERIFIED present',
                             'a status note above it marking the section superseded'))
                print('   FAIL  %s says NOT VERIFIED with no status note above it '
                      'marking that section superseded' % f)


def readme_consistency(csv_path, m=None, path='README.md'):
    """Hold the README to the package it describes. Run this last.

    The README is the one file in the package that no other check touched, and
    it had drifted in three places at once: it claimed 147 assertions when the
    harness ran 296, 34 CSV columns when the file carries 39, and that
    `conley.py` is "imported by the analysis script" when nothing imports it.
    Those were corrected by hand, which fixes the instance and not the class.

    Three claims are now derived rather than trusted: the assertion count, the
    shape of the released CSVs, and the existence of every file the README names.

    The assertion count is self-referential, so the contract is stated exactly:
    the README's number is the total number of "ok" lines the whole run emits,
    including the ones this function prints. At the moment of comparison OK[0]
    counts everything before this line, and the comparison itself prints one
    more, hence the plus one. This check must therefore stay last in main().
    """
    import os
    import re
    print("\nREADME  the package description against the package")
    if not os.path.exists(path):
        SKIPPED.append('%s (README claims unverified)' % path)
        print('   (%s is absent; skipping)' % path)
        return
    txt = open(path, encoding='utf-8').read()

    # Files the README names in backticks. A name it explicitly marks as
    # superseded or not shipped is exempt; the build script's manifest is the
    # authority on what ships, and this only catches names that resolve nowhere.
    named = sorted(set(re.findall(r'`([\w][\w./-]*\.(?:py|js|csv|json|md|sh))`', txt)))
    missing = [f for f in named if not os.path.exists(f)]
    if missing:
        FAIL.append(('README names files that are not here', ', '.join(missing), 'all present'))
        print('   FAIL  README names %d file(s) that do not exist: %s'
              % (len(missing), ', '.join(missing)))
    else:
        print('   ok   every one of the %d files the README names exists' % len(named))

    # The reverse direction, which nothing checked. The test above catches a
    # README naming a file that is not there; this catches a file that ships
    # undocumented, which is what a reviewer opening the archive actually meets.
    # Three files shipped undocumented before this existed: .gitignore,
    # .zenodo.json and GITHUB_AND_ZENODO.md.
    #
    # The README documents related files by suffix shorthand, writing
    # "`figure_studyarea.png`, `.tif`" on one line for two files, so a plain
    # basename search reports five false positives. A file therefore counts as
    # documented if its basename appears, or if some line carries both its stem
    # and its suffix.
    import glob
    shipped = []
    bs = 'build_package.sh'
    if os.path.exists(bs):
        man = open(bs, encoding='utf-8').read()
        block = re.search(r'FILES=\((.*?)\n\)', man, re.S)
        if block:
            # The manifest puts several files on one line, so split on
            # whitespace rather than treating each line as one name.
            for l in block.group(1).split('\n'):
                l = l.strip()
                if not l or l.startswith('#'):
                    continue
                shipped += l.split()
    lines = txt.split('\n')
    undoc = []
    for f in shipped:
        base = os.path.basename(f)
        # the README does not need to name itself
        if base == 'README.md' or base in txt or f in txt:
            continue
        stem, suf = os.path.splitext(base)
        if suf and any(stem in l and suf in l for l in lines):
            continue
        undoc.append(f)
    if undoc:
        FAIL.append(('shipped files the README never mentions', ', '.join(undoc),
                     'every shipped file documented'))
        print('   FAIL  %d shipped file(s) are not mentioned in the README: %s'
              % (len(undoc), ', '.join(undoc)))
    else:
        print('   ok   every one of the %d shipped files is mentioned in the README'
              % len(shipped))

    # The shape of each released CSV, as the README states it.
    for fname, claim in re.findall(r'\| `([\w.-]+\.csv)` \| \*?\*?([^|]{0,90})', txt):
        if not os.path.exists(fname):
            continue
        n = sum(1 for _ in open(fname, encoding='utf-8')) - 1
        ncol = len(open(fname, encoding='utf-8').readline().split(','))
        # "41-county" and "57-county" describe a row count exactly as "24,088
        # rows" does, but the original pattern read only parcels and rows, so the
        # two county-scan CSVs were the only released files whose shape no check
        # reached. They are shipped data carrying README claims, so they are held
        # to the file like the rest.
        mrow = re.search(r'([\d,]+)[\s-]+(?:parcels|rows|county)', claim)
        mcol = re.search(r'(\d+)\s+columns', claim)
        if mrow:
            check('README %s rows' % fname, int(mrow.group(1).replace(',', '')), n, 0)
        if mcol:
            check('README %s columns' % fname, int(mcol.group(1)), ncol, 0)

    # The column reference, name by name, in both directions.
    #
    # The README listed `porch` among the row-level CSV's assessor columns. It is
    # not there: porch area is a column of parcel_extras.csv, and the very next
    # row of the same table explains that porch is excluded from roof_m2. A
    # reviewer following the column reference would have looked for a field the
    # released file does not carry. The file-level shape check above counted 39
    # columns and passed, because a count cannot see a wrong name.
    #
    # Band and field names from other products are quoted in the Meaning column
    # legitimately (`impervious_descriptor` is the NLCD band behind `descr`), so
    # only the Column column is read, which is what the table promises.
    if os.path.exists(csv_path):
        i = txt.find('## Column reference for the row-level CSV')
        if i < 0:
            SKIPPED.append('the README column reference (section not found)')
            print('   (README has no column reference section; skipping)')
        else:
            tbl = txt[i:txt.find('\n## ', i + 10)]
            documented = set()
            for row in tbl.split('\n'):
                if not row.startswith('|') or row.startswith('|---'):
                    continue
                cell = row.split('|')[1]
                documented.update(re.findall(r'`(\w+)`', cell))
            actual = set(open(csv_path, encoding='utf-8').readline().strip().split(','))
            ghost, undoc = sorted(documented - actual), sorted(actual - documented)
            if ghost:
                FAIL.append(('README documents columns the CSV lacks',
                             ', '.join(ghost), 'only columns that exist'))
                print('   FAIL  the column reference names %d field(s) absent from %s: %s'
                      % (len(ghost), csv_path, ', '.join(ghost)))
            elif undoc:
                FAIL.append(('README column reference is incomplete',
                             'undocumented: ' + ', '.join(undoc), 'all %d columns' % len(actual)))
                print('   FAIL  %d column(s) of %s are not in the column reference: %s'
                      % (len(undoc), csv_path, ', '.join(undoc)))
            else:
                print('   ok   the column reference names exactly the %d columns %s carries'
                      % (len(actual), csv_path))

    # The README's own headline paragraph, which is the most-read text in the
    # package and carried FOUR stale t-values: -11.0 for a headline that is
    # -9.7, -13.5 for one that is -13.2, and a range of 8.7 to 9.7 for one that
    # is 7.7 to 8.9. The -13.5 is the value the project record already names as
    # "a printed t that does not reproduce"; it was corrected in the manuscript
    # and the correction never reached the README. Found by writing an
    # independent R implementation and having it disagree.
    if os.path.exists(csv_path):
        # Reuse the frame main() already holds. Loading it a second time here
        # doubled peak memory and killed the run outright on a constrained
        # machine: a clean-unzip verification died silently at 437 of 451
        # checks, with no traceback, because four Conley estimators were being
        # built alongside a second full copy of the data. A reviewer on a
        # laptop would have seen the same thing and concluded the package was
        # broken.
        mm3 = m if m is not None else load(csv_path)[-1]
        for lab, xs, y, want, tol in (
                ('README headline t, unadjusted', H, 'nlcd', -9.7, 0.06),
                ('README headline t, net of lights',
                 H + ['viirs', 'dmsp', 'elev'], 'nlcd', -13.2, 0.06),
                ('README detection-failure t, low end',
                 H + ['viirs', 'dmsp', 'elev'], 'below', 8.9, 0.06),
                ('README detection-failure t, high end', H, 'below', 7.7, 0.06)):
            Xr, _, br, er, Xir, _ = ols(mm3, y, xs)
            t = br[1] / se_conley(Xr, er, Xir, mm3.xk.values, mm3.yk.values, 5.0)
            check(lab, want, t, tol)
        for lit in ('\u22129.7', '\u221213.2', '+7.7 to +8.9'):
            if lit not in txt:
                FAIL.append(('README headline dropped a t-value this check pins',
                             lit, 'the headline must keep quoting it'))
                print('   FAIL  the README headline no longer quotes %r, so this '
                      'check is vacuous' % lit)

    # The two county-scan CSVs carry no manuscript claim, so nothing else in the
    # harness touches them, but the README makes numeric claims about both and a
    # reader can recompute them. The 30.9 percent "missed growth" headline is the
    # unweighted county mean, and the README's warning rests on it being that
    # rather than a result; the 17.9 percent growth-weighted figure is the
    # comparison that makes the warning concrete. A third figure, the strict
    # binary rule, needs pixels that are not released, and the README now says so
    # instead of quoting a number nothing in the package can support.
    if os.path.exists('nlcd_vs_ghsl_check.csv'):
        g = pd.read_csv('nlcd_vs_ghsl_check.csv')
        w = g.ghsl_built_growth_2000_2020_ha
        check('README missed-growth headline, unweighted county mean (%)', 30.9,
              g.pct_growth_outside_nlcd_developed.mean(), 0.06)
        check('README missed-growth, growth-weighted (%)', 17.9,
              100 * (w * g.pct_growth_outside_nlcd_developed / 100).sum() / w.sum(), 0.06)
        for v in ('30.9', '17.9'):
            if v not in txt:
                FAIL.append(('README dropped a figure this check pins', v,
                             'the warning text must keep quoting it'))
                print('   FAIL  the README no longer quotes %s, so this check is vacuous' % v)

    # Every shipped file that quotes the assertion count, not just the README.
    # The count reached six files once the release metadata was added: the
    # README, the CI workflow, the Zenodo description and three places in the
    # GitHub guide. Only the README's was gated, so the other five could drift
    # silently and a reader would meet two different numbers for the same claim.
    # Scanned across EVERY shipped text file, not a hand-kept list of six. The
    # list version missed three stale claims at once: requirements.txt still
    # said 424, test_harness.py said 444, and make_tables.py's own checksum
    # comment said 434. requirements.txt was missed twice over, because its
    # comment wraps and the count and the word "assertions" sit on different
    # lines, so whitespace is normalised before matching.
    #
    # make_tables.py is the one file that legitimately quotes OLD counts: its
    # docstrings narrate defects found at 147, 318, 396 and 293-of-318
    # assertions, and rewriting those would destroy the history they record.
    # Those four are declared here, and any OTHER count in that file is treated
    # as a current claim and held to the README, which is what caught the 434.
    # run_all.py records what the harness cost at 376 assertions, so a reader can
    # see that the memory figure grew with the check count rather than read the
    # current 450 MB as though it had always been that. Declared for the same
    # reason as the five above: the alternative is deleting the history to satisfy
    # the check. README.md carries the same sentence but is `path` here, so the
    # loop skips it and it needs no entry.
    # 376 appears in both sets, and for the same reason twice: run_all.py states
    # the historical cost, and the comment just above states it again in order to
    # explain the exemption. A check that scans the file it lives in will find its
    # own documentation, which is worth knowing before adding a number to a
    # docstring here.
    HISTORICAL = {'make_tables.py': {'147', '318', '396', '293', '408', '376'},
                  'run_all.py': {'376'}}
    manifest_files = []
    if os.path.exists('build_package.sh'):
        blk = re.search(r'FILES=\((.*?)\n\)',
                        open('build_package.sh', encoding='utf-8').read(), re.S)
        if blk:
            for line in blk.group(1).split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    manifest_files += line.split()
    TEXT = ('.md', '.py', '.js', '.R', '.yml', '.json', '.cff', '.txt', '.sh')
    for qf in sorted(set(manifest_files)):
        if qf == path or not qf.endswith(TEXT) or not os.path.exists(qf):
            continue
        # Leading comment markers are stripped before the lines are joined.
        # Without that, requirements.txt's wrapped comment normalises to
        # "...of 522 # assertions...", the marker sits between the number and
        # the word, the pattern does not match, and the file is scanned while
        # checking nothing. That is the vacuous-check failure mode again, in the
        # check written to stop stale counts.
        raw_lines = open(qf, encoding='utf-8', errors='replace').read().split('\n')
        qt = ' '.join(' '.join(re.sub(r'^\s*(#+|//+|\*)\s?', '', l).split())
                      for l in raw_lines)
        quoted = set(re.findall(r'([\d,]+)\s+assertions?', qt))
        quoted -= HISTORICAL.get(qf, set())
        rb2 = re.search(r'([\d,]+)\s+assertions', txt)
        if not quoted:
            continue
        wrong = [q for q in quoted if rb2 and q.replace(',', '') != rb2.group(1).replace(',', '')]
        if wrong:
            FAIL.append(('%s quotes a stale assertion count' % qf,
                         rb2.group(1), ', '.join(sorted(wrong)),
                         ('README', 'this file')))
            print('   FAIL  %s quotes %s assertions; the README says %s'
                  % (qf, ', '.join(sorted(wrong)), rb2.group(1)))
        else:
            print('   ok   %s quotes the README assertion count' % qf)

    # The reduced count, the one a reviewer without SciPy and statsmodels meets,
    # was pinned in exactly one phrasing in one file. Every OTHER statement of
    # it went unchecked, and both of the others were wrong: the README said the
    # count dropped to 432 a hundred lines above correctly stating 446, and
    # requirements.txt still carried the pre-release pair, 424 dropping to 419.
    # Neither was caught, because the loop above matches "<n> assertions" and
    # the reduced count is written as a range, with no such phrase near it.
    # A reviewer in a minimal environment would have read 446 on screen against
    # 432 in the README and had no way to tell which was the package's claim.
    # So: find every statement of the reduced count anywhere in the package,
    # including the README itself, and hold them all to one canonical pair.
    canon_full = re.search(r'([\d,]+)\s+assertions', txt)
    canon_red = re.search(r'([\d,]+)\s+without SciPy and statsmodels', txt)
    if canon_full and canon_red:
        full_s = canon_full.group(1).replace(',', '')
        red_s = canon_red.group(1).replace(',', '')
        seen, bad = 0, []
        for rf in sorted(set(manifest_files) | {path}):
            if not rf.endswith(TEXT) or not os.path.exists(rf):
                continue
            rl = open(rf, encoding='utf-8', errors='replace').read().split('\n')
            rt = ' '.join(' '.join(re.sub(r'^\s*(#+|//+|\*)\s?', '', l).split())
                          for l in rl)
            for a, b in re.findall(r'falls from ([\d,]+) to ([\d,]+)', rt):
                seen += 1
                if (a.replace(',', ''), b.replace(',', '')) != (full_s, red_s):
                    bad.append('%s says %s to %s' % (rf, a, b))
            for one in re.findall(r'([\d,]+)\s+without SciPy and statsmodels', rt):
                seen += 1
                if one.replace(',', '') != red_s:
                    bad.append('%s says %s without the optional packages' % (rf, one))
        if not seen:
            FAIL.append(('reduced assertion count', 'stated nowhere',
                         'the count without SciPy and statsmodels'))
            print('   FAIL  no shipped file states the reduced count; this check is vacuous')
        elif bad:
            FAIL.append(('reduced assertion count',
                         '%s to %s' % (full_s, red_s), '; '.join(sorted(bad)),
                         ('canonical', 'found')))
            print('   FAIL  reduced count disagrees: %s. The canonical pair is %s to %s.'
                  % ('; '.join(sorted(bad)), full_s, red_s))
        else:
            print('   ok   all %d statements of the reduced count agree, %s to %s'
                  % (seen, full_s, red_s))

    # The cover letter's date, which nothing gated.
    #
    # It was added on 29 September and lives in four places at once: the builder,
    # the markdown, the .docx a reviewer receives and the .pdf. The two
    # rendered-against-source checks would have caught a drift in any ordinary
    # paragraph, but both apply a 60-character floor and "Date: 29 September 2026"
    # is 23 characters normalised, so it falls through both. A value in four files
    # with nothing tying them is the defect this harness has found in six other
    # places; it should not be introduced in a seventh by adding a date.
    #
    # The date is also the field most likely to be edited alone, on the morning of
    # submission, in whichever file the author happens to open.
    #
    # Reported, never counted: none of the cover-letter files ships in the
    # reproduction package, so counting any of them would make the total depend on
    # which tree the harness runs in. A disagreement is still a failure.
    if os.path.exists('COVER_LETTER.md'):
        import re as _re2
        srcs, dates = {}, {}
        for f in ('COVER_LETTER.md', 'build_cover_letter.js'):
            if os.path.exists(f):
                srcs[f] = open(f, encoding='utf-8').read()
        if os.path.exists('COVER_LETTER.docx'):
            # Read here rather than reusing rendered_matches_source's docx_text,
            # which is local to that function.
            try:
                import html as _html
                import zipfile as _zf
                _x = _zf.ZipFile('COVER_LETTER.docx').read(
                    'word/document.xml').decode('utf-8')
                srcs['COVER_LETTER.docx'] = _html.unescape(
                    _re2.sub(r'<[^>]+>', '', _re2.sub(r'</w:p>', ' ', _x)))
            except Exception:                              # noqa: BLE001
                pass
        # Two date forms, and the second one is why this is not a one-liner. The
        # original pattern matched only "30 September 2026". Rewriting the letter's
        # date as "September 30, 2026", which is the form an American author is
        # likely to reach for, matched nothing in any of the three files, so `dates`
        # came back empty and the check reported "no date, nothing to keep in step"
        # while three copies of a date sat there able to drift apart. A gate that
        # goes quiet when the thing it guards changes shape is worse than no gate,
        # because the passing line reads like reassurance.
        #
        # Both forms are normalised to ISO before comparison, so the same date
        # written two ways compares EQUAL rather than failing. That is right for a
        # date-agreement check and it leaves a gap: the markdown the author pastes
        # into a submission box and the .docx he attaches could carry the same date
        # in two different styles, which nothing else would catch either, because
        # the prose-drift check below ignores paragraphs under 60 characters and the
        # date line is 23. The raw forms are collected alongside the normalised ones
        # and a mismatch is reported, not failed: it is cosmetic, but it is the kind
        # of cosmetic an editor sees.
        forms = {}
        MONTHS = {m: i for i, m in enumerate(
            ['January', 'February', 'March', 'April', 'May', 'June', 'July',
             'August', 'September', 'October', 'November', 'December'], 1)}
        for f, s in srcs.items():
            m = _re2.search(r'Date:\*{0,2}\s*(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})', s)
            if m:
                d, mon, y = m.group(1), m.group(2), m.group(3)
            else:
                m = _re2.search(r'Date:\*{0,2}\s*([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})', s)
                if not m:
                    continue
                mon, d, y = m.group(1), m.group(2), m.group(3)
            if mon not in MONTHS:
                _print('   FAIL  %s gives the cover letter date with an unreadable '
                       'month, %r' % (f, mon))
                continue
            # Normalised, so "30 September 2026" and "September 30, 2026" compare
            # equal and the reported value is unambiguous.
            dates[f] = '%s-%02d-%02d' % (y, MONTHS[mon], int(d))
            forms[f] = ' '.join(m.group(0).split()[1:])
        if not dates:
            _print('   FAIL  no cover-letter file states a date this check can read. '
                   'Either the date was removed, or it is written in a form neither '
                   'pattern matches, which would leave three copies ungated.')
        elif len(set(dates.values())) == 1:
            if len(set(forms.values())) > 1:
                _print('   .    the cover letter date is written %d different ways '
                       'for the same day: %s (reported, not failed)'
                       % (len(set(forms.values())),
                          '; '.join('%s says %r' % (k, v)
                                    for k, v in sorted(forms.items()))))
            _print('   .    the cover letter date agrees across %d file(s), %s '
                   '(not counted)' % (len(dates), next(iter(dates.values()))))
        else:
            FAIL.append(('the cover letter date differs between its files',
                         'one date everywhere',
                         '; '.join('%s says %s' % (k, v) for k, v in sorted(dates.items())),
                         ('expected', 'found')))
            _print('   FAIL  the cover letter date differs: %s'
                   % '; '.join('%s says %s' % (k, v) for k, v in sorted(dates.items())))
        missing = [f for f in srcs if f not in dates]
        if dates and missing:
            FAIL.append(('the cover letter date is missing from a file that has one elsewhere',
                         'every cover-letter file dated', ', '.join(sorted(missing)),
                         ('expected', 'found')))
            _print('   FAIL  %s carries no date while the others do'
                   % ', '.join(sorted(missing)))

    # The cover letter quotes the same count to the editor, so it drifts the
    # same way. It is checked against the README, so there is one number to
    # change rather than two.
    # Two files carry the letter: the markdown the author can paste into the
    # submission box, and the builder that produces the .docx and .pdf. Both are
    # checked, because fixing one and not the other is the obvious failure.
    letters = [f for f in ('COVER_LETTER.md', 'build_cover_letter.js') if os.path.exists(f)]
    for lf in letters:
        cl = open(lf, encoding='utf-8').read()
        # Match the number whether or not it is emphasised. The first version
        # required the surrounding asterisks and failed the moment the bold was
        # dropped for readability, reporting a count mismatch where the counts
        # in fact agreed. A check on a value should not depend on its styling.
        ca = re.search(r'([\d,]+)\s+assertions', cl)
        rb = re.search(r'([\d,]+)\s+assertions', txt)
        # This one reports through _print on success, so it does NOT add to the
        # "ok" tally. The cover letter is a submission document and is not in
        # the reproduction package, so counting it would make the total depend
        # on which tree the harness runs in, and the README could not state a
        # number true both here and in a reviewer's clean-room unzip.
        # The letter is not obliged to mention the harness at all; the author
        # removed that paragraph. This check exists to stop a quoted count from
        # drifting, not to require one, so a letter that quotes no count passes.
        if not ca:
            _print('   .    %s quotes no assertion count, nothing to drift' % lf)
        elif rb and ca.group(1).replace(',', '') == rb.group(1).replace(',', ''):
            _print('   .    %s quotes the README assertion count (not counted)' % lf)
        else:
            FAIL.append(('%s assertion count' % lf,
                         rb.group(1) if rb else 'README states none',
                         ca.group(1) if ca else 'not stated',
                         ('README', 'this letter')))
            _print('   FAIL  %s and README disagree on the assertion count' % lf)

    # The two letters carry the same prose in two formats: the markdown to paste
    # into the submission box and the builder that makes the .docx and .pdf.
    # Editing one and not the other would send the editor a different letter
    # from the one on file. Reported through _print for the same reason as
    # above: neither file is in the reproduction package.
    if len(letters) == 2:
        js = open('build_cover_letter.js', encoding='utf-8').read()
        md = open('COVER_LETTER.md', encoding='utf-8').read()
        # Curly and straight apostrophes are a formatting difference, not drift:
        # the .docx uses typographic quotes, the markdown stays plain so it
        # survives being pasted into a submission form. Fold them before
        # comparing, or the check fires on every paragraph and means nothing.
        norm = lambda t: ' '.join(re.sub(r'\*+', '', t)
                                  .replace('’', "'").replace('‘', "'")
                                  .replace('“', '"').replace('”', '"').split())
        unesc2 = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                                  lambda mm: chr(int(mm.group(1), 16)), s).replace("\\'", "'")
        body = [norm(unesc2(m2.group(1))) for m2 in
                re.finditer(r"body\.push\((?:p|tight)\('((?:[^'\\]|\\.)*)'", js)]
        mdn = norm(md)
        drift = [b for b in body if len(b) > 60 and b not in mdn]
        if drift:
            FAIL.append(('cover letter copies disagree', drift[0][:70],
                         'the .md and the .docx builder must carry the same text'))
            _print('   FAIL  %d cover-letter paragraph(s) differ between the '
                   '.md and the builder, first: %r' % (len(drift), drift[0][:70]))
        else:
            _print('   .    the two cover-letter copies carry the same text (not counted)')

    submission_archives_agree(txt)

    # The assertion count. See the docstring for why the plus one is right.
    m = re.search(r'([\d,]+)\s+assertions', txt)
    if not m:
        FAIL.append(('README assertion count', 'not stated', 'a number'))
        print('   FAIL  the README no longer states an assertion count')
        return
    # The README states both counts, because two checks depend on optional
    # packages. Expect the one that matches the environment this run had.
    reduced = re.search(r'([\d,]+)\s+without SciPy and statsmodels', txt)
    if not reduced:
        FAIL.append(('README assertion count', 'only one count stated',
                     'the count with and without the optional packages'))
        print('   FAIL  the README states one assertion count; it must state both')
        return
    if OPTIONAL_MISSING:
        claimed = int(reduced.group(1).replace(',', ''))
        _print('   .    %s absent, so the reduced count applies'
               % ' and '.join(sorted(set(OPTIONAL_MISSING))))
    else:
        claimed = int(m.group(1).replace(',', ''))
    actual = OK[0] + 1
    if claimed == actual:
        print('   ok   README states %d assertions, and this run made %d' % (claimed, actual))
    else:
        FAIL.append(('README assertion count', claimed, actual))
        _print('   FAIL  README states %d assertions; this run made %d. Update the README.'
               % (claimed, actual))


def submission_archives_agree(readme_text):
    """Check the two submission archives against the package they describe.

    WHY THIS EXISTS
    ---------------
    `canopy_bias_submission.zip` and `canopy_bias_figures.zip` are what the
    author uploads. Unlike the reproduction package, which `build_package.sh`
    assembles from an explicit manifest behind three gates, these two were
    assembled by hand and each carries a hand-written README stating figures a
    reader will trust: the file count of the reproduction package, the assertion
    count, and every figure's pixel dimensions and dpi.

    Nothing checked those numbers, and one of them was wrong. The submission
    README said the reproduction package holds 65 files. It holds 64.
    `build_package.sh` reported 65 because it read the summary line of
    `unzip -l`, which counts the `matched_parcel_panels/` DIRECTORY entry as a
    file, and the wrong number was copied into the prose. A reader who unzips
    the package and counts finds 64 and has no way to tell which number is the
    typo.

    So this reads both archives and checks their prose against the artefacts.

    NOT COUNTED, deliberately. No archive ships inside the reproduction package,
    so a clean unzip cannot run this, and counting it would make the assertion
    total depend on which tree the harness ran in. That is the same rule the
    cover-letter checks above follow, and the reason is the same.
    """
    import os
    import re as _re
    import zipfile as _zf

    RP = 'canopy_bias_reproduction_package.zip'
    ARCHIVES = {'canopy_bias_submission.zip': 'README_submission.txt',
                'canopy_bias_figures.zip': 'README.txt'}
    # Submission-side figure names to the working-tree files they are copies of.
    FIGURES = {'Figure1.tif': 'figure_studyarea.tif',
               'Figure1.pdf': 'figure_studyarea.pdf',
               'Figure2.tif': 'figure_schematic.tif',
               'Figure2.pdf': 'figure_schematic.pdf',
               'Figure3.tif': 'figure_matched_parcels.tif',
               'Figure3.pdf': 'figure_matched_parcels.pdf',
               'Figure4.tif': 'figure_divergence.tif',
               'Figure4.pdf': 'figure_divergence.pdf',
               'GraphicalAbstract1.png': 'GraphicalAbstract1.png'}

    present = [a for a in ARCHIVES if os.path.exists(a)]
    if not present:
        return

    def stripdate(b):
        """Normalise a matplotlib PDF's embedded creation timestamp.

        Two runs of the same figure script produce byte-identical PDFs except
        for `/CreationDate`. Comparing raw bytes would report drift on every
        regeneration and teach the reader to ignore this check.
        """
        return _re.sub(rb'/CreationDate \(D:[0-9+\x27\-]*\)',
                       b'/CreationDate ()', b)

    # The real file count of the reproduction package: entries that are not
    # directories. This is the number the prose must state.
    rp_files = None
    if os.path.exists(RP):
        with _zf.ZipFile(RP) as z:
            rp_files = sum(1 for i in z.infolist() if not i.is_dir())

    # README.md is already gated against this run's own count a few lines below,
    # so checking the archives against the README makes the chain transitive
    # rather than asserting the number twice from different places.
    want_counts = set()
    for pat in (r'([\d,]+)\s+assertions', r'([\d,]+)\s+without SciPy and statsmodels'):
        mm = _re.search(pat, readme_text)
        if mm:
            want_counts.add(mm.group(1).replace(',', ''))

    bad = 0
    for arc in sorted(present):
        with _zf.ZipFile(arc) as z:
            names = {os.path.basename(n): n for n in z.namelist()
                     if not n.endswith('/')}
            rd = ARCHIVES[arc]
            if rd not in names:
                _print('   FAIL  %s carries no %s' % (arc, rd))
                bad += 1
                continue
            prose = z.read(names[rd]).decode('utf-8', 'replace')

            # 0. the README in the archive against its source in the working
            #    tree. Both archives are built by build_submission.sh from
            #    README_submission.txt and README_figures.txt; an archive whose
            #    README is a stale copy is the failure this catches, and it is
            #    the one that let the wrong file count survive being corrected.
            src_readme = ('README_submission.txt' if rd == 'README_submission.txt'
                          else 'README_figures.txt')
            if os.path.exists(src_readme):
                if prose != open(src_readme, encoding='utf-8').read():
                    _print('   FAIL  %s in %s differs from %s in the working '
                           'tree; rerun build_submission.sh' % (rd, arc, src_readme))
                    bad += 1

            # 0b. the figures README ships twice inside the submission archive,
            #     as 03_Figures/README_figures.txt, and once in the figures
            #     archive as README.txt. Two names, one source. Check they agree.
            if ('README_figures.txt' in names and rd == 'README_submission.txt'
                    and os.path.exists('README_figures.txt')):
                inner = z.read(names['README_figures.txt']).decode('utf-8', 'replace')
                if inner != open('README_figures.txt', encoding='utf-8').read():
                    _print('   FAIL  03_Figures/README_figures.txt in %s differs '
                           'from README_figures.txt in the working tree' % arc)
                    bad += 1

            # 1. the reproduction package's file count, where the prose states it
            mm = _re.search(r'canopy_bias_reproduction_package\.zip,\s*(\d+)\s+files', prose)
            if mm and rp_files is not None:
                if int(mm.group(1)) != rp_files:
                    _print('   FAIL  %s says the reproduction package holds %s '
                           'files; it holds %d' % (rd, mm.group(1), rp_files))
                    bad += 1

            # 2. the assertion counts, against the README's
            for n in _re.findall(r'(\d{3})\s+assertions', prose):
                if want_counts and n not in want_counts:
                    _print('   FAIL  %s states %s assertions; the README states %s'
                           % (rd, n, ' and '.join(sorted(want_counts))))
                    bad += 1
            for n in _re.findall(r'(\d{3})\s+with SciPy and statsmodels absent', prose):
                if want_counts and n not in want_counts:
                    _print('   FAIL  %s states a reduced count of %s; the README '
                           'states %s' % (rd, n, ' and '.join(sorted(want_counts))))
                    bad += 1

            # 3. every figure dimension and dpi the prose states, read from the
            #    image in this same archive rather than from the working tree, so
            #    the check is about what the author will upload.
            for fig, px_w, px_h, dpi in _re.findall(
                    r'(Figure\d\.tif|GraphicalAbstract1\.png)\s+(\d+)\s*x\s*(\d+)\s*px'
                    r'(?:\s+(\d+)\s*dpi)?', prose):
                if fig not in names:
                    _print('   FAIL  %s describes %s, which is not in %s'
                           % (rd, fig, arc))
                    bad += 1
                    continue
                try:
                    from PIL import Image
                    Image.MAX_IMAGE_PIXELS = None
                    import io
                    im = Image.open(io.BytesIO(z.read(names[fig])))
                except Exception:                              # noqa: BLE001
                    continue
                if (im.width, im.height) != (int(px_w), int(px_h)):
                    _print('   FAIL  %s says %s is %s x %s px; it is %d x %d'
                           % (rd, fig, px_w, px_h, im.width, im.height))
                    bad += 1
                if dpi:
                    got = im.info.get('dpi', (None,))[0]
                    if got is None or abs(got - int(dpi)) > 0.01:
                        _print('   FAIL  %s says %s is %s dpi; the file tags %s'
                               % (rd, fig, dpi, got))
                        bad += 1

            # 4. every figure and document in the archive against the working
            #    tree. A figure regenerated after the archive was built is the
            #    failure this catches, and it is the one that would ship a
            #    reviewer a different picture from the one inside the paper.
            for name, src in list(FIGURES.items()) + [
                    ('canopy_bias_manuscript_GIScienceRS.docx',) * 2,
                    ('canopy_bias_manuscript_GIScienceRS.pdf',) * 2,
                    ('COVER_LETTER.docx',) * 2,
                    ('COVER_LETTER.pdf',) * 2]:
                if name not in names or not os.path.exists(src):
                    continue
                a, b = z.read(names[name]), open(src, 'rb').read()
                if name.endswith('.pdf'):
                    a, b = stripdate(a), stripdate(b)
                if a != b:
                    _print('   FAIL  %s in %s differs from %s in the working '
                           'tree; rebuild the archive' % (name, arc, src))
                    bad += 1

    if not bad:
        _print('   .    the %d submission archive(s) agree with the package and '
               'the working tree (not counted)' % len(present))


def check_str(label, got, want):
    """String equality, reported like check() so failures land in the same list."""
    if got == want:
        print('   ok   %s %r' % (label, want[:56]))
    else:
        FAIL.append((label, got[:70] or '(nothing)', want))
        print('   FAIL  %s %r, expected %r' % (label, got[:56], want[:56]))


def conley_implementations_agree(m):
    """Three copies of the Conley estimator ship in this package. Check them.

    `conley.py`, `analyze_canopy_bias.py` and this file each carry their own
    implementation, written differently. Nothing imports `conley.py`, and the
    README described it as "imported by the analysis script", which was wrong.
    Rather than collapse them and risk changing a shipped script, the invariant
    is asserted: on identical inputs all three must agree.

    They do, to 1e-9. That also establishes that the standard-error difference
    between this harness and analyze_canopy_bias.py comes entirely from the
    distance metric each feeds in, not from the estimator.
    """
    import importlib.util
    import os
    from collections import defaultdict as _dd
    print("\nCONLEY  the three shipped implementations, on identical inputs")
    if not (os.path.exists('conley.py') and os.path.exists('analyze_canopy_bias.py')):
        print("   (one of the implementations is absent; skipping)")
        return
    spec = importlib.util.spec_from_file_location('_conleymod', 'conley.py')
    cm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cm)
    src = open('analyze_canopy_bias.py', encoding='utf-8').read()
    i = src.index('def conley_se(')
    j = src.find('\ndef ', i + 1)
    ns = {'np': np, 'defaultdict': _dd}
    exec(src[i:j], ns)
    other = ns['conley_se']
    X, _, b, e, XtXi, _r = ols(m, 'nlcd')
    xs, ys = m.xk.values, m.yk.values
    for cut in (1.0, 2.0, 5.0):
        a = se_conley(X, e, XtXi, xs, ys, cut)
        c = cm.conley_se(X, e, xs, ys, cut, XtXi)
        z = other(X, e, xs, ys, cut, XtXi)
        spread = max(a, c, z) - min(a, c, z)
        check('conley implementations agree at %g km' % cut, 0.0, spread, 1e-9)
    print("   ok   conley.py, analyze_canopy_bias.py and make_tables.py agree")

    # The estimators agreeing is not enough: they must also be fed the same
    # distances. analyze_canopy_bias.py once projected to EPSG:5070 for this,
    # which is equal-area and so distorts distance. Measured against the WGS84
    # geodesic over 79,980 parcel pairs, EPSG:5070 carries an RMS error of
    # 462 m against 90 m for the equirectangular form used here, so the
    # manuscript's standard errors were already on the better metric and the
    # analysis script was moved onto it. This asserts they stay aligned.
    asrc = open('analyze_canopy_bias.py', encoding='utf-8').read()
    assert '111.32' in asrc and 'EPSG:5070 metres, recomputed' not in asrc, (
        'analyze_canopy_bias.py is not using the same local equirectangular '
        'metric as this harness, so its Conley errors will not match Table 1')
    ax = (m.lon.values - m.lon.mean()) * 111.32 * np.cos(np.radians(m.lat.mean())) * 1000.0
    check('analysis-script x metric matches the harness', 0.0,
          float(np.abs(ax / 1000.0 - m.xk.values).max()), 1e-9)



def storey_sensitivity(m):
    """Section 4.2: what a replicator loses without a storey-count field.

    The project's design record (Decision 2) says to publish this so others know
    what the missing field costs, and it was measured but never made it into the
    manuscript. It does now, so it is asserted here.

    Storeys rise with canopy, so a flat assumption overstates roofs exactly where
    canopy is densest, steepens the gradient, and biases the coefficient toward
    the hypothesis. That is the worst direction for an error to run.
    """
    SQFT2M2 = 0.092903
    print("\nSECTION 4.2  cost of assuming a flat storey count")
    dec = pd.qcut(m.canopy, 10, labels=False)
    st = m.groupby(dec).storeys.mean()
    check('4.2 mean storeys, lowest canopy decile', 1.42, st.iloc[0], 0.006)
    check('4.2 mean storeys, highest canopy decile', 1.61, st.iloc[-1], 0.006)
    assert st.iloc[-1] > st.iloc[0], 'storeys must rise with canopy for this to bias upward'
    base = ols(m, 'below')[2][1]
    check('4.2 detection failure, real storeys', 0.312, base, 0.0006)
    flat = float(m.storeys.mean())
    q = m.copy()
    q['_roof'] = (q.sqft / flat + q.garage.fillna(0)) * SQFT2M2
    cell = q.groupby('px')['_roof'].sum()
    q['_b'] = (100 * q.px.map(cell) / 900).clip(upper=100)
    q['_below'] = (q.nlcd < q._b).astype(float)
    flat_c = ols(q, '_below')[2][1]
    check('4.2 detection failure, flat storeys', 0.382, flat_c, 0.0015)
    check('4.2 upward bias from a flat storey count (%)', 22,
          100 * (flat_c - base) / base, 0.6)
    print("   ok   the bias runs toward the hypothesis, as the manuscript states")



def interquartile_reading(m):
    """Section 2.4: the effect over the observed interquartile range.

    `canopy_bias_pipeline.md` directs: "Report the canopy effect over the
    interquartile range of observed canopy, not the 0 to 1 coefficient, which
    extrapolates to a parcel that is 100 percent canopy and also has a house."

    The extrapolation worry turns out not to apply here, and that is worth
    asserting rather than asserting away: 1.2 per cent of the analysed parcels
    sit at complete canopy and carry a recorded dwelling, so the full-range
    contrast is between two observed populations. But the interquartile figure
    is the one a reader needs to judge a typical comparison, and it is about
    half the headline, so the manuscript now reports both.
    """
    print("\nSECTION 2.4  the effect over the observed interquartile range")
    c = m.canopy
    q1, q3 = c.quantile(0.25), c.quantile(0.75)
    check('2.4 canopy first quartile', 0.19, q1, 0.006)
    check('2.4 canopy third quartile', 0.68, q3, 0.006)
    b = ols(m, 'nlcd')[2][1]
    bb = ols(m, 'below')[2][1]
    check('2.4 impervious effect over the IQR', -10.6, b * (q3 - q1), 0.06)
    check('2.4 detection-failure effect over the IQR (points)', 15,
          100 * bb * (q3 - q1), 0.6)
    check('2.4 share at complete canopy (%)', 1.2, 100 * (c >= 1.0).mean(), 0.06)
    check('2.4 share at 0.05 canopy or below (%)', 11.1, 100 * (c <= 0.05).mean(), 0.06)
    assert (c >= 1.0).sum() > 100, (
        'the full-range contrast is only defensible because parcels at complete '
        'canopy genuinely exist; got %d' % (c >= 1.0).sum())
    print("   ok   both ends of the contrast are populated, so it is not an extrapolation")



VERSION_DRIFT = []


def environment_preflight():
    """Say up front when the environment is not the one the results came from.

    Run under pandas 2.2.3 instead of the pinned 3.0.2, the harness reported:

        F4 decile 7 below: manuscript 63.2, data 63.299817
        F4 min decile size: manuscript 2189, data 2188.0

    Five values, and every one of them reads as "the paper is wrong". It is not.
    `qcut` resolves a tie differently between pandas majors, one parcel moves
    between deciles, and the decile 7 and 8 statistics shift with it. The
    pinning in requirements.txt exists for exactly this, and the effect is now
    measured rather than asserted.

    A reviewer meeting five numeric mismatches eighty lines into a run will
    conclude the work does not reproduce. They need to be told in the first
    second, before any number is printed, that their environment is not the one
    being verified. That is what this does.

    It warns rather than refuses: someone deliberately testing a newer pandas
    should still get the full picture, and the summary repeats the warning at
    the end so it cannot scroll past unseen.
    """
    import os
    import re
    if not os.path.exists('requirements.txt'):
        return
    want = {}
    for line in open('requirements.txt', encoding='utf-8'):
        m = re.match(r'\s*([A-Za-z0-9_.-]+)==([^\s#]+)', line)
        if m:
            want[m.group(1).lower()] = m.group(2)
    import numpy
    import pandas
    for mod, name in ((numpy, 'numpy'), (pandas, 'pandas')):
        pinned = want.get(name)
        if pinned and pinned != mod.__version__:
            VERSION_DRIFT.append((name, pinned, mod.__version__))
    if not VERSION_DRIFT:
        return
    bar = '!' * 72
    print(bar)
    print('THIS ENVIRONMENT IS NOT THE ONE THE RELEASED RESULTS CAME FROM.')
    for name, pinned, got in VERSION_DRIFT:
        print('   %-8s pinned %-10s installed %s' % (name, pinned, got))
    print()
    print('Some values below will not reproduce, and that is the environment,')
    print('not the manuscript. pandas resolves a qcut tie differently between')
    print('major versions: one parcel moves between deciles and the decile 7')
    print('and 8 statistics move with it. Measured, not hypothetical.')
    print()
    print('   pip install -r requirements.txt')
    print(bar)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', nargs='?', default='nevada_canopy_bias_rowlevel.csv')
    ap.add_argument('--csv-out', dest='csvdir', default=None,
                    help='directory to write one CSV per table')
    ap.add_argument('--quiet', action='store_true',
                    help='print section headers, failures and the verdict only; '
                         'every check still runs')
    ap.add_argument('--allow-missing', action='store_true',
                    help='accept a partial verification when optional input '
                         'files are absent, instead of exiting non-zero')
    a = ap.parse_args()
    QUIET[0] = a.quiet
    environment_preflight()
    manuscript_lint()
    prose_lint()
    style_lint()
    reference_lint()
    heading_lint()
    callout_lint()
    abstract_lint()
    causal_language_lint()
    hypothesis_containment()
    first_person_lint()
    spelling_consistency()
    citation_reference_pairing()
    journal_limits()
    rendered_matches_source()
    embedded_figures_are_current()
    declared_fonts()
    author_identifiers()
    mechanism_claim_lint()
    literature_figures()
    cover_letter_claims()
    d, m = load(a.csv)
    print(f"analysis sample n = {len(m)} (parcels built on or before 2019)")

    table1(m, a.csvdir)
    table2(m, a.csvdir)
    block_origin_sensitivity(m)
    table3(m, a.csvdir)
    table4(m, a.csvdir)
    table5(d, m, a.csvdir)
    footprint_identity(m)
    equations(d, m)
    wealth_independence(m)
    truncation(m)
    straddle(m)
    nightlights(m)
    functional_form(m)
    covariate_ladder(m)
    epochs(d)
    footprint_validation(d)
    figure4_narrative(m)
    settlement_clustering(m)
    discussion_figures(m)
    density_quartile_rises(m)
    data_availability(d, m)
    robustness_ladder(m)
    study_area(m, d)
    frame_and_porch(d, m)
    table4_tvalues(d, m)
    oehha_reference(m)
    figure3_pair_arithmetic(d, m)
    alt_text_and_caption_counts(d, m)
    figure_title_style()
    release_metadata_agrees_with_the_manuscript()
    gitignore_excludes_nothing_shipped()
    every_shipped_script_is_attributed()
    shipped_javascript_parses()
    figures_carry_no_provenance_manifest()
    figure_formats_and_resolution()
    shipped_tiffs_are_well_formed()
    graphical_abstract_meets_journal_spec()
    ci_covers_every_shipped_script()
    docs_name_only_shipped_files()
    service_record_count()
    repository_metadata()
    matched_pair_selection(m, a.csvdir)
    released_data_consistency(a.csv)
    conley_implementations_agree(m)
    storey_sensitivity(m)
    interquartile_reading(m)
    # Last, because it counts the "ok" lines every check above has printed.
    shipped_docs_consistency()
    shipped_checklists_match_the_placeholders()
    zenodo_description_figures()
    reference_log_is_current()
    reference_implementations_agree()
    footprint_file_integrity(m)
    edge_file_provenance(d)
    abstract_headline_forms()
    abstract_figures_are_each_verified()
    readme_consistency(a.csv, m)

    print("\n" + "=" * 72)
    if FAIL:
        # Two kinds of check fail into this list. A numeric check compares the
        # manuscript against the released data, and "manuscript X, data Y" is
        # exactly right for it. A cross-file check compares two shipped files
        # and never touches the data, so the same labels said "manuscript" of a
        # value the manuscript does not contain, and "data" of a value no data
        # produced. It named the wrong culprit in the one place a reader looks
        # to find out what is wrong. A FAIL entry may therefore carry its own
        # pair of labels as a fourth element; the numeric default is unchanged.
        print(f"{len(FAIL)} CHECK(S) FAILED. Each line gives the two values that disagree:")
        for f in FAIL:
            left, right = f[3] if len(f) > 3 else ('manuscript', 'data')
            print(f"   {f[0]}: {left} {f[1]}, {right} {f[2]}")
        # The failure path is exactly where this matters, and the first version
        # printed it only on success. A reviewer running the wrong pandas sees
        # five numeric mismatches and needs the explanation here, beside them,
        # not in a success message they will never reach.
        if VERSION_DRIFT:
            print("\n   Before reading those as defects: this run used %s, not "
                  "the pinned\n   version(s). pandas moves one parcel between "
                  "deciles across majors, which\n   is what the F4 decile "
                  "mismatches above are. Install the pins and rerun:"
                  % ', '.join('%s %s' % (n, g) for n, _, g in VERSION_DRIFT))
            print("      pip install -r requirements.txt")
        sys.exit(1)
    # A skipped check is not a passed check. The released package once omitted
    # parcel_edge_exact.csv and parcel_extras.csv, so a reviewer running this
    # from the zip silently got 293 of the 318 assertions and still saw the
    # success line below. Skipping is now reported, and fatal by default.
    if SKIPPED:
        why = ('because of a missing optional package or external tool:'
               if (OPTIONAL_MISSING or MISSING_TOOLS)
               else 'because these files are missing:')
        print(f"{len(SKIPPED)} GROUP(S) OF CHECKS COULD NOT RUN, {why}")
        for s in SKIPPED:
            print(f"   {s}")
        if not a.allow_missing:
            if OPTIONAL_MISSING and MISSING_TOOLS:
                fix = ('Install the packages with "pip install -r '
                       'requirements.txt" and the tools named above')
            elif OPTIONAL_MISSING:
                fix = 'Install them with "pip install -r requirements.txt"'
            elif MISSING_TOOLS:
                fix = 'Install %s' % ' and '.join(sorted(set(MISSING_TOOLS)))
            else:
                fix = 'Supply the files'
            print("\nThe manuscript is NOT fully verified by this run. %s, "
                  "or pass --allow-missing to accept a partial check." % fix)
            sys.exit(1)
        print("\n--allow-missing given: continuing with a PARTIAL verification.")
    if VERSION_DRIFT:
        print('\nReminder: this run used %s, not the pinned version(s). Any '
              'numeric mismatch above is the environment, not the manuscript.'
              % ', '.join('%s %s' % (n, g) for n, _, g in VERSION_DRIFT))
    print("All manuscript table, figure and Section 2.4 values reproduce from the data.")


if __name__ == '__main__':
    main()
