# Etsy Design Automation

Generates finished, listable products (digital printables and
print-on-demand physical products) end to end:

1. **Design** - procedurally generate artwork (typography quote posters,
   boho line art, seamless patterns, apparel/mug graphics, and printable
   planners/trackers) with Pillow. No paid AI image generation is used -
   everything is drawn from code, for free.
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

## Notes and caveats

- **No AI image generation.** Every design is drawn procedurally with
  Pillow (typography layout, geometric line art, tileable patterns, icon
  silhouettes for apparel/mug graphics). That keeps this pipeline free to
  run and avoids any AI-generated-content
  disclosure/IP questions, but it also means the visual variety is bounded
  by the generators in `design/generators/` - extend them (or add a new
  generator + niche) to expand into new styles.
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
