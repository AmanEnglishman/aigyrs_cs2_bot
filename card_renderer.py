# card_renderer.py
from playwright.async_api import async_playwright
from jinja2 import Template
from pathlib import Path

TEMPLATE_PATH = Path("templates/faceit_card.html")
OUTPUT_PATH = Path("static/card.png")

async def render_faceit_card(data: dict) -> Path:
    html = Template(
        TEMPLATE_PATH.read_text(encoding="utf-8")
    ).render(**data)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 820, "height": 440})
        await page.set_content(html)
        await page.screenshot(path=str(OUTPUT_PATH))
        await browser.close()

    return OUTPUT_PATH
