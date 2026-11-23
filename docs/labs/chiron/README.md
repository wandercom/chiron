# Chiron on Wander Labs

This directory is the source and standalone preview for the Chiron landing page at
`https://labs.wander.com/chiron`. The page describes the current Factory workflow
without claiming that independent tests prove correctness or that Chiron merges or
deploys a candidate. The command is named `factory` in the current CLI.

Preview from this repository with Python's static server:

```sh
python3 -m http.server 8770 --bind 127.0.0.1 --directory docs/labs
# Open http://127.0.0.1:8770/chiron/
```

## Reuse the Wander Labs design language

The `design/` folder is a Hylonome library. It contains the versioned
`wander-labs-editorial` language, its vocabulary, and the generated tokens used by
the page. From a Hylonome checkout, give the CLI the absolute path to this library:

```sh
python -m kinbase_design --library "$LIBRARY" validate wander-labs-editorial
python -m kinbase_design --library "$LIBRARY" export wander-labs-editorial \
  --adapter generic --out "$OUT"
```

The sources are [Wander Labs at b7ab9e7b](https://github.com/wandercom/labs/tree/b7ab9e7bb4b2063933e1637ff36e2218cb31b82a)
and the color and type assets in its vendored Wander Design System 0.6.30.
The working language was imported and derived in Hylonome, then adjusted to use
the monochrome Labs palette, the editorial width and gutter from its article shell,
and the site's display, heading and prose scale. Font weights are kept at 450/550;
the import's generic number type is expressed as Hylonome's font-weight type.
Labs' relative letter spacing remains in page CSS because Hylonome doesn't accept
`em` dimensions. Decorative colors and template assumptions unused by Labs are
not used on this page. Hylonome validation and Apply run against the portable
page inventory; the page uses the resulting token CSS, not the workbench sample
layouts. Raw imports and capture attempts are not in this directory.

The standalone preview uses the same Instrument Sans font and Wander Labs mark
from the Labs source. The font license is in `assets/FONT-LICENSE.txt`.

## Serving the public route

The public hostname is owned by `wandercom/labs`, not by this repository.
The Labs integration should provide a native `app/chiron/page.tsx`, reuse the Labs
layout, typography and footer, and include `/chiron` in the sitemap. Keep its
copy and the generated token sheet in sync with this directory. This directory
does not deploy the URL or change the site's homepage.
