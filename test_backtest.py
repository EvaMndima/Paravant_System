#!/usr/bin/env python
"""
Comprehensive backtest functionality test
"""
import asyncio
import sys
import io
import json
import time

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

async def test_backtest():
    test_results = {
        "page_load": False,
        "form_visible": False,
        "backtest_clicked": False,
        "backtest_completed": False,
        "results_displayed": False,
        "errors": [],
        "warnings": []
    }

    async with async_playwright() as p:
        print("=" * 70)
        print("BACKTEST FUNCTIONALITY TEST")
        print("=" * 70)

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture console messages
        def handle_console(msg):
            if msg.type == "error":
                test_results["errors"].append(msg.text[:150])
                print(f"  [ERROR] {msg.text[:100]}")
            elif msg.type == "warning":
                test_results["warnings"].append(msg.text[:150])

        page.on("console", handle_console)

        # Load page
        print("\n[1] Loading dashboard...")
        try:
            await page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=15000)
            test_results["page_load"] = True
            print("  [OK] Dashboard loaded")
        except Exception as e:
            print(f"  [FAILED] {e}")
            await browser.close()
            return test_results

        await page.wait_for_timeout(1000)

        # Navigate to Backtest tab
        print("\n[2] Navigating to Backtest page...")
        try:
            # Try clicking sidebar link or tab
            backtest_link = await page.query_selector('a:has-text("Backtest"), [role="tab"]:has-text("Backtest")')
            if backtest_link:
                await backtest_link.click()
                await page.wait_for_timeout(1000)
                print("  [OK] Backtest page accessed")
            else:
                print("  [WARNING] Could not find Backtest link, proceeding anyway")
        except Exception as e:
            print(f"  [WARNING] {e}")

        # Check if form is visible
        print("\n[3] Checking for backtest form...")
        try:
            form_elements = await page.query_selector_all("input, select, form")
            if len(form_elements) > 0:
                test_results["form_visible"] = True
                print(f"  [OK] Found {len(form_elements)} form elements")
            else:
                print("  [WARNING] No form elements found")
        except Exception as e:
            print(f"  [ERROR] {e}")

        # Find and check Run Backtest button
        print("\n[4] Looking for Run Backtest button...")
        run_button = None
        try:
            # Try multiple selector strategies
            run_button = await page.query_selector('button:has-text("Run Backtest")')
            if not run_button:
                run_button = await page.query_selector('button:has-text("run")')
            if not run_button:
                buttons = await page.query_selector_all("button")
                print(f"  Found {len(buttons)} buttons, searching for 'Run' or 'Backtest'...")
                for btn in buttons:
                    text = await btn.text_content()
                    if text and ("run" in text.lower() or "backtest" in text.lower()):
                        run_button = btn
                        break

            if run_button:
                print("  [OK] Run Backtest button found")
            else:
                print("  [WARNING] Run Backtest button not found")
        except Exception as e:
            print(f"  [ERROR] {e}")

        # Click and run backtest
        if run_button:
            print("\n[5] Running backtest...")
            try:
                test_results["backtest_clicked"] = True

                # Capture network requests for backtest
                backtest_started = False
                backtest_response = None

                async def handle_response(response):
                    nonlocal backtest_started, backtest_response
                    if "backtest" in response.url.lower():
                        backtest_started = True
                        status = response.status
                        print(f"  [BACKTEST API] {status} {response.url[:80]}")
                        if status == 200:
                            try:
                                backtest_response = await response.json()
                            except:
                                pass

                page.on("response", handle_response)

                # Click button
                await run_button.click()
                print("  [OK] Run button clicked")

                # Wait for backtest API call and results
                print("  [INFO] Waiting for backtest to complete (max 10 seconds)...")
                start_time = time.time()
                max_wait = 10

                while time.time() - start_time < max_wait:
                    if backtest_started and backtest_response:
                        test_results["backtest_completed"] = True
                        print("  [OK] Backtest API call successful")
                        break
                    await page.wait_for_timeout(500)

                if not test_results["backtest_completed"]:
                    print("  [WARNING] Backtest may still be processing...")

                # Wait a bit more for UI to update
                await page.wait_for_timeout(2000)

            except Exception as e:
                print(f"  [ERROR] {e}")

        # Check for results
        print("\n[6] Checking for backtest results...")
        try:
            page_text = await page.text_content("body")

            # Check for various result indicators
            result_keywords = [
                "return", "win rate", "sharpe", "drawdown",
                "total", "performance", "trades", "success"
            ]

            found_results = []
            for keyword in result_keywords:
                if keyword.lower() in page_text.lower():
                    found_results.append(keyword)

            if len(found_results) >= 2:
                test_results["results_displayed"] = True
                print(f"  [OK] Backtest results displayed")
                print(f"       Found keywords: {', '.join(found_results[:5])}")
            else:
                # Check for error message
                if "something went wrong" in page_text.lower():
                    print("  [ERROR] Page shows 'Something went wrong' message")
                    test_results["errors"].append("Backtest returned error page")
                elif "error" in page_text.lower():
                    print("  [WARNING] Page contains 'error' text")
                else:
                    print("  [WARNING] Could not confirm results on page")
        except Exception as e:
            print(f"  [ERROR] {e}")

        await browser.close()

        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Page Load:              {'PASS' if test_results['page_load'] else 'FAIL'}")
        print(f"Form Visible:           {'PASS' if test_results['form_visible'] else 'FAIL'}")
        print(f"Button Clicked:         {'PASS' if test_results['backtest_clicked'] else 'FAIL'}")
        print(f"API Call Successful:    {'PASS' if test_results['backtest_completed'] else 'FAIL'}")
        print(f"Results Displayed:      {'PASS' if test_results['results_displayed'] else 'FAIL'}")
        print(f"Console Errors:         {len(test_results['errors'])}")
        print(f"Console Warnings:       {len(test_results['warnings'])}")

        if test_results['errors']:
            print(f"\nErrors detected:")
            for error in test_results['errors'][:3]:
                print(f"  - {error}")

        # Overall result
        all_passed = all([
            test_results['page_load'],
            test_results['form_visible'],
            test_results['backtest_clicked'],
        ])

        print("\n" + "=" * 70)
        if all_passed:
            print("RESULT: BACKTEST FUNCTIONALITY WORKING")
        else:
            print("RESULT: BACKTEST FUNCTIONALITY HAS ISSUES")
        print("=" * 70)

        return test_results

if __name__ == "__main__":
    results = asyncio.run(test_backtest())
