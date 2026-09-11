# Etsy Design Automation

Generates finished, listable products (digital printables and
print-on-demand physical products) end to end:

1. **Design** - two sources feed into the same pipeline:
   - **Procedural** (`design/generators/`) - typography quote posters,
     boho line art, seamless/scattered patterns, and printable
     planners/trackers, drawn with Pillow, for free, no paid AI model in
     the loop. This now includes all-over illustrated patterns for
     tumbler/mug wraps (`design/generators/pattern.py`'s scatter motifs,
     built from the same icon library as the wall-art line) - an
     original, non-infringing take on the trending all-over-print
     tumbler style (not a copy of any specific commercial product).
   - **Canva-generated illustrated designs** - hand-lettered script,
     illustrated characters, distressed vintage textures - styles the
     procedural generators can't produce. **This is the source for
     box-print apparel/mug designs** (a whole illustrated rectangle
     printed on the garment - see "Illustrated designs via Canva" below)
     - an earlier flat-icon-silhouette Pillow approach for this was tried
     and dropped for looking cheap on an actual t-shirt mockup; Canva's
     box-print graphics looked dramatically better in testing.
2. **Digital downloads** - upload the generated files straight to Etsy as
   digital-download listings via the Etsy Open API v3.
3. **Print-on-demand** - upload the generated artwork to Printify, create
   a product (poster, t-shirt, sweatshirt, mug, etc.), and publish it -
   which, if your Printify shop has a connected Etsy store, automatically
   creates the matching Etsy listing too.

`config/niches.yaml` ships starter niches picked from actual 2026 Etsy/POD
trend research, not guesswork - see the comments in that file for what
each one targets:

- **Fall/Halloween wall art (procedural)** - `halloween_line_art_wall_decor`,
  `halloween_quote_posters`, `fall_line_art_wall_decor`.
- **Fall/Halloween tumbler & mug patterns (procedural)** -
  `halloween_pattern_tumblers`: all-over scattered-icon wraps (night sky
  w/ bats, cream w/ cats & pumpkins & ghosts, purple w/ cats & pumpkins &
  moons, jack-o'-lantern faces) for 40oz tumblers and mugs.
- **Fall/Halloween illustrated designs (Canva)** -
  `halloween_vintage_posters_canva` / `halloween_vintage_apparel_canva`
  and `fall_vintage_posters_canva` / `fall_vintage_apparel_canva` (same
  illustrated artwork, sold as a paper print vs. printed on apparel/mugs
  - see "Illustrated designs via Canva"), plus
  `fall_party_invitations_canva` for editable-style invitations.
- **Planners & trackers** - `weekly_planner_printable`,
  `fall_budget_tracker_printable`, `habit_tracker_printable`,
  `checklist_printable`. Research showed planners/templates are Etsy's
  *fastest-growing* digital category in 2026, ahead of decorative wall
  art - these are functional documents (tables, grids, checkboxes) via
  `design/generators/planner.py`, deliberately low-ink (plain white page,
  colored lines/text only) since that's a trend in its own right.
- **Original boho/minimalist starter set** -
  `boho_line_art_wall_decor`, `minimalist_quote_posters`,
  `boho_digital_paper_pack`.

`design/generators/apparel_graphic.py` (flat icon silhouette + text on a
transparent background) still exists and is still tested, but no niche
uses it for apparel any more - see above. It's a reasonable base for
cheap, high-volume filler designs later; just not the current answer for
apparel quality.

```
design/        procedural art generators (quote posters, line art, patterns)
config/        niche definitions: palettes, motifs/quotes, SEO copy templates
integrations/  Etsy + Printify API clients
pipeline/      CLI scripts that tie it together: generate -> publish
output/        generated batches land here (gitignored)
```

## 1. Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fonts: the generators use whatever fontconfig resolves for you (DejaVu
Serif/Sans etc. on most Linux boxes, the system fonts on macOS). For a
nicer look, drop free, commercial-use fonts (e.g. from Google Fonts -
Playfair Display, Cormorant, Montserrat) into `design/fonts/custom/` as
`serif.ttf`, `serif_bold.ttf`, `sans.ttf`, `sans_bold.ttf`, `script.ttf` -
see `design/fonts.py` for the full list of roles it looks for.

## 2. Generate a batch of designs

No API keys needed for this step - it's pure local image generation.

```bash
python -m pipeline.generate --niche minimalist_quote_posters --count 6 --seed 1
python -m pipeline.generate --niche boho_line_art_wall_decor --count 8
python -m pipeline.generate --niche boho_digital_paper_pack --count 10

# Trending fall / Halloween wall art (procedural)
python -m pipeline.generate --niche halloween_line_art_wall_decor --count 8
python -m pipeline.generate --niche halloween_quote_posters --count 6
python -m pipeline.generate --niche fall_line_art_wall_decor --count 6

# Planners / trackers (fastest-growing digital category)
python -m pipeline.generate --niche weekly_planner_printable --count 5
python -m pipeline.generate --niche fall_budget_tracker_printable --count 5
python -m pipeline.generate --niche habit_tracker_printable --count 5
python -m pipeline.generate --niche checklist_printable --count 5
```

All apparel/mug niches and every `type: canva` niche (see `config/niches.yaml`)
aren't generated this way - see "Illustrated designs via Canva" below.

Each run writes `output/<niche>/<design-slug>/` containing:

- `<size>.png` / `<size>.pdf` - print-ready files at 300 DPI for every
  configured size
- `preview.jpg` - a web-sized preview image
- `metadata.json` - the SEO title/description/tags and pricing that the
  publish scripts will use

Open a few PNGs to sanity-check them before publishing anything.

Niches (palettes, motifs/quotes, sizes, pricing, SEO templates) live in
`config/niches.yaml`. Duplicate a block to create a new niche - nothing
in the pipeline scripts is hardcoded to a specific niche.

## 3. Publish digital downloads to Etsy

Etsy requires OAuth (not just an API key) for anything that writes data.

1. Register an app at <https://www.etsy.com/developers/register>, then
   add this exact redirect URI to it at
   <https://www.etsy.com/developers/your-apps> (not the app's "Settings"
   link in the API console sidebar - that's a shop-level Developer Mode
   toggle, unrelated):
   ```
   https://localhost:3003/oauth/redirect
   ```
   Etsy's docs are explicit that this must be `https`, character for
   character, with no exception for localhost - plain `http` fails.
   Since there's no real cert for "localhost", `integrations/etsy_oauth.py`
   generates a throwaway self-signed one automatically (via `openssl`,
   cached as `.etsy_oauth_cert.pem`/`.etsy_oauth_key.pem`, gitignored) -
   your browser will show a privacy warning when it lands back on
   localhost after you approve access; that's expected, click through it.
2. Put the app's Keystring in `.env` as `ETSY_KEYSTRING`, and your shop id
   (from Shop Manager > Settings, or your shop's URL) as `ETSY_SHOP_ID`.
3. Authorize once, in a real browser:
   ```bash
   python -m integrations.etsy_oauth
   ```
   This opens a login/approve page, then saves `.etsy_token.json`
   (gitignored). The client refreshes the access token automatically
   after that using the stored refresh token.
4. Find a taxonomy (category) id for your niche - digital wall art
   typically lives under "Art & Collectibles > Prints" or "Craft
   Supplies & Tools > Digital":
   ```bash
   python -c "from integrations.etsy_client import EtsyClient; \
       [print(n['id'], n['name']) for n in EtsyClient().get_seller_taxonomy_nodes()]"
   ```
5. Publish a batch **as drafts** (default - review before anything goes
   live):
   ```bash
   python -m pipeline.publish_digital --batch output/minimalist_quote_posters \
       --taxonomy-id <id from step 4>
   ```
   Add `--activate` once you're happy with the drafts to make listings
   live immediately instead.

Re-running `publish_digital` on the same batch skips any design that
already has an `etsy_listing_id` in its `metadata.json`, so it's safe to
re-run after fixing a mistake partway through a batch.

## 4. Publish print-on-demand products via Printify

1. Get a personal access token at
   <https://printify.com/app/account/api> and put it in `.env` as
   `PRINTIFY_API_TOKEN`.
2. In the Printify dashboard, connect your Etsy shop under **My stores**
   - this is what makes `--publish` below push straight to Etsy.
3. Pick a blueprint (product type), print provider, and variants - either
   browse <https://printify.com/app/products> and read the ids out of the
   product URL, or query the API:
   ```bash
   python -c "from integrations.printify_client import PrintifyClient as P; \
       import json; print(json.dumps(P().list_blueprints()[:10], indent=2))"
   ```
4. Publish a batch:
   ```bash
   python -m pipeline.publish_pod --batch output/boho_line_art_wall_decor \
       --blueprint-id 494 --print-provider-id 1 --variant-ids 33742,33743
   ```
   Add `--publish` to push the product live (and to the connected Etsy
   shop); omit it to leave products as Printify drafts you can review
   first.

### Publishing the same design to multiple product types (tee + sweatshirt + mug)

The Canva apparel niches (see below) produce a `pod_sizes` file per
product shape - `apparel_12x16` (portrait, for tees/sweatshirts/hoodies)
and `mug_9x4` (for mugs) - specifically so the same design can become
several Printify products. Run `publish_pod` once per product type,
pointing `--print-size` at the matching file and `--blueprint-id` at that
product's catalog entry:

```bash
# T-shirts
python -m pipeline.publish_pod --batch output/halloween_vintage_apparel_canva \
    --blueprint-id 6 --print-provider-id 1 --variant-ids 12100,12101 \
    --print-size apparel_12x16 --publish

# Same batch, also as mugs - different blueprint, price, and print file
python -m pipeline.publish_pod --batch output/halloween_vintage_apparel_canva \
    --blueprint-id 68 --print-provider-id 27 --variant-ids 33843 \
    --print-size mug_9x4 --price 14.99 --publish
```

Each blueprint is tracked separately in `metadata.json`
(`printify_products.<blueprint_id>`), so re-running with a *different*
`--blueprint-id` adds a new product instead of being skipped as
already-published, while re-running with the *same* one is idempotent.

**Previewing before Printify is set up:** `pipeline.mockup_preview`
composites a design onto flat t-shirt/hoodie/sweatshirt/mug shapes
(`design/mockup.py`) - not photorealistic, but the real print pixels at
real scale/placement, so you can sanity-check a design before creating
any Printify products:

```bash
python -m pipeline.mockup_preview \
    --design output/halloween_vintage_apparel_canva/<slug> \
    --garment navy
```

## 5. Illustrated designs via Canva

Niches with `type: canva` in `config/niches.yaml` work differently from
every other niche: generation is **interactive, not scriptable**. The
Canva MCP tools (`generate-design`, `create-design-from-candidate`,
`export-design`) are only callable by Claude in a live conversation -
there's no standalone `python -m pipeline.generate --niche ...` for
these. This is the path for **every apparel/mug niche**
(`halloween_vintage_apparel_canva`, `fall_vintage_apparel_canva`), plus
illustrated wall art (`halloween_vintage_posters_canva`,
`fall_vintage_posters_canva`) and invitations
(`fall_party_invitations_canva`).

To generate one: ask Claude (with a Canva account connected) to generate
a design using one of the `prompts` recipes listed under that niche in
`config/niches.yaml`. Claude:

1. Calls `generate-design` with that prompt and the niche's
   `canva_design_type`, then `create-design-from-candidate` on whichever
   candidate looks best.
2. Calls `export-design` with `{"type": "pdf"}` - **no `size` param**.
   Canva's raw PNG export is capped at a modest width on the free plan
   (~1000-1500px failed with a generic "not allowed" error in testing),
   but PDF export renders at the design's own native canvas size, which
   for a "poster" design type is a full physical poster (huge -
   ~4960x7016px once rasterized at 300 DPI - regardless of plan).
3. Runs `pipeline.canva_import` with that one PDF URL. It rasterizes the
   PDF locally (via PyMuPDF) into one master image, then derives every
   size the niche needs from that single master - letter/a4 PDFs for
   wall art (cropped to fill the page exactly), and PNGs for apparel/mug
   POD sizes (scaled to fit within the print area *without* cropping,
   since a tall poster cropped to a wide mug wrap would lose most of the
   design - see the module docstring for why "cover" vs "contain"
   matters here). Output lands in the same
   `output/<niche>/<slug>/metadata.json` shape every other niche
   produces, so `pipeline.publish_digital` / `pipeline.publish_pod` work
   on it unchanged:

```bash
python -m pipeline.canva_import --niche halloween_vintage_apparel_canva \
    --variant "Happy Haunting Pumpkin" \
    --master-pdf <signed pdf export url, requested with no size param> \
    --canva-design-id DAHUuBX0MfE --canva-edit-url https://www.canva.com/d/...
```

**One generation, two listings:** the poster and apparel niches for the
same season share the same `prompts` - generate the design once, then
import it twice (once into the wall-art niche, once into the apparel
niche) to get both a paper print listing and a t-shirt/mug listing from
one Canva generation call.

**A design's native canvas size varies a lot by `canva_design_type`** -
"poster" defaults to a large physical poster, "invitation" defaults to a
modest card size. The invitation niche's small file size isn't
under-resolution; 300 DPI at invitation size is legitimately a few
thousand pixels smaller than 300 DPI at poster size because the card is
physically smaller. Check that a niche's configured sizes are a
reasonable fit for its `canva_design_type` (`test_every_configured_size_is_a_real_size`
in `tests/test_generators.py` only checks the size *exists*, not that
it's a sensible fit).

**Close-up sharpness:** cropping into the poster-sized master at extreme
zoom shows some softness - the underlying illustration likely has less
native detail than the huge poster canvas suggests. It reads cleanly at
normal viewing distance (see the mockups this pipeline produces) but is
worth re-generating at Canva Pro if you need it to hold up under a tight
product-photo crop.

**QC every candidate before publishing anything, not just at a glance.**
A design that reads fine as a small thumbnail can still have real
defects a full-page or whole-composition view won't show:

- **Zoom into any character/face illustration** (a full-res crop, not
  just the downsized preview) - AI generation artifacts like mismatched
  or asymmetric eyes are easy to miss at normal preview size but
  obvious once you look closely (this shipped once before it was
  caught - see git history around the calendar background swap).
- **Confirm it's actually the content type you asked for**, not a
  plausible-looking substitute - Canva's AI has repeatedly returned a
  fake event invitation, a press release, or an infographic when asked
  for a plain graphic or a literal data grid. Check the *content*, not
  just that something rendered.
- **For a design going onto a POD print area (mug/tumbler wrap) or into
  a compositing safe-zone**, render the actual mockup (`pipeline.mockup_preview`,
  or a real Printify product's own generated photos) before publishing
  - a crop or composite that looks right in the flat source image can
  still cut through a focal point once mapped onto the real print
  shape.

None of this is optional polish - it's the difference between a listing
you'd actually want a customer to see and one that ships an obvious
flaw because nobody looked closely before hitting publish.

**When a competitor design/format is clearly working, recreate it in
our own style and ship it - don't wait for a go-ahead first.** This is
how the Halloween weekly planner got made: the user found a
well-performing competitor listing's format (illustrated background,
fillable write-in grid), and the instruction going forward is to spot
that pattern proactively and act on it the same way, not just when
asked. In practice that means: build it with this repo's own generators/
palettes/assets (never trace, copy exact layouts pixel-for-pixel, or
reuse anyone else's copy/branding/trademarked characters - recreate the
*concept*, not the artifact), run it through the QC steps above, publish
it, and report what shipped. Reserve asking first for the genuinely
open decisions - pricing a materially new product, personalization/
per-order fulfillment, anything with real recurring cost (a paid tool,
an ad spend) - not for "should I build the thing that's obviously
working."

**Standing exception: hold off on new Printify physical products (apparel,
shirts, etc.) until the user confirms a payment method is on file for
additional listings.** This doesn't block digital-only work (printables,
calendars, planners, wrap-file bundles) or anything on already-approved
product types (tumblers) - it's specifically new Printify product
*categories* while billing is unconfirmed. Check with the user before
publishing a new physical product type; ask if this still holds before
assuming it's been lifted.

**Vary the color palette across products - don't let the whole store
default to the same one or two colors.** It's easy for every Halloween
design in a session to end up purple/orange/cream because that's what
the first design landed on; the user explicitly wants visual variety
across the catalog instead of a monochromatic-looking store. When
building or recreating a design, deliberately pick a palette that reads
differently from what's already live for that niche (e.g. black/orange,
deep teal/orange, burgundy/cream, navy/gold) rather than defaulting back
to the same purple. Keep the palette on-brand for the niche/season, just
don't repeat it listing after listing.

**Same rule applies to creature/motif choice, not just color.** Don't
default to a black cat every time a Halloween design needs a companion
animal/creature - mix in skeletons, spiders, bats, owls, etc. across
different listings so the catalog doesn't read as one repeated cast of
characters.

**Illustrated planners/trackers: Canva illustration + procedural overlay,
not pure Pillow line art.** Established with the cauldron mood tracker
and cute weekly to-do list (see `output/_review/` for the approved
references and the git history around them for the exact recipe): when a
trending printable format calls for genuinely illustrated art (a realistic
cauldron, a cute mug/pumpkin/ghost cluster, etc.) rather than flat
geometric shapes, generate that illustration in Canva - ask for it
composed as a banner/border across roughly the top third to top fifth of
the page with the rest left completely blank parchment (this is what
makes it reliably compositable; without that constraint Canva fills the
whole page and there's nowhere left to put a grid). Then export at high
res and composite the functional content (day-number grids, checkboxes,
mood-key text, titles) on top with PIL/Pillow, positioned in the
guaranteed-blank area - never ask Canva to render the precise text/numbers
itself, it isn't reliable for that (same reasoning as the existing
illustrated-weekly-planner/calendar niches). A plain vector-drawn cauldron
or mug reads as an obvious placeholder, not "an actual one" - this is the
difference between a listing that looks trend-competitive and one that
doesn't, so don't fall back to pure-Pillow icons for this category even
though it's more steps than the fully-procedural planner templates.

## Notes and caveats

- **Procedural generation is free; Canva generation is not.** The
  quote-poster/line-art/pattern/planner niches are drawn with Pillow - no
  paid AI model, no per-design cost. The `canva` niches call Canva's AI
  design generation through a connected account, so there's a real
  cost/plan dependency there that the rest of the pipeline doesn't have.
- **Etsy policy.** Etsy prohibits fully automated, unreviewed listing
  creation at scale and requires accurate "digital file" / production
  disclosures; that's why the publish scripts default to creating
  **drafts**, not live listings. Review Etsy's Seller Policy and digital
  item guidelines before turning on `--activate`/`--publish` for anything
  beyond a small test batch.
- **Everything here is a starting point, not a finished storefront.**
  Sensible defaults are built in (draft-first publishing, Etsy's
  title/tag length limits enforced in code, idempotent re-runs) but you
  are the one accountable for what actually goes live - proofread
  generated titles/descriptions and preview images before activating
  anything.
