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
run_all.py  -  one entry point that verifies the whole package.

WHY THIS EXISTS
---------------
Verifying the package meant knowing which of a dozen scripts to run and in what
order. This runs them all and prints one verdict. It is also the file to open in
IDLE: File, Open, run_all.py, then Run Module or F5. No arguments are needed and
none are read, so it behaves identically whether it is launched from IDLE, from
a double-click, or from a terminal in any working directory.

WHAT IT RUNS
------------
  make_tables.py     the numeric harness, 522 assertions against the released data
  check_layout.py    the rendered manuscript's typography and pagination
  check_colours.py   dichromacy and greyscale legibility of every figure
  verify_in_r.R      the headline results, independently reimplemented in R
  test_harness.py    whether each lint fires on the defect it exists to catch

WHAT IT COSTS
-------------
About 70 seconds and under half a gigabyte, measured rather than guessed, on a
clean unzip and timed more than once. Output is streamed rather than captured so
the run visibly progresses: in IDLE a script that prints nothing for a minute
reads as a freeze.

  make_tables.py    ~59 s, peak 450 MB      check_colours.py  ~3 s, peak 425 MB
  verify_in_r.R     ~5 s,  peak 450 MB      check_layout.py   under 1 s
  test_harness.py   under 1 s

The harness peak was 353 MB when it made 376 assertions and has grown with the
checks added since. It is still under half a gigabyte, but the margin is smaller
than it was, and this is the step to watch on a memory-constrained machine.

Both Conley implementations were peaking near 950 MB before being chunked, which
is enough to be killed on a modest laptop and did kill one verification run in
this project. Chunk size is CONLEY_BLOCK in make_tables.py and BLOCK in
verify_in_r.R; lower either if memory is tight, at some cost in speed. The
estimates do not change: only the order of summation does.

WHAT IT TOLERATES
-----------------
Two of these depend on things a Windows or minimal install may not have, and
neither absence is a defect in the package:

  poppler   supplies pdftotext, pdfinfo, pdfimages and pdftoppm. Without it the
            layout checks cannot run at all and the numeric harness skips its
            PDF-currency check. The numeric result is unaffected.
  R         only verify_in_r.R needs it. Its absence is reported, not failed.

Anything else that fails is a real failure and this exits non-zero.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Each entry: label, command, and whether a missing interpreter or tool is a
# tolerated skip rather than a failure.
STEPS = [
    ('numeric harness   (make_tables.py)',
     [sys.executable, os.path.join(HERE, 'make_tables.py')], None),
    # --allow-missing is added below when poppler is absent: the harness then
    # skips its PDF-currency check, and a skip this script has already reported
    # at the top should not also be reported as a failure.
    ('layout checks     (check_layout.py)',
     [sys.executable, os.path.join(HERE, 'check_layout.py')], 'pdftotext'),
    ('colour checks     (check_colours.py)',
     [sys.executable, os.path.join(HERE, 'check_colours.py')], None),
    ('R reimplementation (verify_in_r.R)',
     ['Rscript', os.path.join(HERE, 'verify_in_r.R')], 'Rscript'),
    ('harness self-test  (test_harness.py)',
     [sys.executable, os.path.join(HERE, 'test_harness.py')], None),
]


def main():
    print('Verifying the canopy-bias reproduction package')
    print('  python   %s' % sys.version.split()[0])
    print('  folder   %s' % HERE)
    print('  poppler  %s' % ('found' if shutil.which('pdftotext') else
                             'NOT FOUND, layout checks will be skipped'))
    print('  R        %s' % ('found' if shutil.which('Rscript') else
                             'NOT FOUND, the R check will be skipped'))
    print()

    failed, skipped = [], []
    for label, cmd, needs in STEPS:
        if needs and shutil.which(needs) is None:
            print('  SKIP  %s   (%s is not installed)' % (label, needs))
            skipped.append(label)
            continue
        # Output is streamed rather than captured: in IDLE the point is to watch
        # it, and a captured run that prints only at the end looks like a hang.
        print('  ---- %s ----' % label)
        if 'make_tables.py' in cmd[-1] and shutil.which('pdftotext') is None:
            cmd = cmd + ['--allow-missing']
        rc = subprocess.call(cmd, cwd=HERE)
        if rc == 0:
            print('  PASS  %s\n' % label)
        else:
            print('  FAIL  %s   (exit %d)\n' % (label, rc))
            failed.append(label)

    print('=' * 72)
    for s in skipped:
        print('  skipped: %s' % s)
    if failed:
        for f in failed:
            print('  FAILED:  %s' % f)
        print('\n%d of %d checks failed.' % (len(failed), len(STEPS) - len(skipped)))
        return 1
    print('  All %d checks that could run passed.'
          % (len(STEPS) - len(skipped)))
    if skipped:
        print('  %d were skipped for a missing tool, not for a defect.' % len(skipped))
    return 0


if __name__ == '__main__':
    code = main()
    # IDLE keeps its shell open after a script ends, and sys.exit() there raises
    # SystemExit into the shell where it reads as an error. Exit quietly when
    # there is nothing to report to a calling process.
    if code:
        sys.exit(code)
