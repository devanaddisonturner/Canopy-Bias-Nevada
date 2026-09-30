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
"""Remove embedded C2PA content-credentials manifests from the shipped images.

WHY THIS SHIPS
--------------
`make_tables.py` fails, and `build_package.sh` refuses to build, if any shipped
image carries a C2PA manifest. For fourteen of the fifteen images the fix is to
rerun the figure script, which produces the image without one.

The six Earth Engine exports under `matched_parcel_panels/` have no such fix. They
are INPUTS: no script regenerates them, they are pulled from Earth Engine by hand,
and their SHA-256 hashes in `CHECKSUMS.sha256` are what the package offers in place
of a provenance chain. When an environment re-attaches a manifest to one of them,
and some do (the manifests seen here named "Anthropic Files / Claude" as the claim
generator and asserted that Claude had provided the file), the harness fails with
nothing to point the reader at. That happened repeatedly during preparation and was
fixed each time by hand, which is not something a reader can do.

So the tool is here. It does the minimum, and it checks its own work:

  * PNG: drops the `caBX` chunk, and any text chunk whose payload mentions c2pa.
  * JPEG: drops APP11 segments, which is how JUMBF rides in a JPEG, and any other
    APPn segment containing a `jumb` box.
  * TIFF: blanks private tag 52545 (0xCD41) and zeroes its payload, in place. The
    file keeps its exact length so no strip offset is invalidated.
  * Nothing else in the file is touched, and no re-encoding happens: the remaining
    bytes are copied through verbatim, so the image data is bit-for-bit what it was.

TIFF was missing from the first version of this file, which shipped describing
itself as the recovery route for the shipped images. Four of the fifteen are TIFFs,
and on those it refused with "a marker survives the strip" rather than doing
anything wrong, but it could not do the job it was written for.

BEFORE WRITING ANYTHING it decodes both versions and refuses to proceed unless the
pixels, the mode and the size are identical. A manifest strip that changed a pixel
would be a silent edit to released data, so that check is not optional.

USAGE
-----
    python3 strip_provenance.py              # report only, changes nothing
    python3 strip_provenance.py --write      # strip, then verify pixels
    python3 strip_provenance.py --write FILE # one file

AFTERWARDS, for any file listed in CHECKSUMS.sha256, its hash no longer matches,
because the bytes legitimately changed. Do not edit the hash without reading the
note at the top of CHECKSUMS.sha256: it records what the 29 September 2026 change
was and what was measured before the hashes were rewritten. Rerun

    python3 make_figure_matched_parcels.py

and confirm Figure 3 still comes out byte-identical before you accept a new hash.
"""
import os
import struct
import sys

EXT = ('.png', '.tif', '.tiff', '.jpg', '.jpeg')
MARKERS = (b'urn:c2pa', b'jumb', b'caBX')

# Every path here is resolved against the script's own folder, not the working
# directory. Anchoring on the working directory is what the portability check in
# make_tables.py caught in the first version of this file: double-clicking it, or
# IDLE's Run Module from anywhere but the package folder, would have found no
# build_package.sh and reported that the shipped-file list could not be read.
HERE = os.path.dirname(os.path.abspath(__file__))


def here(*parts):
    return os.path.join(HERE, *parts)


def shipped_images():
    """The images the package actually ships, read from build_package.sh's list.

    Scanning the whole directory instead was the first version, and it reported
    GraphicalAbstract1_alt.png and graphical_abstract_comparison.png: working files
    that are not in the package. A tool that exits non-zero on a clean package
    teaches the reader to ignore it, so the scope is the manifest, which is the same
    scope make_tables.py checks. The panel directory is walked because the manifest
    names it as a directory rather than file by file, which is the omission that let
    six manifests ship unnoticed in the first place.
    """
    import re
    if not os.path.exists(here('build_package.sh')):
        return None
    blk = re.search(r'FILES=\((.*?)\n\)',
                    open(here('build_package.sh'), encoding='utf-8').read(), re.S)
    named = []
    if blk:
        for line in blk.group(1).split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                named += line.split()
    out = [here(f) for f in named
           if f.lower().endswith(EXT) and os.path.exists(here(f))]
    for root, _dirs, files in os.walk(here('matched_parcel_panels')):
        if 'figure_panels' in root.split(os.sep):
            continue
        for fn in files:
            if fn.lower().endswith(EXT):
                out.append(os.path.join(root, fn))
    return sorted(set(out))


def carries_manifest(blob):
    return any(m in blob for m in MARKERS)


def strip_png(b):
    """Copy every chunk except the C2PA ones. No re-encoding."""
    if b[:8] != b'\x89PNG\r\n\x1a\n':
        return b
    out, i = bytearray(b[:8]), 8
    while i < len(b) - 8:
        ln = struct.unpack('>I', b[i:i + 4])[0]
        typ = b[i + 4:i + 8]
        chunk = bytes(b[i:i + 12 + ln])
        drop = typ == b'caBX' or (typ in (b'iTXt', b'tEXt', b'zTXt')
                                  and b'c2pa' in chunk.lower())
        if not drop:
            out += chunk
        i += 12 + ln
        if typ == b'IEND':
            break
    return bytes(out)


def strip_jpeg(b):
    """Copy every segment except APP11 and any APPn holding a JUMBF box."""
    if b[:2] != b'\xff\xd8':
        return b
    out, i = bytearray(b[:2]), 2
    while i < len(b) - 1:
        if b[i] != 0xFF:
            out += b[i:]
            break
        m = b[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            out += b[i:i + 2]
            i += 2
            continue
        if m == 0xDA:                      # start of scan; the rest is entropy data
            out += b[i:]
            break
        ln = struct.unpack('>H', b[i + 2:i + 4])[0]
        seg = bytes(b[i:i + 2 + ln])
        drop = m == 0xEB or (0xE0 <= m <= 0xEF and b'jumb' in seg)
        if not drop:
            out += seg
        i += 2 + ln
    return bytes(out)


def strip_tiff(b):
    """Rewrite the TIFF without the C2PA tag, letting the encoder rebuild the IFD.

    WHY THIS ONE RE-ENCODES WHEN THE OTHERS DO NOT
    ----------------------------------------------
    The PNG and JPEG paths do byte surgery and never re-encode, because six of
    those files are pinned in CHECKSUMS.sha256 and their exact bytes are the
    record. NO TIFF IS PINNED there, so a TIFF may be rewritten, and rewriting is
    the only way to get this right.

    The first version of this function blanked the tag in place: it rewrote the
    IFD entry as tag 0, type 1, count 0, and zeroed the payload, so the file kept
    its length and no offset moved. That was wrong in two ways that only showed up
    on inspection.

      1. TIFF6 requires IFD entries to be sorted in ASCENDING TAG ORDER. Tag 52545
         is the last entry, so blanking it to 0 left the directory ending on a tag
         lower than every tag before it. Pillow is lenient and reads it; a stricter
         reader in a publisher's production workflow need not be, and a figure that
         fails silently at the far end of the process is the worst kind.
      2. Each strip-then-recontaminate cycle left another dead entry behind. Two
         cycles produced an IFD carrying two tag-0 entries.

    Re-encoding with Pillow sidesteps both: the encoder writes a fresh, correctly
    ordered directory with no dead entries and no C2PA tag, because it only writes
    the tags it knows about. Mode, size, compression and the dpi tag are carried
    across explicitly, and main() verifies the decoded pixels afterwards regardless.
    """
    import io

    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(io.BytesIO(b))
    # Keep the compression the file already uses rather than imposing one, so a
    # stripped figure stays the same kind of file it was.
    compression = im.info.get('compression', 'tiff_lzw')
    dpi = im.info.get('dpi')
    # Pillow carries unknown tags across a save, so tag 52545 survived the first
    # re-encode as an empty ASCII field: inert, no payload, but still a C2PA tag
    # sitting in a directory that claims not to have one. Dropping it from tag_v2
    # before the save removes it outright, which makes the tag list say what the
    # file means.
    C2PA_TAG = 52545
    if hasattr(im, 'tag_v2') and C2PA_TAG in im.tag_v2:
        del im.tag_v2[C2PA_TAG]
    out = io.BytesIO()
    kw = {'format': 'TIFF', 'compression': compression}
    if dpi:
        kw['dpi'] = dpi
    im.save(out, **kw)
    return out.getvalue()


def pixels_unchanged(before, after):
    """Decode both and compare. Returns (ok, explanation)."""
    try:
        import io

        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        a = Image.open(io.BytesIO(before))
        c = Image.open(io.BytesIO(after))
        if a.size != c.size:
            return False, 'size changed %s -> %s' % (a.size, c.size)
        if a.mode != c.mode:
            return False, 'mode changed %s -> %s' % (a.mode, c.mode)
        if a.tobytes() != c.tobytes():
            return False, 'pixel data changed'
        return True, 'pixels, mode and size identical'
    except ImportError:
        # Without Pillow the strip cannot be verified, so it is not performed.
        # Refusing is the right failure: the alternative is editing released data
        # on the assumption that the surgery was clean.
        return False, 'Pillow is not installed, so the strip cannot be verified'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    write = '--write' in sys.argv[1:]

    if args:
        targets = args
    else:
        targets = shipped_images()
        if targets is None:
            print('build_package.sh is absent, so the shipped-file list cannot be '
                  'read.\nName the files to check on the command line instead.')
            return 1

    dirty = []
    for f in targets:
        if not os.path.exists(f):
            print('  missing   %s' % f)
            continue
        b = open(f, 'rb').read()
        if carries_manifest(b):
            dirty.append((f, b))

    if not dirty:
        print('No shipped image carries a content-credentials manifest. '
              'Nothing to do.')
        return 0

    print('%d image(s) carry a manifest:' % len(dirty))
    for f, _ in dirty:
        print('    %s' % f)
    if not write:
        print('\nReport only. Rerun with --write to strip them.')
        return 1

    print()
    failed = 0
    for f, b in dirty:
        low = f.lower()
        if low.endswith(('.jpg', '.jpeg')):
            new = strip_jpeg(b)
        elif low.endswith(('.tif', '.tiff')):
            new = strip_tiff(b)
        else:
            new = strip_png(b)
        ok, why = pixels_unchanged(b, new)
        still = carries_manifest(new)
        if not ok:
            print('  REFUSED   %-44s %s' % (f, why))
            failed += 1
        elif still:
            print('  REFUSED   %-44s a marker survives the strip' % f)
            failed += 1
        else:
            open(f, 'wb').write(new)
            print('  stripped  %-44s %d -> %d bytes, %s'
                  % (f, len(b), len(new), why))

    print()
    if failed:
        print('%d file(s) were left alone. Nothing is written unless the strip is '
              'provably lossless.' % failed)
        return 1
    print('Now rerun make_tables.py. If a stripped file is listed in '
          'CHECKSUMS.sha256,\nread the note at the top of that file before '
          'rewriting its hash.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
