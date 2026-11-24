"""Render the Russian handout from the same markup patients see in the app."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import os

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PRINT_CSS = """
@page { size: A4; margin: 10mm 14mm; }
body { margin: 0; font: 10.8pt/1.27 Arial, sans-serif; color: #1d2925; }
h1 { font-size: 21pt; margin: 0 0 3mm; }
h2 { font-size: 13pt; margin: 0 0 1.3mm; }
h3 { font-size: 12pt; margin: 0 0 1.3mm; }
p { margin: 1.2mm 0; }
.choking-guide > section { margin: 2.6mm 0; }
.choking-call, .choking-unconscious {
  border-left: 1.2mm solid #9c3027; padding: 2mm 3mm; background: #fff1ed;
}
.choking-jump { display: none; }
.choking-phones a { font-size: 14pt; font-weight: bold; color: #842920; }
.choking-phones span { margin-left: 2mm; }
.choking-ages { display: grid; gap: 3mm; grid-template-columns: 1fr 1fr; margin: 2mm 0; }
.choking-ages section { border: .3mm solid #a6b8a2; padding: 2.2mm; border-radius: 2mm; }
ol { padding-left: 5mm; margin: 0; }
li + li { margin-top: 1mm; }
a { color: #284e40; }
.choking-source, footer { color: #45554a; font-size: 9pt; }
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    with ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=ROOT)) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH'))
            page = browser.new_page(service_workers='block')
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            page.wait_for_function("!loading && !pendingWrites")
            page.evaluate("render('readiness')")
            guide = page.locator('#choking-help .choking-guide').evaluate('(element) => element.outerHTML')
            original = page.locator('#choking-help .choking-files a').last.get_attribute('href')
            output = page.locator('#choking-help .choking-files a').first.get_attribute('href')
            page.set_content('<html lang="ru"><head><title>Если ребёнок подавился — Ем Прикорм</title></head>'
                             '<body><h1>Если ребёнок подавился</h1>' + guide +
                             '<footer><a href="' + original + '">Оригинал схемы RCUK на английском (PDF)</a></footer></body></html>')
            # Preserve the heading hierarchy independently of the surrounding app dialog.
            page.evaluate("""() => {
                for (const heading of document.querySelectorAll('h3, h4')) {
                    const printHeading = document.createElement(heading.tagName === 'H3' ? 'h2' : 'h3');
                    printHeading.textContent = heading.textContent;
                    heading.replaceWith(printHeading);
                }
            }""")
            page.add_style_tag(content=PRINT_CSS)
            page.pdf(path=ROOT / urlsplit(output).path, prefer_css_page_size=True,
                     print_background=True, tagged=True)
            browser.close()
        server.shutdown()


if __name__ == '__main__':
    main()
