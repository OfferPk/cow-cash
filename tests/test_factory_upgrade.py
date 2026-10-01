"""Verify the one-time Dairy Factory upgrade in isolated synthetic game sessions.

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


class DairyFactoryTests(unittest.TestCase):
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

    def _open_save(self, synthetic_save, now_ms=1_700_000_000_000):
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
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
        return context, page

    def test_legacy_save_defaults_factory_to_unowned(self):
        now_ms = 1_700_000_000_000
        legacy_save = {
            "coins": 0,
            "milk": 4,
            "totalMilk": 12,
            "autoSell": False,
            "owned": {"cow": 1, "machine": 0, "feed": 0, "barn": 0},
            "lastSaved": now_ms,
        }
        context, page = self._open_save(legacy_save, now_ms)
        try:
            factory = page.locator('[data-id="factory"]')
            self.assertEqual(factory.locator(".owned").inner_text(), "Owned: 0/1")
            self.assertEqual(factory.locator(".cost").inner_text(), "25K 🪙")
            self.assertTrue(factory.is_disabled())
            self.assertEqual(page.locator("#price").inner_text(), "1")
            self.assertEqual(page.locator("#milk").inner_text(), "4 / 100")
        finally:
            context.close()

    def test_factory_costs_exactly_25000_and_can_only_be_bought_once(self):
        now_ms = 1_700_000_000_000
        synthetic_save = {
            "coins": 50000,
            "milk": 0,
            "totalMilk": 0,
            "autoSell": False,
            "owned": {"cow": 0, "machine": 0, "feed": 0, "barn": 0},
            "lastSaved": now_ms,
        }
        context, page = self._open_save(synthetic_save, now_ms)
        try:
            factory = page.locator('[data-id="factory"]')
            self.assertEqual(factory.locator(".cost").inner_text(), "25K 🪙")
            self.assertEqual(factory.locator(".owned").inner_text(), "Owned: 0/1")

            factory.click()
            self.assertEqual(page.locator("#coins").inner_text(), "25K")
            self.assertEqual(page.locator("#price").inner_text(), "3")
            self.assertEqual(factory.locator(".owned").inner_text(), "Owned: 1/1")
            self.assertTrue(factory.is_disabled())

            page.evaluate("""() => {
              const button = document.querySelector('[data-id="factory"]');
              button.disabled = false;
              button.click();
            }""")
            self.assertEqual(page.locator("#coins").inner_text(), "25K")
            page.locator("#saveBtn").click()
            saved = page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertEqual(saved["coins"], 25000)
            self.assertEqual(saved["owned"]["factory"], 1)
        finally:
            context.close()

    def test_factory_multiplies_existing_barn_bonus_for_manual_sale(self):
        now_ms = 1_700_000_000_000
        synthetic_save = {
            "coins": 0,
            "milk": 5,
            "totalMilk": 5,
            "autoSell": False,
            "owned": {"cow": 0, "machine": 0, "feed": 0, "barn": 2, "factory": 1},
            "lastSaved": now_ms,
        }
        context, page = self._open_save(synthetic_save, now_ms)
        try:
            self.assertEqual(page.locator("#price").inner_text(), "3.6")
            self.assertEqual(page.locator("#sellValue").inner_text(), "18")
            page.locator("#sellBtn").click()
            self.assertEqual(page.locator("#coins").inner_text(), "18")
            self.assertEqual(page.locator("#milk").inner_text(), "0 / 400")
        finally:
            context.close()

    def test_active_auto_sell_uses_the_same_factory_and_barn_price(self):
        now_ms = 1_700_000_000_000
        synthetic_save = {
            "coins": 0,
            "milk": 0,
            "totalMilk": 0,
            "autoSell": True,
            "owned": {"cow": 0, "machine": 0, "feed": 0, "barn": 2, "factory": 1},
            "lastSaved": now_ms,
        }
        context, page = self._open_save(synthetic_save, now_ms)
        try:
            self.assertEqual(page.locator("#price").inner_text(), "3.6")
            page.locator("#cow").click()
            self.assertEqual(page.locator("#coins").inner_text(), "3.6")
            self.assertEqual(page.locator("#milk").inner_text(), "0 / 400")
            self.assertEqual(page.locator("#totalMilk").inner_text(), "1")
        finally:
            context.close()

    def test_offline_payout_uses_shared_price_and_is_independent_of_auto_sell(self):
        now_ms = 1_700_000_000_000
        for auto_sell in (False, True):
            with self.subTest(auto_sell=auto_sell):
                synthetic_save = {
                    "coins": 7,
                    "milk": 12,
                    "totalMilk": 34,
                    "autoSell": auto_sell,
                    "owned": {"cow": 2, "machine": 0, "feed": 0, "barn": 2, "factory": 1},
                    "lastSaved": now_ms - 60_000,
                }
                context, page = self._open_save(synthetic_save, now_ms)
                try:
                    self.assertEqual(page.locator("#coins").inner_text(), "439")
                    self.assertEqual(page.locator("#milk").inner_text(), "12 / 400")
                    self.assertEqual(page.locator("#autoSell").is_checked(), auto_sell)
                    self.assertIn("sold for 432 coins", page.locator("#modalBody").inner_text())
                finally:
                    context.close()

    def test_factory_does_not_change_milk_production_storage_or_offline_cap(self):
        now_ms = 1_700_000_000_000
        synthetic_save = {
            "coins": 7,
            "milk": 5,
            "totalMilk": 5,
            "autoSell": False,
            "owned": {"cow": 2, "machine": 0, "feed": 0, "barn": 1, "factory": 1},
            "lastSaved": now_ms - 3 * 60 * 60 * 1000,
        }
        context, page = self._open_save(synthetic_save, now_ms)
        try:
            self.assertEqual(page.locator("#mps").inner_text(), "2")
            self.assertEqual(page.locator("#milk").inner_text(), "5 / 200")
            self.assertEqual(page.locator("#price").inner_text(), "3.3")
            self.assertEqual(page.locator("#coins").inner_text(), "47.53K")
            self.assertIn("capped at 2h", page.locator("#modalBody").inner_text())
            self.assertIn("sold for 47.52K coins", page.locator("#modalBody").inner_text())
            self.assertEqual(page.locator("#milk").inner_text(), "5 / 200")
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
