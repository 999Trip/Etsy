from . import line_art, pattern, quote_poster

GENERATORS = {
    "quote_poster": quote_poster.generate,
    "line_art": line_art.generate,
    "pattern": pattern.generate,
}
