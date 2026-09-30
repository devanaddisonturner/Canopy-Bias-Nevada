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
# "python3 /path/to/check_colours.py" all leave the working directory somewhere other than
# this file's folder, and every input below is named relatively. Without this
# the run dies on the first open() with a FileNotFoundError that says nothing
# about the real cause.
# ---------------------------------------------------------------------------
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE and _os.getcwd() != _HERE:
    _os.chdir(_HERE)
#!/usr/bin/env python3
"""Colour-vision and contrast checks on the figures.

The numeric harness in make_tables.py checks values, and check_layout.py checks
pagination. Neither can see whether a reader can actually tell two series
apart. These checks can, and they found three real defects:

  1. The gap annotation (#a01b20) sat 39 from the product colour (#b8560f)
     under simulated tritanopia, below the separation threshold of 40.
  2. Figure 3's red cell marker separated by only 24 from the darkest colour of
     the green canopy ramp, in the closed-canopy panel that the figure exists
     to show.
  3. Figure 1's red site marker was worse: separation 8, and 1.30:1 luminance
     contrast against the darkest ramp colour, which fails the 3:1 graphics
     threshold for every reader, colour-blind or not, and disappears in
     greyscale printing.

Dichromacy is simulated by the Vienot, Brettel and Mollon (1999) LMS method.
Separation is Euclidean distance in 0-255 sRGB, taken as the worst case over
normal vision and all three dichromacies; 40 is the confusion threshold used
here. Luminance contrast is the WCAG 2.1 ratio, with 3:1 the threshold for
graphical objects.

    python3 check_colours.py

Exits 1 if any check fails, so it gates a release like the other two.
"""
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEP_MIN = 40.0        # dichromat confusion threshold, worst case over all types
CR_MIN = 3.0          # WCAG 2.1 threshold for graphical objects (4.5 is for text)
GREY_MIN = 2.2        # luminance ratio between two series, for greyscale printing
FAIL = []

# ---------------------------------------------------------------- colour maths
_R2L = np.array([[17.8824, 43.5161, 4.1193],
                 [3.4557, 27.1554, 3.8671],
                 [0.02996, 0.18431, 1.4670]])
_L2R = np.linalg.inv(_R2L)
_SIM = {'protanopia':   np.array([[0, 2.02344, -2.52581], [0, 1, 0], [0, 0, 1]]),
        'deuteranopia': np.array([[1, 0, 0], [0.494207, 0, 1.24827], [0, 0, 1]]),
        'tritanopia':   np.array([[1, 0, 0], [0, 1, 0], [-0.395913, 0.801109, 0]])}


def rgb(h):
    if not isinstance(h, str):
        return np.asarray(h, float)
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255


def _lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def simulate(c, kind):
    """Dichromat appearance of a colour. Clipped, because unclipped powers of
    out-of-gamut LMS values overflow and produce meaningless distances."""
    return np.clip(_srgb(_L2R @ (_SIM[kind] @ (_R2L @ _lin(rgb(c))))), 0, 1)


def separation(a, b):
    """Worst-case sRGB distance over normal vision and all three dichromacies."""
    A, B = rgb(a), rgb(b)
    d = [float(np.linalg.norm((A - B) * 255))]
    d += [float(np.linalg.norm((simulate(A, k) - simulate(B, k)) * 255)) for k in _SIM]
    return min(d)


def luminance(c):
    l = _lin(rgb(c))
    return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def over_white(c, alpha):
    """What the reader sees for a semi-transparent fill, which is the colour
    that must be checked, not the fill's nominal value."""
    return 1 - alpha * (1 - rgb(c))


# ------------------------------------------------------- 1. source-level rules
def literal(path, name):
    """Read a colour constant out of a figure script, so the check tracks the
    script instead of a copy of its values that could drift.

    Parsed with ast rather than by regex. A regex reading the line
    "BOUND_C, NLCD_C = '#005A8F', '#A8480A'" returns the first hex string for
    both names, which made this check compare the blue against itself and
    report a separation of zero.
    """
    import ast
    tree = ast.parse(open(os.path.join(HERE, path), encoding='utf-8').read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            names = tgt.elts if isinstance(tgt, (ast.Tuple, ast.List)) else [tgt]
            vals = (node.value.elts
                    if isinstance(node.value, (ast.Tuple, ast.List))
                    and len(getattr(node.value, 'elts', [])) == len(names)
                    else [node.value] * len(names))
            for nm, vl in zip(names, vals):
                if isinstance(nm, ast.Name) and nm.id == name \
                        and isinstance(vl, ast.Constant) and isinstance(vl.value, str) \
                        and re.fullmatch(r'#[0-9a-fA-F]{6}', vl.value):
                    return vl.value
    return None


def literal_num(path, name):
    """The same, for a numeric constant such as a fill alpha."""
    import ast
    tree = ast.parse(open(os.path.join(HERE, path), encoding='utf-8').read())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            names = tgt.elts if isinstance(tgt, (ast.Tuple, ast.List)) else [tgt]
            vals = (node.value.elts
                    if isinstance(node.value, (ast.Tuple, ast.List))
                    and len(getattr(node.value, 'elts', [])) == len(names)
                    else [node.value] * len(names))
            for nm, vl in zip(names, vals):
                if isinstance(nm, ast.Name) and nm.id == name \
                        and isinstance(vl, ast.Constant) \
                        and isinstance(vl.value, (int, float)):
                    return float(vl.value)
    return None


def check_cooccurring_sets():
    """Colours only have to be distinguishable from the ones drawn beside them,
    so each panel is checked as its own set."""
    dv, ga = 'make_figure_divergence.py', 'make_graphical_abstract.py'
    sets = []
    for path in (dv, ga):
        # Every colour is read from the script. Holding copies here is how a
        # check passes while the figure it is meant to guard has changed: an
        # earlier draft hard-coded the annotation colour and so would not have
        # noticed a revert to the crimson that failed in the first place.
        vals = {k: literal(path, k) for k in ('BOUND_C', 'NLCD_C', 'GAP_C', 'FILL_C')}
        alpha = literal_num(path, 'FILL_A')
        missing = [k for k, v in vals.items() if not v] + ([] if alpha else ['FILL_A'])
        if missing:
            FAIL.append('%s: palette constant(s) %s absent, so the colours in '
                        'that figure are unchecked' % (path, ', '.join(missing)))
            continue
        s = {'bound': vals['BOUND_C'], 'product': vals['NLCD_C'],
             'annotation': vals['GAP_C'],
             'shaded band as composited': over_white(vals['FILL_C'], alpha)}
        sets.append(('%s series panel' % path, s))
    sets.append(('make_figure_divergence.py panel (b)',
                 {'failure rate': '#d62728', 'zero-impervious rate': '#7b3294'}))
    for label, s in sets:
        keys = list(s)
        bad, worst = [], 1e9
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                d = separation(s[keys[i]], s[keys[j]])
                worst = min(worst, d)
                if d < SEP_MIN:
                    bad.append('%s: %s vs %s separate by only %.0f (need %.0f)'
                               % (label, keys[i], keys[j], d, SEP_MIN))
        FAIL.extend(bad)
        print('   %s %-44s worst pair %3.0f'
              % ('FAIL ' if bad else 'ok   ', label, worst))
    # the band must also be visible against the page
    band = over_white(literal(ga, 'FILL_C') or '#d62728', literal_num(ga, 'FILL_A') or 0.17)
    d = separation(band, [1., 1., 1.])
    if d < SEP_MIN:
        FAIL.append('shaded band separates from white by only %.0f' % d)
    else:
        print('   ok    %-44s %3.0f' % ('shaded band against white', d))


def check_greyscale():
    """Two series that print as the same grey are useless in black and white.

    This axis was missed at first, and missing it cost something: an earlier
    palette change raised colour-blind separation from 110 to 129 while
    quietly dropping greyscale contrast from 1.81:1 to 1.26:1, which is two
    lines in nearly the same grey. Optimising one axis without measuring the
    others is how that happens, so it is measured here.
    """
    for path in ('make_figure_divergence.py', 'make_graphical_abstract.py'):
        bd, pr = literal(path, 'BOUND_C'), literal(path, 'NLCD_C')
        if not (bd and pr):
            continue
        c = contrast(bd, pr)
        if c < GREY_MIN:
            FAIL.append('%s: the two series differ by only %.2f:1 in luminance, '
                        'so they print as nearly the same grey (need %.1f:1)'
                        % (path, c, GREY_MIN))
            print('   FAIL  %-44s %.2f:1' % ('%s greyscale' % path, c))
        else:
            print('   ok    %-44s %.2f:1' % ('%s greyscale' % path, c))


def check_markers_over_ramps():
    """A marker drawn over a colour ramp must either hold 3:1 contrast against
    every ramp colour, or carry a white casing. Both map figures failed this on
    contrast alone, so both must declare a halo."""
    cases = [('make_figure_matched_parcels.py', 'Figure 3 cell and centroid markers', '#d62728',
              ['#ffffff', '#e8f3e0', '#b7dba0', '#74c476', '#31a354', '#006d2c', '#00441b']),
             ('make_figure_studyarea.py', 'Figure 1 site markers', '#d62728',
              ['#f2f2f0', '#cfe3c2', '#8fca86', '#3f9c46', '#10612a'])]
    for path, label, marker, ramp in cases:
        src = open(os.path.join(HERE, path), encoding='utf-8').read()
        worst_cr = min(contrast(marker, g) for g in ramp)
        worst_sep = min(separation(marker, g) for g in ramp)
        haloed = 'HALO' in src and 'withStroke' in src and 'path_effects=HALO' in src
        if worst_cr < CR_MIN or worst_sep < SEP_MIN:
            if not haloed:
                FAIL.append('%s: worst contrast %.2f:1, worst separation %.0f, '
                            'and no white casing declared' % (label, worst_cr, worst_sep))
            else:
                print('   ok    %-44s %.2f:1 bare, rescued by a white casing'
                      % (label, worst_cr))
        else:
            print('   ok    %-44s %.2f:1 unaided' % (label, worst_cr))


# ------------------------------------------------- 2. rendered-pixel verification
def check_halo_is_rendered():
    """Verify the casing in the output, not just in the source.

    path_effects is easy to set and easy to have silently not apply to markers,
    so the rendered PNG is measured: nearly every red marker pixel must have a
    near-white pixel within a couple of pixels of it.
    """
    try:
        from PIL import Image
    except ImportError:
        print('   skip  Pillow absent, cannot verify rendered halos')
        return
    for png, label in (('figure_matched_parcels.png', 'Figure 3'),
                       ('figure_studyarea.png', 'Figure 1')):
        p = os.path.join(HERE, png)
        if not os.path.exists(p):
            print('   skip  %s not rendered yet' % png)
            continue
        a = np.asarray(Image.open(p).convert('RGB'), float)
        red = (np.linalg.norm(a - rgb('#d62728') * 255, axis=2) < 60)
        # Keep only stroke pixels. Figure 1 also fills Nevada County solid red
        # in its California inset, and the interior of a solid fill has no white
        # beside it by design, so counting it would understate the casing.
        dens = np.zeros(red.shape, float)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                dens += np.roll(np.roll(red, dy, 0), dx, 1)
        red &= (dens / 49.0) < 0.62
        if red.sum() < 50:
            FAIL.append('%s: found only %d red marker stroke pixels'
                        % (label, int(red.sum())))
            continue
        white = (a.min(axis=2) > 232)
        # dilate the white mask by 3 px without scipy
        near = np.zeros_like(white)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                near |= np.roll(np.roll(white, dy, 0), dx, 1)
        frac = float((red & near).sum()) / float(red.sum())
        if frac < 0.95:
            FAIL.append('%s: only %.0f%% of red marker pixels have white within '
                        '3 px, so the casing is not rendering' % (label, 100 * frac))
        else:
            print('   ok    %-44s %.0f%% of marker pixels cased in white'
                  % ('%s rendered halo' % label, 100 * frac))


def check_variants_agree():
    """Each figure ships as a PNG, a TIFF and sometimes a vector PDF. They must
    all show the same picture.

    Nothing was checking this. The palette changed several times, and a TIFF or
    PDF regenerated one run late would have shipped the superseded colours to a
    production editor while the PNG in the manuscript showed the current ones.
    Comparing whole variants rather than just the palette catches any staleness,
    not only a colour change.
    """
    import shutil
    import subprocess
    try:
        from PIL import Image
    except ImportError:
        print('   skip  Pillow absent, cannot compare figure variants')
        return
    Image.MAX_IMAGE_PIXELS = None

    # Both variants are resampled to one fixed size. Requiring identical pixel
    # dimensions was too strict: rasterising a PDF at 150 dpi rounds, so the
    # same figure came back 1110x773 against 4440x3089, an aspect difference of
    # 0.0014 that is rounding and not a different picture.
    BOX = (480, 320)

    def load(path):
        if path.endswith('.pdf'):
            out = os.path.join(HERE, '_variant_tmp')
            try:
                subprocess.run(['pdftoppm', '-r', '300', '-png', '-singlefile',
                                path, out], capture_output=True)
            except FileNotFoundError:
                # poppler absent, common on Windows. The PNG and TIFF variants
                # are still compared; only the vector PDF is skipped.
                return None, None
            path = out + '.png'
            if not os.path.exists(path):
                return None, None
        im = Image.open(path).convert('RGB')
        aspect = im.size[0] / im.size[1]
        return np.asarray(im.resize(BOX, Image.LANCZOS), float), aspect

    # Derived from the manuscript, not hand-listed. A fifth figure added to the
    # paper would otherwise have its variants unchecked, silently. Same reason
    # as in make_tables.py::manuscript_figures(): the question is about the
    # figures that appear in the paper, and the paper is where that is written
    # down. Falls back to the hand list only if the builder is absent, and says
    # so, because a check that quietly narrows to nothing is worse than one that
    # fails.
    builder = os.path.join(HERE, 'build_manuscript.js')
    stems = []
    if os.path.exists(builder):
        src = open(builder, encoding='utf-8').read()
        for n in re.findall(r"readFileSync\(path\.join\(HERE,\s*'(figure_[\w-]+)\.png'\)\)", src):
            if n not in stems:
                stems.append(n)
    if len(stems) < 4:
        print('   note  only %d figure(s) derived from the manuscript; falling '
              'back to the known four' % len(stems))
        stems = ['figure_studyarea', 'figure_schematic',
                 'figure_matched_parcels', 'figure_divergence']
    for stem in stems:
        png = os.path.join(HERE, stem + '.png')
        if not os.path.exists(png):
            continue
        base, base_aspect = load(png)
        for ext in ('.tif', '.pdf'):
            other = os.path.join(HERE, stem + ext)
            if not os.path.exists(other):
                continue
            got, aspect = load(other)
            if got is None:
                # A vector PDF that cannot be rasterised because poppler is not
                # installed is a missing tool, not a defective figure. Windows
                # has no poppler by default and that is where IDLE is most used.
                if ext == '.pdf' and shutil.which('pdftoppm') is None:
                    print('   .     %-44s skipped, pdftoppm not installed'
                          % (stem + ext))
                else:
                    FAIL.append('%s%s could not be read' % (stem, ext))
                    print('   FAIL  %-44s unreadable' % (stem + ext))
                continue
            if abs(aspect - base_aspect) > 0.01:
                FAIL.append('%s%s has aspect %.4f against the PNG\'s %.4f, so it is '
                            'a different crop' % (stem, ext, aspect, base_aspect))
                print('   FAIL  %-44s aspect %.4f vs %.4f'
                      % (stem + ext, aspect, base_aspect))
                continue
            diff = float(np.abs(got - base).mean())
            # Rasterising a vector PDF never reproduces the PNG exactly. At
            # 300 dpi the honest variants sit at 0.0 to 3.0 grey levels, and a
            # genuinely different figure is far above that, so 6.0 leaves room
            # for antialiasing without admitting a stale file.
            if diff > 6.0:
                FAIL.append('%s%s differs from its PNG by %.1f grey levels on '
                            'average, so one of them is stale' % (stem, ext, diff))
                print('   FAIL  %-44s mean difference %.1f' % (stem + ext, diff))
            else:
                print('   ok    %-44s matches its PNG (mean diff %.1f)'
                      % (stem + ext, diff))
    for tmp in ('_variant_tmp.png',):
        p = os.path.join(HERE, tmp)
        if os.path.exists(p):
            os.remove(p)


def main():
    print('COLOUR CHECKS   separation %.0f, contrast %.1f:1, greyscale %.1f:1'
          % (SEP_MIN, CR_MIN, GREY_MIN))
    check_cooccurring_sets()
    check_greyscale()
    check_markers_over_ramps()
    check_halo_is_rendered()
    check_variants_agree()
    print('=' * 68)
    if FAIL:
        for f in FAIL:
            print('   FAIL  %s' % f)
        print('%d colour problem(s).' % len(FAIL))
        return 1
    print('Colour use is legible under normal vision, all three dichromacies '
          'and greyscale.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
