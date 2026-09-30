"""Run with `python -B -m unittest discover -s tests -v` after installing requirements-test.txt and Chromium (`python -m playwright install chromium`).

The game script is stubbed so tests never read or write saved game state.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import shutil
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
VIEWPORT = {"width": 390, "height": 844}


class AutoSellAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

        cls.playwright = sync_playwright().start()
        executable = shutil.which("chromium")
        launch_options = {"headless": True}
        if executable:
            launch_options["executable_path"] = executable
        cls.browser = cls.playwright.chromium.launch(**launch_options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=1,
            is_mobile=True,
            has_touch=True,
        )
        self.page = self.context.new_page()
        self.page.route(
            "**/js/game.js",
            lambda route: route.fulfill(
                status=200, content_type="application/javascript", body=""
            ),
        )
        self.page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")

    def tearDown(self):
        self.context.close()

    def test_checkbox_has_auto_sell_accessible_name_from_its_label(self):
        self.assertEqual(
            self.page.get_by_role("checkbox", name="Auto-sell").count(), 1
        )
        association = self.page.locator("#autoSell").evaluate(
            "el => ({labelCount: el.labels.length, labelText: el.labels[0]?.innerText.trim()})"
        )
        self.assertEqual(association, {"labelCount": 1, "labelText": "Auto-sell"})

    def test_mobile_tab_order_reaches_checkbox_with_visible_focus_without_toggling(self):
        viewport = self.page.evaluate(
            "() => ({width: innerWidth, height: innerHeight, mobile: matchMedia('(max-width: 760px)').matches})"
        )
        self.assertEqual(viewport, {"width": 390, "height": 844, "mobile": True})

        trace = []
        focus = None
        for _ in range(5):
            self.page.keyboard.press("Tab")
            active_id = self.page.evaluate("() => document.activeElement.id")
            trace.append(active_id)
            if active_id == "autoSell":
                focus = self.page.locator("#autoSell").evaluate(
                    "el => ({checked: el.checked, focused: el.matches(':focus'), outlineWidth: getComputedStyle(el.nextElementSibling).outlineWidth, outlineStyle: getComputedStyle(el.nextElementSibling).outlineStyle})"
                )
        self.assertEqual(trace, ["cow", "sellBtn", "autoSell", "saveBtn", "resetBtn"])
        self.assertIsNotNone(focus, "Tab navigation must reach Auto-sell")
        self.assertFalse(focus["checked"], "Tab navigation must not toggle Auto-sell")
        self.assertTrue(focus["focused"])
        self.assertEqual(focus["outlineWidth"], "3px")
        self.assertEqual(focus["outlineStyle"], "solid")


if __name__ == "__main__":
    unittest.main()
