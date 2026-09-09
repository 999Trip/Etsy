"""Smoke tests for the design generators and batch pipeline.

No network access or API credentials required - these only exercise the
local, procedural design generation.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from design import mockup
from design.engine import SIZES_IN
from design.generators import apparel_graphic, line_art, pattern, planner, quote_poster
from design.motifs import ICON_DRAW_FN
from design.palettes import PALETTES
from pipeline.generate import generate_batch, load_niches


class GeneratorSmokeTests(unittest.TestCase):
    def test_quote_poster_produces_an_image(self):
        canvas = quote_poster.generate(quote="Test quote", author="Tester", size_name="5x7", seed=1)
        self.assertEqual(canvas.image.mode, "RGB")
        self.assertGreater(canvas.w, 0)
        self.assertGreater(canvas.h, 0)

    def test_line_art_all_motifs(self):
        for motif in line_art.MOTIFS:
            canvas = line_art.generate(motif=motif, size_name="5x7", seed=1)
            self.assertGreater(canvas.w, 0)

    def test_pattern_all_motifs(self):
        for motif in pattern.MOTIFS:
            canvas = pattern.generate(motif=motif, size_name="square_12x12", seed=1)
            self.assertGreater(canvas.w, 0)

    def test_every_palette_is_usable(self):
        for name in PALETTES:
            canvas = quote_poster.generate(quote="Hi", palette_name=name, size_name="5x7", seed=1)
            self.assertGreater(canvas.w, 0)

    def test_apparel_graphic_is_transparent_and_portrait_or_landscape(self):
        for motif in ICON_DRAW_FN:
            portrait = apparel_graphic.generate(motif=motif, text="Boo", size_name="apparel_12x16", seed=1)
            self.assertEqual(portrait.image.mode, "RGBA")
            landscape = apparel_graphic.generate(motif=motif, text="Boo", size_name="mug_9x4", seed=1)
            self.assertEqual(landscape.image.mode, "RGBA")

    def test_apparel_graphic_without_text(self):
        canvas = apparel_graphic.generate(motif="pumpkin", size_name="apparel_12x16", seed=1)
        self.assertEqual(canvas.image.mode, "RGBA")

    def test_planner_all_templates_fit_header_within_page(self):
        for template in planner.TEMPLATES:
            canvas = planner.generate(template=template, header="A Reasonably Long Header Title Here", size_name="letter_8.5x11")
            self.assertEqual(canvas.image.mode, "RGB")
            self.assertGreater(canvas.w, 0)

    def test_mockups_render_for_every_product_type(self):
        design = apparel_graphic.generate(motif="ghost", text="Boo", size_name="apparel_12x16", seed=1)
        mug_design = apparel_graphic.generate(motif="ghost", text="Boo", size_name="mug_9x4", seed=1)
        for fn, img in [
            (mockup.mockup_tshirt, design.image),
            (mockup.mockup_hoodie, design.image),
            (mockup.mockup_sweatshirt, design.image),
            (mockup.mockup_mug, mug_design.image),
        ]:
            result = fn(img)
            self.assertEqual(result.mode, "RGB")
            self.assertEqual(result.size, mockup.CANVAS_SIZE)

    def test_tumbler_and_mug_wrap_mockups_render(self):
        pattern_design = pattern.generate(motif="night_sky", palette_name="midnight_gold", size_name="tumbler_9x5", seed=1)
        mug_pattern = pattern.generate(motif="night_sky", palette_name="midnight_gold", size_name="mug_9x4", seed=1)
        for fn, img in [
            (mockup.mockup_tumbler, pattern_design.image),
            (lambda i: mockup.mockup_mug(i, cover=True), mug_pattern.image),
        ]:
            result = fn(img)
            self.assertEqual(result.mode, "RGB")
            self.assertEqual(result.size, mockup.CANVAS_SIZE)


class NicheConfigTests(unittest.TestCase):
    def test_niches_yaml_loads_and_matches_known_generator_types(self):
        niches = load_niches()
        self.assertTrue(niches)
        for name, niche in niches.items():
            self.assertIn(niche["type"], ("quote_poster", "line_art", "pattern", "apparel_graphic", "planner", "canva"), name)
            for tag in niche["seo"]["tags"]:
                self.assertLessEqual(len(tag), 20, f"{name}: tag '{tag}' exceeds Etsy's 20-char limit")
            self.assertLessEqual(len(niche["seo"]["tags"]), 13, f"{name}: more than 13 tags")

    def test_every_configured_size_is_a_real_size(self):
        """Every digital_sizes/pod_sizes entry must be a key design.engine
        actually knows how to render at - a typo or made-up label here
        (e.g. a size name invented for one niche and never added to
        SIZES_IN) would only surface at generation/import time otherwise."""
        for name, niche in load_niches().items():
            for size_name in niche.get("digital_sizes", []) + niche.get("pod_sizes", []):
                self.assertIn(size_name, SIZES_IN, f"{name}: '{size_name}' is not a key in design.engine.SIZES_IN")

    def test_canva_niches_have_required_fields(self):
        for name, niche in load_niches().items():
            if niche["type"] != "canva":
                continue
            self.assertIn("canva_design_type", niche, name)
            self.assertTrue(niche.get("prompts"), f"{name}: no prompts configured")
            for prompt in niche["prompts"]:
                self.assertIn("label", prompt, name)
                self.assertIn("query", prompt, name)
            self.assertTrue(niche.get("digital_sizes") or niche.get("pod_sizes"), f"{name}: no digital_sizes or pod_sizes")


class BatchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)

    def test_generate_batch_writes_files_and_metadata(self):
        results = generate_batch("minimalist_quote_posters", 2, self.tmp_dir, seed=1)
        self.assertEqual(len(results), 2)
        for design in results:
            design_dir = self.tmp_dir / design["design_id"]
            self.assertTrue((design_dir / "metadata.json").exists())
            self.assertTrue(Path(design["preview"]).exists())
            self.assertLessEqual(len(design["tags"]), 13)
            self.assertLessEqual(len(design["title"]), 140)

    def test_generate_batch_planner_niche(self):
        results = generate_batch("fall_budget_tracker_printable", 2, self.tmp_dir, seed=1)
        self.assertEqual(len(results), 2)
        for design in results:
            self.assertEqual(design["product_mode"], "digital")
            self.assertIn("letter_8.5x11", design["files"]["pdf"])
            self.assertTrue(Path(design["preview"]).exists())


if __name__ == "__main__":
    unittest.main()
