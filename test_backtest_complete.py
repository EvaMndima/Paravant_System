#!/usr/bin/env python
"""
Complete end-to-end backtest test with form submission
"""
import asyncio
import sys
import io
import time
import json

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

async def test_backtest_complete():
    async with async_playwright() as p:
        print("=" * 70)
        print("END-TO-END BACKTEST TEST")
        print("=" * 70)

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        api_responses = []

        async def handle_response(response):
            if "backtest" in response.url.lower():
                status = response.status
                api_responses.append({
                    "url": response.url,
                    "status": status,
                    "time": time.time()
                })
                print(f"  [BACKTEST API] {status} {response.url[-50:]}")

        page.on("response", handle_response)

        # Load backtest page
        print("\n[1] Loading backtest page...")
        await page.goto("http://localhost:3001/backtest", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        print("  [OK] Page loaded")

        # Check form elements
        print("\n[2] Checking form elements...")
        selects = await page.query_selector_all("select")
        inputs = await page.query_selector_all("input")
        print(f"  Found {len(selects)} select dropdowns and {len(inputs)} input fields")

        # Fill in the form
        print("\n[3] Filling form...")

        # Select strategy (first select)
        if len(selects) >= 1:
            print("  Selecting strategy dropdown...")
            await selects[0].select_option(index=1)  # Select first non-placeholder option
            strategy_text = await selects[0].input_value()
            print(f"    Selected strategy")
            await page.wait_for_timeout(500)

        # Select asset (second select)
        if len(selects) >= 2:
            print("  Selecting asset...")
            await selects[1].select_option(value="BTCUSDT")
            print(f"    Selected BTCUSDT")
            await page.wait_for_timeout(500)

        # Select timeframe (third select)
        if len(selects) >= 3:
            print("  Selecting timeframe...")
            await selects[2].select_option(value="1h")
            print(f"    Selected 1h")
            await page.wait_for_timeout(500)

        # Fill lookback days (first input)
        if len(inputs) >= 1:
            print("  Setting lookback days...")
            await inputs[0].fill("30")
            print(f"    Set to 30 days")
            await page.wait_for_timeout(500)

        # Fill initial capital (second input)
        if len(inputs) >= 2:
            print("  Setting initial capital...")
            await inputs[1].fill("10000")
            print(f"    Set to 10000 USD")
            await page.wait_for_timeout(500)

        # Fill commission rate (third input)
        if len(inputs) >= 3:
            print("  Setting commission rate...")
            await inputs[2].fill("0.001")
            print(f"    Set to 0.1%")
            await page.wait_for_timeout(500)

        # Find and click Run Backtest button
        print("\n[4] Finding Run Backtest button...")
        run_button = None
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            text = await btn.text_content()
            if text and "Run" in text:
                run_button = btn
                is_enabled = await btn.is_enabled()
                print(f"  Found button: '{text.strip()}' (enabled={is_enabled})")
                break

        if run_button:
            print("\n[5] Running backtest...")
            try:
                await run_button.click()
                print("  [OK] Button clicked")

                # Wait for results
                print("  [INFO] Waiting for backtest results (max 20 seconds)...")
                start = time.time()
                results_found = False

                while time.time() - start < 20:
                    await page.wait_for_timeout(1000)
                    page_text = await page.text_content("body")

                    # Look for result keywords
                    result_keywords = [
                        "total return", "win rate", "sharpe", "drawdown",
                        "number of trades", "performance"
                    ]

                    if any(keyword in page_text.lower() for keyword in result_keywords):
                        results_found = True
                        print("  [OK] Backtest results displayed on page!")
                        break

                    # Check for errors
                    if "something went wrong" in page_text.lower():
                        print("  [ERROR] Page shows error message")
                        break

                if not results_found and "something went wrong" not in page_text.lower():
                    print("  [WARNING] Results not clearly detected but no error")

            except Exception as e:
                print(f"  [ERROR] {e}")

        # Final page inspection
        print("\n[6] Final results inspection...")
        final_text = await page.text_content("body")

        # Count occurrences of result keywords
        keywords = ["return", "win", "sharpe", "drawdown", "trades", "metric"]
        keyword_count = sum(final_text.lower().count(kw) for kw in keywords)

        if keyword_count > 5:
            print(f"  [OK] Page contains {keyword_count} result-related keywords")
            print("  [SUCCESS] Backtest functionality is WORKING!")
        else:
            print(f"  [WARNING] Page contains only {keyword_count} result keywords")

        # API call summary
        print("\n[7] API Call Summary:")
        if api_responses:
            for call in api_responses[:5]:
                print(f"  {call['status']}: {call['url'][-60:]}")
            if len(api_responses) > 5:
                print(f"  ... and {len(api_responses) - 5} more calls")
        else:
            print("  No backtest API calls captured")

        await browser.close()

        # Overall result
        print("\n" + "=" * 70)
        success = results_found and keyword_count > 5
        if success:
            print("RESULT: BACKTEST FUNCTIONALITY IS FULLY OPERATIONAL")
        else:
            print("RESULT: BACKTEST NEEDS FURTHER INVESTIGATION")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_backtest_complete())
