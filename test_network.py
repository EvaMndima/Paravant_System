#!/usr/bin/env python
"""
Playwright test to capture network requests and failures
"""
import asyncio
import sys
import io

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

async def test_network():
    failed_requests = []
    all_requests = []

    async with async_playwright() as p:
        print("=" * 70)
        print("NETWORK REQUEST ANALYSIS")
        print("=" * 70)

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture response events
        async def handle_response(response):
            url = response.url
            status = response.status
            all_requests.append({
                "url": url,
                "status": status,
                "method": response.request.method
            })

            # Track failures
            if status >= 400:
                failed_requests.append({
                    "url": url,
                    "status": status,
                    "method": response.request.method
                })
                print(f"  [FAIL] {status} {response.request.method} {url[:80]}")

        page.on("response", handle_response)

        # Load page
        print("\n[1] Loading http://localhost:3001...")
        try:
            await page.goto("http://localhost:3001", wait_until="domcontentloaded", timeout=15000)
            print("  [OK] Page loaded")
        except Exception as e:
            print(f"  [ERROR] {e}")
            await browser.close()
            return

        await page.wait_for_timeout(2000)

        # Print summary
        print("\n" + "=" * 70)
        print("NETWORK SUMMARY")
        print("=" * 70)
        print(f"Total Requests: {len(all_requests)}")
        print(f"Failed Requests (4xx, 5xx): {len(failed_requests)}")

        print("\nFAILED REQUESTS DETAILS:")
        for req in failed_requests:
            print(f"  {req['status']} {req['method']}: {req['url']}")

        print("\nAPI REQUESTS (backend calls):")
        api_reqs = [r for r in all_requests if '/api' in r['url']]
        if api_reqs:
            for req in api_reqs[:10]:
                icon = "OK" if req['status'] < 400 else "FAIL"
                print(f"  [{icon}] {req['status']} {req['method']}: {req['url'][:100]}")
        else:
            print("  No API requests made yet")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_network())
