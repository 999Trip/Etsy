# Etsy Design Automation

Generates finished, listable products (digital printables and
print-on-demand physical products) end to end:

1. **Design** - procedurally generate artwork (typography quote posters,
   boho line art, seamless patterns, apparel/mug graphics, and printable
   planners/trackers) with Pillow, for free, with no paid AI image model
   in the loop. Optionally supplement that with illustrated/painterly
   designs generated through a connected Canva account (see "Illustrated
   designs via Canva" below) for styles the procedural generators can't
   produce - hand-lettered script, watercolor florals, distressed vintage
   textures.
2. **Digital downloads** - upload the generated files straight to Etsy as
   digital-download listings via the Etsy Open API v3.
3. **Print-on-demand** - upload the generated artwork to Printify, create
   a product (poster, t-shirt, sweatshirt, mug, etc.), and publish it -
   which, if your Printify shop has a connected Etsy store, automatically
   creates the matching Etsy listing too.

`config/niches.yaml` ships starter niches picked from actual 2026 Etsy/POD
trend research, not guesswork - see the comments in that file for what
each one targets:

- **Fall/Halloween wall art & apparel** - `halloween_line_art_wall_decor`,
  `halloween_quote_posters`, `fall_line_art_wall_decor`,
  `halloween_apparel_graphics`, `fall_apparel_graphics`. Apparel designs
  use a worn/distressed texture by default (`Canvas.add_distress`) to
  match 2026's dominant vintage-Halloween aesthetic, plus a
  `pastel_cuteoween` palette for the trending soft-pastel look.
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
- **Canva-generated illustrated designs** - `halloween_vintage_posters_canva`,
  `fall_party_invitations_canva`. These target styles (illustrated retro
  artwork, hand-lettered invitations) the procedural generators can't
  produce - see "Illustrated designs via Canva" below for how generation
  works differently for this niche type.

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

# Trending fall / Halloween niches
python -m pipeline.generate --niche halloween_line_art_wall_decor --count 8
python -m pipeline.generate --niche halloween_quote_posters --count 6
python -m pipeline.generate --niche fall_line_art_wall_decor --count 6
python -m pipeline.generate --niche halloween_apparel_graphics --count 10
python -m pipeline.generate --niche fall_apparel_graphics --count 10

# Planners / trackers (fastest-growing digital category)
python -m pipeline.generate --niche weekly_planner_printable --count 5
python -m pipeline.generate --niche fall_budget_tracker_printable --count 5
python -m pipeline.generate --niche habit_tracker_printable --count 5
python -m pipeline.generate --niche checklist_printable --count 5
```

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

1. Register an app at <https://www.etsy.com/developers/register> and add
   `http://localhost:3003/oauth/redirect` as a redirect URI.
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

The apparel/mug niches (`halloween_apparel_graphics`,
`fall_apparel_graphics`) render each design at more than one size -
`apparel_12x16` (portrait, for tees/sweatshirts/hoodies) and `mug_9x4`
(landscape wrap, for mugs) - specifically so the same batch can become
several Printify products. Run `publish_pod` once per product type,
pointing `--print-size` at the matching file and `--blueprint-id` at that
product's catalog entry:

```bash
# T-shirts
python -m pipeline.publish_pod --batch output/halloween_apparel_graphics \
    --blueprint-id 6 --print-provider-id 1 --variant-ids 12100,12101 \
    --print-size apparel_12x16 --publish

# Same batch, also as mugs - different blueprint, price, and print file
python -m pipeline.publish_pod --batch output/halloween_apparel_graphics \
    --blueprint-id 68 --print-provider-id 27 --variant-ids 33843 \
    --print-size mug_9x4 --price 14.99 --publish
```

Each blueprint is tracked separately in `metadata.json`
(`printify_products.<blueprint_id>`), so re-running with a *different*
`--blueprint-id` adds a new product instead of being skipped as
already-published, while re-running with the *same* one is idempotent.

**Dark garments:** the apparel/mug niches only use dark-ink palettes, so
the artwork is safely visible on white/light/heather product variants out
of the box. For a black or navy garment variant you'll want an
inverted/white version of the art - swap `palette["ink"]` for a light
color when generating that batch, or recolor in Printify's product editor
after uploading.

**Previewing before Printify is set up:** `pipeline.mockup_preview`
composites a design onto flat t-shirt/hoodie/sweatshirt/mug shapes
(`design/mockup.py`) - not photorealistic, but the real print pixels at
real scale/placement, so you can sanity-check a design before creating
any Printify products:

```bash
python -m pipeline.mockup_preview \
    --design output/halloween_apparel_graphics/<slug> \
    --garment black
```

## 5. Illustrated designs via Canva (optional)

Niches with `type: canva` in `config/niches.yaml` (currently
`halloween_vintage_posters_canva`, `fall_party_invitations_canva`) work
differently from every other niche: generation is **interactive, not
scriptable**. The Canva MCP tools (`generate-design`,
`create-design-from-candidate`, `export-design`) are only callable by
Claude in a live conversation - there's no standalone `python -m
pipeline.generate --niche halloween_vintage_posters_canva` for these.

To generate one: ask Claude (with a Canva account connected) to generate
a design using one of the `prompts` recipes listed under that niche in
`config/niches.yaml`. Claude will call the Canva tools, then run
`pipeline.canva_import` with the resulting export URLs to package the
result into the exact same `output/<niche>/<slug>/metadata.json` shape
every other niche produces - so `pipeline.publish_digital` works on it
unchanged:

```bash
python -m pipeline.canva_import --niche halloween_vintage_posters_canva \
    --variant "Happy Haunting Pumpkin" \
    --pdf letter_8.5x11=<signed pdf url> a4=<signed pdf url> \
    --preview <signed png url> \
    --canva-design-id DAHUuBX0MfE --canva-edit-url https://www.canva.com/d/...
```

Use `--pdf size=url` for designs whose native ratio is close to a
standard page (e.g. Canva's "poster" type, which is ~A-series ratio) -
Canva's PDF export can size directly to `a4`/`letter`/`a3`/`legal`. Use
`--png size=url` instead for designs with a different native ratio (e.g.
"invitation"/"card" types) to avoid distorting them into a page size that
doesn't fit - `publish_digital` uploads whichever of PDF/PNG is present as
the buyer's digital file.

**Export resolution is capped on Canva's free plan** - in testing, PNG
exports above roughly 1000-1500px wide failed with a generic "not allowed
to access design" error, while the same export at 1000px succeeded and
paper-sized PDF export was unaffected. Once Canva Pro is active,
re-export any free-plan PNG-based design (like the invitation niche) at
a higher resolution before selling it - 1000px is noticeably soft for a
print product.

## Notes and caveats

- **Procedural generation is free; Canva generation is not.** The
  quote-poster/line-art/pattern/apparel/planner niches are drawn with
  Pillow - no paid AI model, no per-design cost. The `canva` niches call
  Canva's AI design generation through a connected account and need
  Canva Pro for full-resolution exports, so there's a real cost/plan
  dependency there that the rest of the pipeline doesn't have.
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
