"""Manual checking is always available; independent recovery works over a cached older build."""
import functools,http.server,os,shutil,subprocess,tempfile,threading,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 fail_worker=False
 def log_message(self,*args):pass
 def do_GET(self):
  if self.fail_worker and self.path.split('?')[0].endswith('/sw.js'):self.send_error(503);return
  super().do_GET()
def build(app):subprocess.run(['python',str(app/'tools/build_sw.py')],check=True,stdout=subprocess.DEVNULL)
with tempfile.TemporaryDirectory() as tmp,sync_playwright() as pw:
 app=Path(tmp)/'em-prikorm';shutil.copytree(ROOT,app,ignore=shutil.ignore_patterns('.git','__pycache__'))
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=tmp));threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/em-prikorm/'
 browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox']);context=browser.new_context();page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
 page.goto(url);page.wait_for_function('!loading&&!pendingWrites&&offlineReady');page.evaluate("render('settings')")
 check=page.locator('[data-runtime=check-update]');expect(check).to_be_visible();check.click();page.wait_for_function('!updateChecking');assert 'Готового обновления нет' in page.locator('#update-check-status').inner_text()
 context.set_offline(True);check.click();expect(page.locator('#update-check-status')).to_contain_text('Нет подключения');expect(check).to_be_enabled();context.set_offline(False)
 # A fetch failure must be reported, not presented as an up-to-date app.
 Quiet.fail_worker=True;check.click();page.wait_for_function('!updateChecking');assert 'Готового обновления нет' not in page.locator('#update-check-status').inner_text();expect(check).to_be_enabled();Quiet.fail_worker=False
 page.evaluate("p.name='Пациент после восстановления';render('today')");page.wait_for_function('!pendingWrites');saved=page.evaluate('JSON.stringify(collection)')
 # Publish a new build while this tab is still using its old worker.
 file=app/'app.js';file.write_text(re.sub(r"VERSION='[^']+'","VERSION='recovery-test'",file.read_text(),count=1));build(app)
 page.goto(url+'update.html');page.wait_for_function('!document.getElementById("check").disabled');expect(page.locator('#status')).to_contain_text('Обновление загружено');expect(page.locator('#activate')).to_be_disabled();page.locator('#saved').check();expect(page.locator('#activate')).to_be_enabled()
 for width in [320,390,1440]:
  page.set_viewport_size({'width':width,'height':900});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 page.locator('#activate').click();page.wait_for_function("typeof VERSION!=='undefined'&&VERSION==='recovery-test'&&!loading&&!pendingWrites");assert page.evaluate('JSON.stringify(collection)')==saved
 page.locator('[data-go=about]').click();expect(page.locator('dialog.family-about:not(#family-help)')).to_be_visible()
 context.set_offline(True);page.reload();page.wait_for_function('!loading');assert page.evaluate('p.name')=='Пациент после восстановления';page.locator('[data-go=about]').click();expect(page.locator('dialog.family-about:not(#family-help)')).to_be_visible();assert not errors,errors
 browser.close();server.shutdown()
print('PASS: permanent update check, offline/server errors, recovery through old cache, explicit activation, unchanged diaries, About modal and offline after recovery.')
