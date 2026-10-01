"""Verify the barn-capacity indicator in isolated synthetic game sessions.

Run with `python -B -m unittest discover -s tests -v` after installing
requirements-test.txt and Chromium (`python -m playwright install chromium`).
"""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import shutil
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class BarnCapacityMeterTests(unittest.TestCase):
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

    def test_meter_tracks_milk_and_capacity_without_changing_progression(self):
        now_ms = 1_700_000_000_000
        synthetic_save = {
            "coins": 1000,
            "milk": 25,
            "totalMilk": 25,
            "autoSell": False,
            "owned": {"cow": 0, "machine": 0, "feed": 0, "barn": 0},
            "lastSaved": now_ms,
        }
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        try:
            page = context.new_page()
            page.add_init_script(
                """(() => {
                  Date.now = () => __NOW__;
                  window.requestAnimationFrame = () => 0;
                  localStorage.clear();
                  localStorage.setItem("cowCashSave.v1", JSON.stringify(__SAVE__));
                })();"""
                .replace("__NOW__", str(now_ms))
                .replace("__SAVE__", json.dumps(synthetic_save))
            )
            page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")

            meter = page.get_by_role("progressbar", name="Barn storage used")
            self.assertEqual(meter.count(), 1)
            self.assertEqual(
                meter.evaluate(
                    "el => ({value: el.value, max: el.max, valueText: el.getAttribute('aria-valuetext')})"
                ),
                {"value": 25, "max": 100, "valueText": "25 of 100 milk"},
            )

            page.locator("#cow").click()
            self.assertEqual(
                meter.evaluate(
                    "el => ({value: el.value, max: el.max, valueText: el.getAttribute('aria-valuetext')})"
                ),
                {"value": 26, "max": 100, "valueText": "26 of 100 milk"},
            )

            page.locator('[data-id="barn"]').click()
            self.assertEqual(page.locator("#milk").inner_text(), "26 / 200")
            self.assertEqual(page.locator("#coins").inner_text(), "750")
            self.assertEqual(page.locator("#price").inner_text(), "1.1")
            self.assertEqual(
                meter.evaluate(
                    "el => ({value: el.value, max: el.max, valueText: el.getAttribute('aria-valuetext')})"
                ),
                {"value": 26, "max": 200, "valueText": "26 of 200 milk"},
            )
        finally:
            context.close()

    def test_meter_warns_when_nearly_full_and_clears_after_capacity_upgrade(self):
        now_ms = 1_700_000_000_000
        synthetic_save = {
            "coins": 1000,
            "milk": 79,
            "totalMilk": 79,
            "autoSell": False,
            "owned": {"cow": 0, "machine": 0, "feed": 0, "barn": 0},
            "lastSaved": now_ms,
        }
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        try:
            page = context.new_page()
            page.add_init_script(
                """(() => {
                  Date.now = () => __NOW__;
                  window.requestAnimationFrame = () => 0;
                  localStorage.clear();
                  localStorage.setItem("cowCashSave.v1", JSON.stringify(__SAVE__));
                })();"""
                .replace("__NOW__", str(now_ms))
                .replace("__SAVE__", json.dumps(synthetic_save))
            )
            page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")
            meter = page.get_by_role("progressbar", name="Barn storage used")

            page.locator("#cow").click()
            self.assertEqual(meter.get_attribute("aria-valuetext"), "80 of 100 milk, barn nearly full")
            self.assertTrue(meter.evaluate("el => el.classList.contains('is-near-full')"))

            for _ in range(20):
                page.locator("#cow").click()
            self.assertEqual(meter.get_attribute("aria-valuetext"), "100 of 100 milk, barn full")
            self.assertTrue(meter.evaluate("el => el.classList.contains('is-full')"))

            page.locator('[data-id="barn"]').click()
            self.assertEqual(meter.get_attribute("aria-valuetext"), "100 of 200 milk")
            self.assertFalse(meter.evaluate("el => el.classList.contains('is-near-full') || el.classList.contains('is-full')"))
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
