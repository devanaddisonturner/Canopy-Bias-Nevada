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


# ---------------------------------------------------------------------------
# Run from anywhere. IDLE's Run Module, a double-click, and
# "python3 /path/to/check_layout.py" all leave the working directory somewhere other than
# this file's folder, and every input below is named relatively. Without this
# the run dies on the first open() with a FileNotFoundError that says nothing
# about the real cause.
# ---------------------------------------------------------------------------
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE and _os.getcwd() != _HERE:
    _os.chdir(_HERE)
#!/usr/bin/env python3
"""Layout checks that can only be made on the rendered PDF.

The verification harness in make_tables.py checks numbers and prose against
the data and the build script. It cannot see pagination. These checks can:

  1. No figure caption is separated from its figure by a page break.
     Figure 2's caption sat on page 6 while its image sat on page 5 until
     keepNext was added to the four image paragraphs.
  2. No numbered heading is left stranded at the foot of a page.
  3. No page opens with a short closing line of the previous paragraph
     (a widow).
  4. No page is nearly empty.

    python3 check_layout.py [canopy_bias_manuscript_GIScienceRS.pdf]

Exits 1 if any check fails, so it can gate a release the same way the
numeric harness does.
"""
import os
import re
import subprocess
import sys

_args = [a for a in sys.argv[1:] if not a.startswith('--')]
PDF = _args[0] if _args else 'canopy_bias_manuscript_GIScienceRS.pdf'
HEAD = re.compile(r'^(Abstract|[1-9]\.\s[A-Z]|[1-9]\.[1-9]\.\s[A-Z]|Acknowledgements|Funding|'
                  r'Disclosure|Declaration|Data availability|Author contributions|'
                  r'References)')
FAIL = []


def page_text(p):
    return subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), PDF, '-'],
                          capture_output=True, text=True).stdout


def page_has_image(p):
    out = subprocess.run(['pdfimages', '-list', '-f', str(p), '-l', str(p), PDF],
                         capture_output=True, text=True).stdout
    return len(out.strip().split('\n')) > 2



def header_alignment(docx):
    """Every cell of every table's header row must be centred, including the
    first column and any column whose body cells carry an alignment override.
    """
    import zipfile
    if not os.path.exists(docx):
        return []
    x = zipfile.ZipFile(docx).read('word/document.xml').decode('utf-8')
    bad = []
    for ti, tbl in enumerate(re.findall(r'<w:tbl>.*?</w:tbl>', x, re.S), 1):
        rows = re.findall(r'<w:tr[ >].*?</w:tr>', tbl, re.S)
        if not rows:
            continue
        for ci, cell in enumerate(re.findall(r'<w:tc>.*?</w:tc>', rows[0], re.S)):
            m = re.search(r'<w:jc w:val="([a-z]+)"', cell)
            if not m or m.group(1) != 'center':
                txt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', cell))[:24]
                bad.append('Table %d col %d "%s" is %s'
                           % (ti, ci + 1, txt, m.group(1) if m else 'unset'))
    return bad



def symbol_typography(docx):
    """Mathematical typography, which only the rendered DOCX shows.

    Scalar variables are italic regardless of alphabet, so Greek variables must
    be italic like the Latin ones; the summation sign stays roman. Every
    cross-reference to an Equation must be bold like every other callout.
    Both failed: beta, gamma, epsilon and kappa were roman, and three Equation
    references inside where-blocks were unbolded against five bolded elsewhere.
    """
    import zipfile
    if not os.path.exists(docx):
        return []
    x = zipfile.ZipFile(docx).read('word/document.xml').decode('utf-8')
    runs = [(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', r)),
             '<w:i/>' in r, '<w:b/>' in r)
            for r in re.findall(r'<w:r>(.*?)</w:r>', x, re.S)]
    bad = []
    for t, ital, _ in runs:
        if re.search(r'[\u03b1-\u03c9]', t) and not ital and '\u03a3' not in t:
            bad.append('roman Greek variable: %r' % t[:34])
    for t, _, bold in runs:
        if re.search(r'\b(Figure|Table|Equation)s?[\s\u00a0]\d', t) and not bold:
            bad.append('unbolded cross-reference: %r' % t[:34])
    # A negative number must use the real minus sign U+2212, not a hyphen.
    # The convention here is the Unicode minus in tables and the word "minus"
    # in prose; both are consistent today, and this keeps an edited table value
    # from quietly reintroducing a hyphen. The pattern is deliberately narrow,
    # so hyphenated compounds and parcel numbers like 045-300-033 do not match.
    for t, _, _ in runs:
        m = re.search(r'(?:^|[\s(=])-\d', t)
        if m:
            bad.append('hyphen used as a minus sign: %r' % t[:34])
    return bad



def document_metadata(docx):
    """docProps must carry the full title and a real name.

    The title was truncated at "built-surface products", dropping the second
    half, and lastModifiedBy read "Un-named".
    """
    import zipfile
    if not os.path.exists(docx):
        return []
    z = zipfile.ZipFile(docx)
    try:
        c = z.read('docProps/core.xml').decode('utf-8')
    except KeyError:
        return ['docProps/core.xml absent']
    bad = []
    got = {}
    for tag in ('dc:title', 'dc:creator', 'cp:lastModifiedBy'):
        m = re.search(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), c, re.S)
        got[tag] = m.group(1) if m else ''
    for tag, val in got.items():
        if not val or 'un-named' in val.lower() or 'unnamed' in val.lower():
            bad.append('%s is %r' % (tag, val))
    # the metadata title must match the title printed on page one
    x = z.read('word/document.xml').decode('utf-8')
    first = re.search(r'<w:t[^>]*>([^<]{40,})</w:t>', x)
    if first and got.get('dc:title') and not got['dc:title'].startswith(first.group(1)[:40]):
        bad.append('dc:title does not match the on-page title')
    return bad


def builder_blocks(builder='build_manuscript.js'):
    """Every text-bearing block in the builder, in document order.

    Extraction is by balanced-paren scan rather than by a single regex. The
    earlier pattern required a call to end in "')" followed by ")", so it
    silently skipped p('...', {opts}) and every pr([...]) block. That hid the
    abstract, the keywords, the affiliation, the corresponding-author line and
    the ORCID from every check built on it: 88 blocks were seen out of 106.
    A checker that quietly inspects four fifths of a document is worse than
    one that admits it cannot read it.
    """
    if not os.path.exists(builder):
        return []
    src = open(builder, encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda m: chr(int(m.group(1), 16)), s).replace("\\'", "'")
    out = []
    for m in re.finditer(r'body\.push\((\w+)\(', src):
        kind = m.group(1)
        i = src.index('(', m.end() - 1)
        depth, j = 0, i
        while j < len(src):
            c = src[j]
            if c == "'":                          # skip over string literals
                j += 1
                while j < len(src) and src[j] != "'":
                    j += 2 if src[j] == '\\' else 1
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        texts = [unesc(s) for s in re.findall(r"'((?:[^'\\]|\\.)*)'", src[i:j + 1])]
        texts = [t for t in texts if not re.fullmatch(r'#[0-9a-fA-F]{3,8}|\s*', t)]
        if texts:
            out.append((kind, ' '.join(texts)))
    return out


def every_block_reaches_the_page(pdf, builder='build_manuscript.js'):
    """Every text block in the builder must actually appear in the rendered PDF.

    Nothing was checking this. The builder could drop a paragraph, or emit one
    the layout never places, and no other check would notice: the numeric
    harness reads the builder's source strings, and the layout checks read the
    PDF, so a block present in one and absent from the other falls between them.

    Page numbers are stripped before matching. They sit in the text stream at
    page boundaries, so a probe spanning a page break otherwise picks up a
    stray digit and reports a false miss.
    """
    if not os.path.exists(pdf):
        return []
    raw = subprocess.run(['pdftotext', '-layout', pdf, '-'],
                         capture_output=True, text=True).stdout
    lines = [l for l in raw.replace('\f', '\n').split('\n') if not l.strip().isdigit()]
    # The first argument is U+00A0, a non-breaking space, written as an escape
    # rather than as the character. It used to be the literal character, which
    # made this read `.replace(' ', ' ')`: two glyphs that are indistinguishable
    # on screen. Any editor that normalises whitespace, any copy and paste
    # through a field that does, turns it into a no-op that still looks correct,
    # and the layout check silently stops folding non-breaking spaces. Nothing
    # would have caught it.
    flat = re.sub(r'\s+', ' ', ' '.join(lines)).replace('\u00a0', ' ')
    bad = []
    for kind, t in builder_blocks(builder):
        if kind in ('eq', 'where', 'makeTable'):
            continue
        probe = re.sub(r'\s+', ' ', t).strip()
        if len(probe) < 25:
            continue
        mid = probe[len(probe) // 3:len(probe) // 3 + 45]
        if mid and mid not in flat:
            bad.append('%s block not found in the PDF: %r' % (kind, probe[:56]))
    return bad


def paragraph_balance(builder='build_manuscript.js', cap=260, ratio=6.0):
    """Paragraphs a reader cannot get through, and sections that lurch between
    very long and very short ones.

    Section 2.3 ran a 278-word paragraph against a 45-word one, and five
    paragraphs in the paper exceeded 220 words. Splitting at sentence
    boundaries fixed it without changing a word. A short paragraph used for
    emphasis is legitimate, so the ratio threshold is set loosely and only
    catches a section that has drifted badly.

    The Abstract is exempt. It is one paragraph by the journal's own
    requirement, it cannot be split, and its length is governed by the 500-word
    limit rather than by readability, which it meets at 337.
    """
    EXEMPT = {'Abstract'}
    cur, secs, bad = None, {}, []
    for kind, t in builder_blocks(builder):
        if kind in ('h1', 'h2'):
            cur = t.strip()
            if cur not in EXEMPT:
                secs.setdefault(cur, [])
        elif cur is not None and cur not in EXEMPT and kind == 'p':
            secs[cur].append(len(t.split()))
    for sec, w in secs.items():
        for n in w:
            if n > cap:
                bad.append('%s has a %d-word paragraph (cap %d)' % (sec[:40], n, cap))
        if len(w) > 1 and max(w) / min(w) > ratio:
            bad.append('%s paragraphs range %d to %d words' % (sec[:40], min(w), max(w)))
    return bad


def equation_symbols(builder='build_manuscript.js'):
    """Every variable in an equation must be defined in a where-block.

    Equation 4, the estimating equation, used gamma and epsilon and named
    neither, and left beta-zero unlabelled. In a methods paper that is the
    kind of gap a referee returns the manuscript over.

    Variables are identified by the italic flag rather than by guessing from
    the characters: in this builder `i: true` marks a scalar variable, and
    operators and function names such as "min" are set roman. A symbol defined
    for an earlier equation stays defined, so the scope accumulates.
    """
    if not os.path.exists(builder):
        return []
    src = open(builder, encoding='utf-8').read()
    unesc = lambda s: re.sub(r'\\u([0-9a-fA-F]{4})',
                             lambda m: chr(int(m.group(1), 16)), s).replace("\\'", "'")
    eqs = []
    for m in re.finditer(r'body\.push\(eq\(\[(.*?)\],\s*(\d)\)\)', src, re.S):
        ital = re.findall(r"\{\s*t:\s*'((?:[^'\\]|\\.)*)'[^}]*\bi:\s*true[^}]*\}", m.group(1))
        eqs.append((int(m.group(2)), {unesc(t) for t in ital if unesc(t).strip()}, m.end()))
    wheres = [(m.start(), ''.join(unesc(t) for t in
              re.findall(r"t:\s*'((?:[^'\\]|\\.)*)'", m.group(1))))
              for m in re.finditer(r'body\.push\(where\(\[(.*?)\]\)\)', src, re.S)]
    bad, scope = [], ''
    for num, syms, pos in eqs:
        following = [w for p, w in wheres if p > pos]
        if not following:
            bad.append('Equation %d has no where-block' % num)
            continue
        scope += following[0]
        for s in sorted(syms):
            if s not in scope:
                bad.append('Equation %d uses %r with no definition' % (num, s))
    return bad


def table_structure(docx):
    """Table widths and the repeating-header flag.

    Word repeats a row at the top of a continuation page only if that row
    carries w:tblHeader. Adding it via docx-js is a trap: the library emits
    <w:tblHeader/> whenever the key is present, even when its value is false,
    so `tableHeader: isHead` silently marked every body row as a header, which
    would repeat the entire table on a split instead of just its header. The
    flag must appear on the first row of each table and on no other.

    Widths are checked too: the grid, the table width and every header cell
    must agree, in DXA, since a percentage-based or mismatched width renders
    differently outside Word.
    """
    import zipfile
    if not os.path.exists(docx):
        return []
    x = zipfile.ZipFile(docx).read('word/document.xml').decode('utf-8')
    bad = []
    for i, t in enumerate(re.findall(r'<w:tbl>.*?</w:tbl>', x, re.S), 1):
        rows = re.findall(r'<w:tr[ >].*?</w:tr>', t, re.S)
        marked = [j + 1 for j, r in enumerate(rows) if '<w:tblHeader' in r]
        if marked != [1]:
            bad.append('Table %d marks rows %s as repeating headers, expected [1]'
                       % (i, marked))
        if not all('<w:cantSplit' in r for r in rows):
            bad.append('Table %d has a row that may split across a page' % i)
        grid = [int(v) for v in re.findall(r'<w:gridCol[^>]*w:w="(\d+)"', t)]
        cells = [int(m.group(1)) for m in re.finditer(r'<w:tcW[^>]*?w:w="(\d+)"', rows[0])]
        tw = re.search(r'<w:tblW[^>]*w:w="(\d+)"', t)
        if not tw or int(tw.group(1)) != sum(grid):
            bad.append('Table %d width %s does not match its grid sum %d'
                       % (i, tw.group(1) if tw else 'unset', sum(grid)))
        if cells and sum(cells) != sum(grid):
            bad.append('Table %d header cell widths %d do not match the grid %d'
                       % (i, sum(cells), sum(grid)))
    return bad


def placeholders(builder='build_manuscript.js'):
    """Bracketed placeholders still in the manuscript.

    Outstanding placeholders are by design until the deposit and funding details
    exist, so this is reported rather than fatal during drafting. The count is
    deliberately not written here: this docstring said "Four are outstanding" for
    a fortnight after the number changed, which is the same staleness the shipped
    checklists carried. Run with
    --submission to make it fatal, which is the check to do immediately before
    uploading: a manuscript submitted with "[insert the DOI here]" still in the
    data availability statement is the kind of error no reviewer forgives.
    """
    out, cur = [], None
    for kind, t in builder_blocks(builder):
        if kind in ('h1', 'h2'):
            cur = t
            continue
        # Equations legitimately use square brackets: Equation 3 carries the
        # indicator "1[P_c < B_c]". Only prose blocks are scanned, and the
        # bracket must read like a sentence rather than like notation.
        if kind not in ('p', 'caption'):
            continue
        for m in re.finditer(r'\[[^\]]{8,240}\]', t):
            inner = m.group(0)
            if len(re.findall(r'\b[a-z]{3,}\b', inner)) < 3:
                continue
            out.append('%s: %s' % ((cur or '?')[:34], inner[:90]))
    return out


def main():
    # Every check here reads the rendered PDF, so poppler is not optional for
    # this script the way it is for the numeric harness. Say so in one line
    # instead of dying in subprocess with a bare FileNotFoundError.
    import shutil
    missing = [t for t in ('pdftotext', 'pdfinfo', 'pdfimages')
               if shutil.which(t) is None]
    if missing:
        print('These layout checks need poppler, which supplies %s.'
              % ', '.join(missing))
        print('  Debian or Ubuntu:  sudo apt-get install poppler-utils')
        print('  macOS:             brew install poppler')
        print('  Windows:           install poppler and put its bin/ on PATH')
        print('\nThe numeric harness, make_tables.py, does not need it and still runs.')
        return 1
    if not os.path.exists(PDF):
        print('no PDF at %s; render it first' % PDF)
        return 1
    info = subprocess.run(['pdfinfo', PDF], capture_output=True, text=True).stdout
    n = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    print('LAYOUT CHECKS  %s, %d pages' % (PDF, n))

    # The reference list is exempt from the widow check. Its entries are set with
    # a hanging indent and routinely break across a page, so a short line ending
    # in a period at the top of a page is an entry's middle, not a paragraph's
    # tail: the OEHHA entry broke with "California Environmental Protection
    # Agency." atop a page and its URL on the line below, which the heuristic
    # read as a widow. Journals typeset the reference list themselves in any
    # case. The check still runs over every page of the body, which is where a
    # stranded closing line is a real defect.
    refs_from = n + 1
    for p in range(1, n + 1):
        if re.search(r'^\s*References\s*$', page_text(p), re.M):
            refs_from = p
            break

    sep, orphan, widow, empty = [], [], [], []
    for p in range(1, n + 1):
        lines = [l.strip() for l in page_text(p).split('\n')
                 if l.strip() and not l.strip().isdigit()]
        if not lines:
            continue
        if len(lines) <= 3:
            empty.append((p, len(lines)))
        for l in lines:
            if re.match(r'^Figure \d\.', l) and not page_has_image(p):
                sep.append((p, l[:55]))
        if HEAD.match(lines[-1]) and len(lines[-1].split()) <= 9:
            orphan.append((p, lines[-1][:55]))
        if (p < refs_from and len(lines[0].split()) <= 5
                and lines[0].endswith('.')):
            widow.append((p, lines[0][:55]))

    # Several checks below read the .docx. If it is missing they each return an
    # empty list, which reads as a pass. Fail loudly instead: a silent pass on a
    # file that is not there is worse than no check at all.
    docx = PDF[:-4] + '.docx'
    if not os.path.exists(docx):
        print('   FAIL  %s absent, so the DOCX checks cannot run' % docx)
        return 1

    # The page count is stated in prose in two shipped documents and was stated
    # nowhere that a check could see. Adding one Table 4 row took the manuscript
    # from 22 pages to 23 and left both of them wrong. The rendered PDF is the
    # authority, so the claims are read back against it.
    pagecount = []
    for doc in ('README.md', 'SUBMISSION_CHECKLIST.md'):
        if not os.path.exists(doc):
            continue
        for m in re.finditer(r'manuscript(?:,| is) (\d+) pages',
                             open(doc, encoding='utf-8').read()):
            if int(m.group(1)) != n:
                pagecount.append('%s says %s pages, the PDF has %d' % (doc, m.group(1), n))

    hdr = header_alignment(PDF[:-4] + '.docx')
    sym = symbol_typography(PDF[:-4] + '.docx')
    meta = document_metadata(PDF[:-4] + '.docx')
    para = paragraph_balance()
    holes = placeholders()
    dropped = every_block_reaches_the_page(PDF)
    tstruct = table_structure(PDF[:-4] + '.docx')
    eqsym = equation_symbols()
    for label, hits in (('figure caption split from its figure', sep),
                        ('table header cell not centred', hdr),
                        ('symbol or callout typography', sym),
                        ('document metadata', meta),
                        ('paragraph length and balance', para),
                        ('table widths and header repeat', tstruct),
                        ('equation symbols defined', eqsym),
                        ('every block reaches the page', dropped),
                        ('heading stranded at a page foot', orphan),
                        ('widowed closing line atop a page', widow),
                        ('near-empty page', empty),
                        ('page count as the shipped docs state it', pagecount)):
        if hits:
            FAIL.append((label, hits[0]))
            print('   FAIL  %-38s %s' % (label, hits[0]))
        else:
            print('   ok    %s' % label)

    if holes:
        fatal = '--submission' in sys.argv
        print('   %s %d bracketed placeholder(s) still in the manuscript:'
              % ('FAIL ' if fatal else 'NOTE ', len(holes)))
        for h in holes:
            print('          %s' % h)
        if fatal:
            FAIL.append(('bracketed placeholder', holes[0]))
    else:
        print('   ok    no bracketed placeholders remain')

    print('=' * 60)
    if FAIL:
        print('%d layout problem(s).' % len(FAIL))
        return 1
    print('Layout is clean.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
