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
test_harness.py  -  does each lint actually fire?

WHY THIS EXISTS
---------------
The harness makes 522 assertions about the manuscript. Nothing asserted anything
about the harness. That gap has bitten this package three times, each time with
a check that printed "ok" while looking at nothing:

  * the keyword check searched for a 'Keywords:...' string literal when the
    keywords are built as a run array, found nothing, and passed;
  * the document-title check matched a figure's alt-text `title:` instead of the
    document metadata, and passed on the wrong string;
  * the assertion-count check required bold asterisks around the number and
    stopped seeing it the moment the bold was dropped for readability.

Every check added since has been proved to fire by hand, by reverting the defect
it was written for and watching it fail. This automates that ritual so it runs
on every push instead of depending on whoever added the check remembering to do
it.

WHAT IT DOES
------------
For each case below it writes a PERTURBED COPY of build_manuscript.js to a
temporary file, calls the one lint under test against that copy, and requires
the lint to record a failure. Nothing in the package is modified: the lints take
their path as an argument, so the real file is never touched, which matters
because a test that mutates the thing it tests can leave the tree broken when it
is interrupted.

A lint that does NOT fire on its own defect is a vacuous check, and this exits
non-zero when it finds one.

  python3 test_harness.py

Fast by design: it calls the individual lints rather than running the whole
harness once per case, so it takes seconds rather than a quarter of an hour, and
can run on every push.
"""
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Load make_tables.py's namespace without running main().
_src = open(os.path.join(HERE, 'make_tables.py'), encoding='utf-8').read()
_src = _src.split("if __name__")[0]
MT = {'__file__': os.path.join(HERE, 'make_tables.py')}
exec(compile(_src, 'make_tables.py', 'exec'), MT)

SOURCE = os.path.join(HERE, 'build_manuscript.js')
ORIGINAL = open(SOURCE, encoding='utf-8').read()

# label, lint to call, a (find, replace) pair that reintroduces the defect the
# lint exists to catch. Each find must occur exactly once, or the case is
# reported as stale rather than quietly testing nothing, which is the same
# failure mode this file exists to catch.
CASES = [
    ('spelling_consistency catches a US spelling',
     'spelling_consistency',
     'attenuates the estimate towards zero', 'attenuates the estimate toward zero'),

    ('citation_reference_pairing catches a missing reference entry',
     'citation_reference_pairing',
     "  'Conley, T.G. 1999.", "  'XXConley, T.G. 1999."),

    ('journal_limits catches an over-long abstract',
     'journal_limits',
     'Percentage impervious surface from optical satellite products underpins',
     'Percentage impervious surface from optical satellite products underpins'
     + ' filler' * 200),

    ('journal_limits catches a missing element',
     'journal_limits',
     "body.push(h1('Funding'));", ""),

    ('mechanism_claim_lint catches a mechanism in a caption title',
     'mechanism_claim_lint',
     "caption('Figure 3. Canopy and measured impervious",
     "caption('Figure 3. Canopy occlusion at two matched"),

    ('first_person_lint catches a first-person plural',
     'first_person_lint',
     'This paper makes a methodological contribution',
     'We make a methodological contribution'),
]


def main():
    print('test_harness.py  does each lint fire on the defect it exists to catch?')
    print('  %d cases, against a temporary copy; nothing in the package is modified\n'
          % len(CASES))
    stale, vacuous, ok = [], [], 0
    tmpdir = tempfile.mkdtemp(prefix='harness_selftest_')

    for label, fn, find, repl in CASES:
        if ORIGINAL.count(find) != 1:
            stale.append('%s: its anchor occurs %d times, not once'
                         % (label, ORIGINAL.count(find)))
            print('  STALE %s' % label)
            continue
        path = os.path.join(tmpdir, 'perturbed_build_manuscript.js')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(ORIGINAL.replace(find, repl))

        # Silence the lint's own output and watch its FAIL list instead.
        before = len(MT['FAIL'])
        real_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            MT[fn](path)
        except Exception as exc:                      # noqa: BLE001
            sys.stdout = real_stdout
            vacuous.append('%s: raised %s' % (label, exc.__class__.__name__))
            print('  ERROR %s   (%s)' % (label, exc))
            continue
        finally:
            if sys.stdout is not real_stdout:
                sys.stdout.close()
                sys.stdout = real_stdout

        if len(MT['FAIL']) > before:
            ok += 1
            print('  fires %s' % label)
            del MT['FAIL'][before:]
        else:
            vacuous.append(label)
            print('  VACUOUS %s   -- the defect was reintroduced and the lint '
                  'still passed' % label)

    print('\n' + '=' * 72)
    for s in stale:
        print('  STALE CASE: %s' % s)
    for v in vacuous:
        print('  VACUOUS:    %s' % v)
    if stale or vacuous:
        print('\n%d case(s) did not demonstrate a working lint.' % (len(stale) + len(vacuous)))
        return 1
    print('  All %d lints fire on the defect they exist to catch.' % ok)
    return 0


if __name__ == '__main__':
    code = main()
    if code:
        sys.exit(code)
