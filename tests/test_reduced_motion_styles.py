"""Check the reduced-motion stylesheet contract without starting a browser."""
import re
import unittest
from pathlib import Path


CSS_PATH = Path(__file__).resolve().parents[1] / "css" / "style.css"


class ReducedMotionStylesTests(unittest.TestCase):
    def test_reduced_motion_disables_all_decorative_motion(self):
        css = CSS_PATH.read_text(encoding="utf-8")
        media_rule = re.search(
            r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(?P<body>[\s\S]*)\}\s*$",
            css,
        )
        self.assertIsNotNone(media_rule, "Reduced-motion media query must be present")
        body = media_rule.group("body")
        normalized = re.sub(r"\s+", "", body)

        self.assertIn("*,*::before,*::after{", normalized)
        self.assertRegex(normalized, r"animation:none!important;")
        self.assertRegex(normalized, r"transition:none!important;")


if __name__ == "__main__":
    unittest.main()
