#!/usr/bin/env python
"""
Direct backtest page test - navigate directly to /backtest route
"""
import asyncio
import sys
import io
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

async def test_backtest_direct():
    async with async_playwright() as p:
        print("=" * 70)
        print("DIRECT BACKTEST PAGE TEST")
        print("=" * 70)

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture errors and network
        errors = []
        api_calls = []

        def handle_console(msg):
            if msg.type == "error":
                errors.append(msg.text[:150])
                print(f"  [ERROR] {msg.text[:100]}")

        async def handle_response(response):
            if "/api/" in response.url or "/backtest" in response.url.lower():
                api_calls.append({
                    "url": response.url,
                    "status": response.status
                })
                print(f"  [API] {response.status} {response.url[:80]}")

        page.on("console", handle_console)
        page.on("response", handle_response)

        # Navigate directly to backtest page
        print("\n[1] Navigating directly to /backtest...")
        try:
            await page.goto("http://localhost:3001/backtest", wait_until="domcontentloaded", timeout=15000)
            print("  [OK] Backtest page loaded")
        except Exception as e:
            print(f"  [FAILED] {e}")
            await browser.close()
            return

        await page.wait_for_timeout(2000)

        # Check page content
        print("\n[2] Checking page content...")
        body_text = await page.text_content("body")

        keywords_to_check = [
            ("BACKTEST", "Page title"),
            ("Configuration", "Config section"),
            ("Strategy", "Strategy field"),
            ("Asset", "Asset field"),
            ("Lookback", "Lookback field"),
            ("Run Backtest", "Run button"),
            ("Timeframe", "Timeframe field"),
        ]

        found = {}
        for keyword, description in keywords_to_check:
            if keyword in body_text:
                found[description] = True
                print(f"  [OK] {description}: '{keyword}' found")
            else:
                found[description] = False
                print(f"  [MISSING] {description}: '{keyword}' NOT found")

        # Look for form elements
        print("\n[3] Looking for form elements...")
        selects = await page.query_selector_all("select")
        inputs = await page.query_selector_all("input")
        buttons = await page.query_selector_all("button")
        print(f"  Select dropdowns: {len(selects)}")
        print(f"  Input fields: {len(inputs)}")
        print(f"  Buttons: {len(buttons)}")

        if selects:
            print("\n  Select field options:")
            for i, select in enumerate(selects[:3]):
                name = await select.get_attribute("name")
                id_attr = await select.get_attribute("id")
                options = await select.query_selector_all("option")
                print(f"    [{i}] {name or id_attr}: {len(options)} options")
                for j, opt in enumerate(options[:3]):
                    opt_text = await opt.text_content()
                    print(f"        - {opt_text}")

        # Find and click Run button
        print("\n[4] Looking for Run Backtest button...")
        run_btn = None
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            text = await btn.text_content()
            if text and ("Run" in text or "run" in text):
                run_btn = btn
                print(f"  [FOUND] Button: '{text}'")
                break

        if run_btn:
            print("\n[5] Clicking Run Backtest button...")
            try:
                await run_btn.click()
                print("  [OK] Button clicked")

                # Wait for backtest to process
                print("  [INFO] Waiting for results (max 15 seconds)...")
                start = time.time()
                while time.time() - start < 15:
                    await page.wait_for_timeout(1000)
                    page_text = await page.text_content("body")

                    # Check for result indicators
                    if any(word in page_text for word in ["return", "win rate", "sharpe", "results", "total return"]):
                        print("  [OK] Results appeared on page")
                        break
                    elif "error" in page_text.lower() and "wrong" in page_text.lower():
                        print("  [ERROR] Error message detected on page")
                        break

            except Exception as e:
                print(f"  [ERROR] {e}")

        # Final check
        print("\n[6] Final page state:")
        final_text = await page.text_content("body")
        if "something went wrong" in final_text.lower():
            print("  [FAILED] Page shows error: 'Something went wrong'")
        elif any(word in final_text.lower() for word in ["result", "return", "performance", "win"]):
            print("  [OK] Backtest results visible on page")
        else:
            print("  [UNCLEAR] Results status unclear")

        print("\n[7] API Calls made:")
        if api_calls:
            for call in api_calls:
                status_icon = "OK" if call["status"] < 400 else "FAIL"
                print(f"  [{status_icon}] {call['status']}: {call['url'][:100]}")
        else:
            print("  No API calls captured")

        print("\n[8] Console Errors:")
        if errors:
            for error in errors[:3]:
                print(f"  - {error}")
        else:
            print("  No console errors")

        await browser.close()

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        form_complete = all(found.values())
        print(f"Form elements visible: {'YES' if form_complete else 'PARTIAL'}")
        print(f"API calls successful: {'YES' if all(c['status'] < 400 for c in api_calls) else 'CHECK LOGS'}")
        print(f"Console errors: {len(errors)}")
        print(f"Overall status: {'WORKING' if form_complete and not errors else 'HAS ISSUES'}")

if __name__ == "__main__":
    asyncio.run(test_backtest_direct())
