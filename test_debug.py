#!/usr/bin/env python
"""
Debug script to inspect page structure
"""
import asyncio
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright

async def debug_page():
    async with async_playwright() as p:
        print("=" * 70)
        print("PAGE STRUCTURE DEBUG")
        print("=" * 70)

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("\n[1] Loading page...")
        await page.goto("http://localhost:3001", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        print("\n[2] Page title and URL:")
        print(f"  Title: {await page.title()}")
        print(f"  URL: {page.url}")

        print("\n[3] Navigation/Sidebar links:")
        links = await page.query_selector_all("a, [role='tab'], [role='button']")
        print(f"  Found {len(links)} clickable elements")
        for i, link in enumerate(links[:15]):
            text = await link.text_content()
            classes = await link.get_attribute("class")
            href = await link.get_attribute("href")
            print(f"    {i}: {text[:30]:30} | href={href} | class={classes[:40] if classes else 'none'}")

        print("\n[4] Current route/content:")
        main_content = await page.query_selector("main, [role='main'], .container")
        if main_content:
            text = await main_content.text_content()
            print(f"  Main content found: {text[:100]}...")
        else:
            body_text = await page.text_content("body")
            print(f"  Body text: {body_text[:150]}...")

        print("\n[5] Looking for 'Backtest' text anywhere on page:")
        body_html = await page.content()
        if "Backtest" in body_html:
            print("  [FOUND] 'Backtest' text is in HTML")
            # Find context around it
            idx = body_html.find("Backtest")
            print(f"  Context: ...{body_html[max(0, idx-50):idx+100]}...")
        else:
            print("  [NOT FOUND] 'Backtest' not in HTML")

        print("\n[6] Form elements on page:")
        forms = await page.query_selector_all("form, input, select, button[type='submit']")
        print(f"  Found {len(forms)} form-related elements")

        print("\n[7] Buttons on page:")
        buttons = await page.query_selector_all("button")
        print(f"  Found {len(buttons)} buttons:")
        for i, btn in enumerate(buttons[:20]):
            text = await btn.text_content()
            print(f"    {i}: '{text}'")

        print("\n[8] Try clicking different elements to navigate:")
        # Look for sidebar navigation
        nav_items = await page.query_selector_all("[class*='sidebar'], [class*='nav'], [class*='menu']")
        print(f"  Navigation-like elements: {len(nav_items)}")

        # Try to find and click a Backtest element
        elements_to_try = [
            'a:has-text("Backtest")',
            "[role='tab']:has-text('Backtest')",
            'button:has-text("Backtest")',
            '[href*="backtest"]',
        ]

        for selector in elements_to_try:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    is_visible = await elem.is_visible()
                    is_enabled = await elem.is_enabled()
                    text = await elem.text_content()
                    print(f"  [{selector}] visible={is_visible}, enabled={is_enabled}, text='{text}'")
                    if is_visible and is_enabled:
                        print(f"    -> Attempting click...")
                        await elem.click()
                        await page.wait_for_timeout(1500)
                        new_url = page.url
                        print(f"    -> New URL: {new_url}")
                        break
            except Exception as e:
                pass

        print("\n[9] After navigation, checking content again:")
        page_text = await page.text_content("body")
        if "backtest" in page_text.lower():
            print("  [OK] 'backtest' found in page content")
        else:
            print("  [WARNING] 'backtest' NOT in page content")

        if "configuration" in page_text.lower():
            print("  [OK] Configuration form content found")

        # Look for specific form fields
        print("\n[10] Looking for form fields:")
        selects = await page.query_selector_all("select")
        inputs = await page.query_selector_all("input[type='text'], input[type='number']")
        buttons = await page.query_selector_all("button")
        print(f"  Select dropdowns: {len(selects)}")
        print(f"  Text inputs: {len(inputs)}")
        print(f"  Buttons: {len(buttons)}")

        if selects:
            print("\n  Select options:")
            for select in selects[:2]:
                options = await select.query_selector_all("option")
                name = await select.get_attribute("name")
                print(f"    {name}: {len(options)} options")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
