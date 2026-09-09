"""Smoke tests for the design generators and batch pipeline.

No network access or API credentials required - these only exercise the
local, procedural design generation.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from design.generators import line_art, pattern, quote_poster
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


class NicheConfigTests(unittest.TestCase):
    def test_niches_yaml_loads_and_matches_known_generator_types(self):
        niches = load_niches()
        self.assertTrue(niches)
        for name, niche in niches.items():
            self.assertIn(niche["type"], ("quote_poster", "line_art", "pattern"), name)
            for tag in niche["seo"]["tags"]:
                self.assertLessEqual(len(tag), 20, f"{name}: tag '{tag}' exceeds Etsy's 20-char limit")
            self.assertLessEqual(len(niche["seo"]["tags"]), 13, f"{name}: more than 13 tags")


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


if __name__ == "__main__":
    unittest.main()
