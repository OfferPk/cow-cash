"""Verify the Baby Cow feature using isolated synthetic saves only.

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
HOUR_MS = 60 * 60 * 1000
MATURATION_MS = 12 * HOUR_MS


class BabyCowTests(unittest.TestCase):
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

    def _open_game(self, synthetic_save=None, now_ms=1_700_000_000_000,
                   controllable_clock=False, freeze_animation=True):
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()
        clock_setup = (
            "let mockedNow = __NOW__; Date.now = () => mockedNow; "
            "window.__setMockNow = value => { mockedNow = value; };"
            if controllable_clock else
            "Date.now = () => __NOW__;"
        )
        raf_setup = "window.requestAnimationFrame = () => 0;" if freeze_animation else ""
        save_setup = (
            "localStorage.setItem('cowCashSave.v1', JSON.stringify(__SAVE__));"
            if synthetic_save is not None else
            "localStorage.removeItem('cowCashSave.v1');"
        )
        init_script = f"""(() => {{
          {clock_setup}
          {raf_setup}
          localStorage.clear();
          {save_setup}
        }})();""".replace("__NOW__", str(now_ms))
        if synthetic_save is not None:
            init_script = init_script.replace("__SAVE__", json.dumps(synthetic_save))
        page.add_init_script(init_script)
        page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")
        return context, page

    @staticmethod
    def _save(now_ms, **overrides):
        state = {
            "coins": 0,
            "milk": 0,
            "totalMilk": 0,
            "autoSell": False,
            "owned": {"cow": 0, "machine": 0, "feed": 0, "barn": 0, "factory": 0},
            "lastSaved": now_ms,
        }
        state.update(overrides)
        return state

    def test_fresh_nonpersistent_context_has_no_cookies_or_origins_before_local_navigation(self):
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        try:
            self.assertEqual(context.cookies(), [])
            self.assertEqual(context.pages, [])
            page = context.new_page()
            self.assertEqual(page.url, "about:blank")
            self.assertEqual(page.evaluate("location.origin"), "null")
            self.assertEqual(context.cookies(), [])

            now_ms = 1_700_000_000_000
            synthetic = self._save(now_ms, coins=15_000)
            page.add_init_script(f"""(() => {{
              Date.now = () => {now_ms};
              window.requestAnimationFrame = () => 0;
              localStorage.clear();
              localStorage.setItem('cowCashSave.v1', JSON.stringify({json.dumps(synthetic)}));
            }})();""")
            page.goto(f"http://127.0.0.1:{self.server.server_port}/", wait_until="load")
            self.assertEqual(page.evaluate("location.origin"), f"http://127.0.0.1:{self.server.server_port}")
            baby_cow = page.locator('[data-id="babyCow"]')
            self.assertEqual(baby_cow.locator(".cost").inner_text(), "15K 🪙")
            baby_cow.click()
            self.assertEqual(page.locator("#coins").inner_text(), "0")
            self.assertIn("Golden/Trophy Cow in 12h", baby_cow.locator(".desc").inner_text())
            self.assertFalse(page.get_by_role("dialog").is_visible())
        finally:
            context.close()

    def test_legacy_save_defaults_baby_cow_to_unowned_without_changing_existing_state(self):
        now_ms = 1_700_000_000_000
        legacy_save = {
            "coins": 0,
            "milk": 4,
            "totalMilk": 12,
            "autoSell": False,
            "owned": {"cow": 1, "machine": 0, "feed": 0, "barn": 0},
            "lastSaved": now_ms,
        }
        context, page = self._open_game(legacy_save, now_ms)
        try:
            baby_cow = page.locator('[data-id="babyCow"]')
            self.assertEqual(baby_cow.locator(".owned").inner_text(), "Owned: 0/1")
            self.assertTrue(baby_cow.is_disabled())
            self.assertEqual(page.locator("#mps").inner_text(), "1")
            self.assertEqual(page.locator("#milk").inner_text(), "4 / 100")
            self.assertEqual(page.locator("#totalMilk").inner_text(), "12")

            page.locator("#saveBtn").click()
            saved = page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertEqual(saved["owned"]["babyCow"], 0)
            self.assertEqual(saved["babyCowPurchasedAt"], 0)
            self.assertEqual(saved["babyCowMaturesAt"], 0)
            self.assertEqual(saved["babyCowMaturedAt"], 0)
            self.assertEqual(saved["milk"], 4)
            self.assertEqual(saved["totalMilk"], 12)
        finally:
            context.close()

    def test_exact_one_time_purchase_deduction_global_boost_and_no_free_milk_or_storage(self):
        now_ms = 1_700_000_000_000
        synthetic = self._save(
            now_ms,
            coins=30_000,
            milk=20,
            totalMilk=20,
            owned={"cow": 2, "machine": 0, "feed": 0, "barn": 0, "factory": 0},
        )
        context, page = self._open_game(synthetic, now_ms)
        try:
            baby_cow = page.locator('[data-id="babyCow"]')
            self.assertEqual(baby_cow.locator(".cost").inner_text(), "15K 🪙")
            baby_cow.click()
            self.assertEqual(page.locator("#coins").inner_text(), "15K")
            self.assertEqual(baby_cow.locator(".owned").inner_text(), "Owned: 1/1")
            self.assertTrue(baby_cow.is_disabled())
            self.assertEqual(page.locator("#mps").inner_text(), "2.3")
            self.assertEqual(page.locator("#milk").inner_text(), "20 / 100")
            self.assertEqual(page.locator("#totalMilk").inner_text(), "20")
            self.assertEqual(page.locator("#price").inner_text(), "1")
            self.assertIn("12h", baby_cow.locator(".desc").inner_text())

            page.evaluate("""() => {
              const button = document.querySelector('[data-id="babyCow"]');
              button.disabled = false;
              button.click();
            }""")
            self.assertEqual(page.locator("#coins").inner_text(), "15K")
            self.assertEqual(baby_cow.locator(".owned").inner_text(), "Owned: 1/1")

            page.locator("#cow").click()
            page.locator("#saveBtn").click()
            saved = page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertEqual(saved["coins"], 15_000)
            self.assertEqual(saved["owned"]["babyCow"], 1)
            self.assertEqual(saved["babyCowPurchasedAt"], now_ms)
            self.assertEqual(saved["babyCowMaturesAt"], now_ms + MATURATION_MS)
            self.assertEqual(saved["babyCowMaturedAt"], 0)
            self.assertAlmostEqual(saved["milk"], 21.15)
            self.assertAlmostEqual(saved["totalMilk"], 21.15)
            self.assertEqual(page.locator("#milkCapacity").get_attribute("max"), "100")
        finally:
            context.close()

    def test_twelve_hour_boundary_and_fixed_mature_bonus_with_controlled_clock(self):
        purchased_at = 1_700_000_000_000
        maturity_at = purchased_at + MATURATION_MS
        before_boundary = maturity_at - 1000
        synthetic = self._save(
            before_boundary,
            owned={"cow": 2, "machine": 0, "feed": 0, "barn": 0, "factory": 0, "babyCow": 1},
            babyCowPurchasedAt=purchased_at,
            babyCowMaturesAt=maturity_at,
            babyCowMaturedAt=0,
        )
        context, page = self._open_game(
            synthetic,
            before_boundary,
            controllable_clock=True,
            freeze_animation=False,
        )
        try:
            baby_cow = page.locator('[data-id="babyCow"]')
            self.assertEqual(page.locator("#mps").inner_text(), "2.3")
            self.assertEqual(baby_cow.locator(".badge").inner_text(), "")
            self.assertIn("1s", baby_cow.locator(".desc").inner_text())
            self.assertFalse(page.get_by_role("dialog").is_visible())

            page.evaluate("(timestamp) => window.__setMockNow(timestamp)", maturity_at)
            page.wait_for_function("document.querySelector('[data-id=\"babyCow\"] .badge').textContent.includes('Golden Cow')")
            self.assertEqual(page.locator("#mps").inner_text(), "17.3")
            self.assertIn("permanent +15 milk/sec", baby_cow.locator(".desc").inner_text())
            saved = page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertEqual(saved["babyCowMaturedAt"], maturity_at)
        finally:
            context.close()

    def test_maturation_while_offline_survives_reload_and_pays_only_post_maturity_segment(self):
        purchased_at = 1_700_000_000_000
        maturity_at = purchased_at + MATURATION_MS
        before_boundary = maturity_at - 60_000
        first_save = self._save(
            before_boundary,
            coins=12,
            milk=5,
            totalMilk=17,
            owned={"cow": 0, "machine": 0, "feed": 0, "barn": 0, "factory": 0, "babyCow": 1},
            babyCowPurchasedAt=purchased_at,
            babyCowMaturesAt=maturity_at,
            babyCowMaturedAt=0,
        )
        first_context, first_page = self._open_game(first_save, before_boundary)
        try:
            self.assertEqual(first_page.locator('[data-id="babyCow"] .badge').inner_text(), "")
            first_page.locator("#saveBtn").click()
            persisted = first_page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
        finally:
            first_context.close()

        after_boundary = maturity_at + HOUR_MS
        second_context, second_page = self._open_game(persisted, after_boundary)
        try:
            self.assertEqual(second_page.locator("#modalTitle").inner_text(), "Welcome back! 🐄")
            self.assertIn("Your cows made 54K milk, sold for 54K coins", second_page.locator("#modalBody").inner_text())
            self.assertEqual(second_page.locator("#coins").inner_text(), "54.01K")
            self.assertEqual(second_page.locator("#milk").inner_text(), "5 / 100")
            self.assertEqual(second_page.locator("#totalMilk").inner_text(), "54.02K")
            self.assertEqual(second_page.locator('[data-id="babyCow"] .badge').inner_text(), "🏆 Golden Cow")

            second_page.get_by_role("button", name="Collect").click()
            second_page.locator("#saveBtn").click()
            after_reload = second_page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertEqual(after_reload["babyCowMaturedAt"], maturity_at)
            self.assertEqual(after_reload["milk"], 5)
            self.assertEqual(after_reload["totalMilk"], 54_017)
        finally:
            second_context.close()

    def test_offline_payout_straddles_maturity_and_keeps_two_hour_cap(self):
        now_ms = 1_700_000_000_000
        purchased_at = now_ms - 13 * HOUR_MS
        maturity_at = purchased_at + MATURATION_MS  # one hour before now
        synthetic = self._save(
            now_ms - 3 * HOUR_MS,
            coins=7,
            milk=10,
            totalMilk=100,
            autoSell=True,
            owned={"cow": 2, "machine": 0, "feed": 0, "barn": 0, "factory": 0, "babyCow": 1},
            babyCowPurchasedAt=purchased_at,
            babyCowMaturesAt=maturity_at,
            babyCowMaturedAt=0,
        )
        context, page = self._open_game(synthetic, now_ms)
        try:
            # The capped two-hour window contains one hour at 2.3 MPS and one at 17.3 MPS.
            expected_milk = (2.3 * HOUR_MS / 1000) + (17.3 * HOUR_MS / 1000)
            self.assertEqual(expected_milk, 70_560)
            self.assertEqual(page.locator("#coins").inner_text(), "70.57K")
            self.assertEqual(page.locator("#milk").inner_text(), "10 / 100")
            self.assertEqual(page.locator("#totalMilk").inner_text(), "70.66K")
            self.assertTrue(page.locator("#autoSell").is_checked())
            self.assertIn("capped at 2h", page.locator("#modalBody").inner_text())
            self.assertIn("70.56K milk", page.locator("#modalBody").inner_text())
            self.assertEqual(page.locator('[data-id="babyCow"] .badge').inner_text(), "🏆 Golden Cow")
        finally:
            context.close()

    def test_mature_bonus_does_not_change_factory_barn_manual_or_auto_sales(self):
        now_ms = 1_700_000_000_000
        purchased_at = now_ms - 13 * HOUR_MS
        maturity_at = purchased_at + MATURATION_MS
        manual_save = self._save(
            now_ms,
            milk=5,
            totalMilk=33,
            owned={"cow": 0, "machine": 0, "feed": 0, "barn": 2, "factory": 1, "babyCow": 1},
            babyCowPurchasedAt=purchased_at,
            babyCowMaturesAt=maturity_at,
            babyCowMaturedAt=maturity_at,
        )
        context, page = self._open_game(manual_save, now_ms)
        try:
            self.assertEqual(page.locator("#price").inner_text(), "3.6")
            self.assertEqual(page.locator("#sellValue").inner_text(), "18")
            self.assertEqual(page.locator("#milk").inner_text(), "5 / 400")
            page.locator("#sellBtn").click()
            self.assertEqual(page.locator("#coins").inner_text(), "18")
            self.assertEqual(page.locator("#milk").inner_text(), "0 / 400")
            self.assertEqual(page.locator("#totalMilk").inner_text(), "33")
        finally:
            context.close()

        auto_save = self._save(
            now_ms,
            autoSell=True,
            totalMilk=0,
            owned={"cow": 0, "machine": 0, "feed": 0, "barn": 1, "factory": 1, "babyCow": 1},
            babyCowPurchasedAt=purchased_at,
            babyCowMaturesAt=maturity_at,
            babyCowMaturedAt=maturity_at,
        )
        auto_context, auto_page = self._open_game(auto_save, now_ms)
        try:
            self.assertEqual(auto_page.locator("#price").inner_text(), "3.3")
            auto_page.locator("#cow").click()
            self.assertEqual(auto_page.locator("#milk").inner_text(), "0 / 200")
            self.assertEqual(auto_page.locator("#totalMilk").inner_text(), "1.2")
            auto_page.locator("#saveBtn").click()
            saved = auto_page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertAlmostEqual(saved["milk"], 0)
            self.assertAlmostEqual(saved["totalMilk"], 1.15)
            self.assertAlmostEqual(saved["coins"], 3.795)
        finally:
            auto_context.close()

    def test_reset_clears_baby_cow_through_default_reset_state(self):
        now_ms = 1_700_000_000_000
        purchased_at = now_ms - 13 * HOUR_MS
        maturity_at = purchased_at + MATURATION_MS
        synthetic = self._save(
            now_ms,
            coins=500,
            milk=50,
            totalMilk=500,
            owned={"cow": 2, "machine": 1, "feed": 1, "barn": 1, "factory": 1, "babyCow": 1},
            babyCowPurchasedAt=purchased_at,
            babyCowMaturesAt=maturity_at,
            babyCowMaturedAt=maturity_at,
        )
        context, page = self._open_game(synthetic, now_ms)
        try:
            page.locator("#resetBtn").click()
            page.get_by_role("button", name="Yes, reset").click()
            self.assertEqual(page.locator("#coins").inner_text(), "0")
            self.assertEqual(page.locator("#milk").inner_text(), "0 / 100")
            self.assertEqual(page.locator("#totalMilk").inner_text(), "0")
            self.assertEqual(page.locator("#mps").inner_text(), "0")
            self.assertEqual(page.locator('[data-id="babyCow"] .owned').inner_text(), "Owned: 0/1")
            self.assertEqual(page.locator('[data-id="babyCow"] .badge').inner_text(), "")
            self.assertEqual(page.evaluate("localStorage.getItem('cowCashSave.v1')"), None)

            page.locator("#saveBtn").click()
            reset_save = page.evaluate("JSON.parse(localStorage.getItem('cowCashSave.v1'))")
            self.assertEqual(reset_save["owned"]["babyCow"], 0)
            self.assertEqual(reset_save["babyCowPurchasedAt"], 0)
            self.assertEqual(reset_save["babyCowMaturesAt"], 0)
            self.assertEqual(reset_save["babyCowMaturedAt"], 0)
        finally:
            context.close()


if __name__ == "__main__":
    unittest.main()
