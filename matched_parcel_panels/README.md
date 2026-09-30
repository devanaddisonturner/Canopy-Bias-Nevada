# The six Google Earth Engine panel exports

*Devan Cantrell Addison-Turner, ORCID [0000-0002-2511-3680](https://orcid.org/0000-0002-2511-3680), Department of Civil and Environmental Engineering, Stanford University. From the reproduction package for "An optically independent administrative reference for validating built-surface products, and the tree-canopy bias it reveals", prepared for GIScience & Remote Sensing. Repository: https://github.com/devanaddisonturner/Canopy-Bias-Nevada Code MIT, released data CC0 1.0.*

These six images are what Figure 3 is composed from. They are the only files in
this package that are **inputs with no script that regenerates them**, which makes
them the ones worth explaining.

| File | Parcel | Layer |
|---|---|---|
| `high_naip_j.jpg` | the canopied parcel | NAIP aerial imagery, 24 July 2020 |
| `high_canopy.png` | the canopied parcel | Meta and WRI canopy height |
| `high_imp.png` | the canopied parcel | NLCD 2019 percent impervious |
| `low_naip_j.jpg` | the open parcel | NAIP aerial imagery, 24 July 2020 |
| `low_canopy.png` | the open parcel | Meta and WRI canopy height |
| `low_imp.png` | the open parcel | NLCD 2019 percent impervious |

Each is 633 x 633 pixels. `make_figure_matched_parcels.py` prints them at
2.1068 inches wide, so 633 / 2.1068 gives 300.5 dpi: that is why Figure 3 is saved
at 300 dpi rather than the 600 used for the drawn figures. A 600 dpi save would
upsample a 633 px source to 1264 px and add nothing.

## Where they came from, and why they are not regenerated

They were pulled from Google Earth Engine by `gee_matched_parcel_panels.js`, which
returns `getThumbURL` links rather than writing files. Fetching those links is a
manual step, and the thumbnail service does not guarantee byte-identical output on
a later call, so the exports are **released as data** rather than rebuilt.

That is why all six are pinned in `CHECKSUMS.sha256`. Those hashes are the
provenance chain a script would otherwise provide, and `make_tables.py` verifies
every one on every run.

## If a hash ever fails

Do not rewrite the hash to match the file. Find out what changed first.

The one cause seen so far is a file transfer attaching a C2PA content-credentials
manifest, which adds about 5,770 bytes without altering a single pixel.
`strip_provenance.py` removes it and refuses to write unless it has decoded both
versions and confirmed the pixels, mode and size are unchanged. After running it,
the hashes match again with nothing rewritten, which is the evidence that the
strip is exactly inverse to the contamination.

The note at the top of `CHECKSUMS.sha256` records the one occasion these six
hashes were legitimately changed, and what was measured before they were.
