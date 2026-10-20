"""Actual service-worker replacement, shared-tab notification and write protection."""
import functools,http.server,os,shutil,subprocess,tempfile,threading,re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
def ready(p,url):
 p.goto(url);p.wait_for_function('!loading&&!pendingWrites&&offlineReady');assert not p.evaluate('storageFailed')
def deploy(root,version):
 f=root/'app.js';f.write_text(re.sub(r"VERSION='[^']+'",f"VERSION='{version}'",f.read_text(),count=1))
 subprocess.run(['python',str(root/'tools/build_sw.py')],check=True,stdout=subprocess.DEVNULL)
with tempfile.TemporaryDirectory() as tmp,sync_playwright() as pw:
 base=Path(tmp);app=base/'em-prikorm';shutil.copytree(ROOT,app,ignore=shutil.ignore_patterns('.git','__pycache__'))
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=tmp));threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/em-prikorm/'
 b=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);c=b.new_context(viewport={'width':390,'height':844});p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());ready(p,url);initial=p.evaluate('VERSION')
 assert p.evaluate('view')=='profile';assert p.locator('#update-banner').is_hidden()
 q=c.new_page();ready(q,url);q.evaluate("render('profile')");q.locator('[name=name]').fill('Несохранённая форма')
 deploy(app,'update-test-1');p.evaluate('registration.update()');p.wait_for_function('!!registration.waiting');p.wait_for_selector('#update-banner:not([hidden])')
 for width in [320,390,768]:
  p.set_viewport_size({'width':width,'height':900})
  for view in p.evaluate('Object.keys(screens)'):
   p.evaluate('(v)=>render(v)',view);assert p.locator('#update-banner').is_visible();assert not p.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,view)
 p.evaluate("render('symptom');photoReading=true");p.locator('#update-banner button').click();assert 'загрузки фото' in p.locator('#update-message').inner_text();assert not p.evaluate('updateRequested');p.evaluate("photoReading=false;render('today')")
 # Pending writes finish before activation; profile must survive the replacement.
 p.evaluate("window.realWrite=DiaryStore.write;DiaryStore.write=s=>new Promise(resolve=>{window.finishWrite=()=>realWrite(s).then(resolve)});p.name='Сохранённый профиль';render('today')")
 p.wait_for_function('pendingWrites===1');p.locator('#update-banner button').click();p.wait_for_function('updatePreparing');assert p.evaluate('VERSION')==initial;assert p.locator('#update-banner button').is_disabled()
 p.evaluate('finishWrite()');p.wait_for_function("VERSION==='update-test-1'&&!loading");assert p.evaluate('p.name')=='Сохранённый профиль';assert p.locator('#update-banner').is_hidden()
 # Another tab gets an offer; its unfinished form is not lost to an automatic reload.
 q.wait_for_function('reloadReady');assert q.evaluate('VERSION')==initial;assert q.locator('[name=name]').input_value()=='Несохранённая форма'
 q.locator('#update-banner button').click();assert 'Сначала сохраните' in q.locator('#update-message').inner_text();assert q.evaluate('dirty')
 q.evaluate("render('today')");dismiss=lambda d:d.dismiss();q.on('dialog',dismiss);q.locator('#update-banner button').click();assert q.evaluate('VERSION')==initial
 q.remove_listener('dialog',dismiss);q.on('dialog',lambda d:d.accept());q.locator('#update-banner button').click();q.wait_for_function("VERSION==='update-test-1'&&!loading");assert q.evaluate('p.name')=='Сохранённый профиль'
 q.close();r=c.new_page();ready(r,url);assert r.evaluate('VERSION')=='update-test-1'
 # An error while waiting for a write must keep the old document and offer recovery.
 deploy(app,'update-test-2');r.evaluate('registration.update()');r.wait_for_function('!!registration.waiting');r.on('dialog',lambda d:d.accept())
 r.evaluate("DiaryStore.write=()=>new Promise((resolve,reject)=>{window.failWrite=()=>reject(new Error('QuotaExceededError'))});p.name='Несохранённый профиль';render('today')")
 r.wait_for_function('pendingWrites===1');r.locator('#update-banner button').click();r.wait_for_function('updatePreparing');r.evaluate('failWrite()');r.wait_for_function('storageFailed&&!updatePreparing');assert r.evaluate('VERSION')=='update-test-1';assert not r.evaluate('updateRequested');assert r.locator('#update-banner button').is_disabled();assert r.locator('#storage-error [data-runtime=export]').count()==1
 # The successful update is still usable offline with the saved patient.
 c.set_offline(True);p.reload();p.wait_for_function('!loading');assert p.evaluate('VERSION')=='update-test-1';assert p.evaluate('p.name')=='Сохранённый профиль'
 assert not errors,errors;b.close();server.shutdown()
print('PASS: update banner on all screens/3 widths, no first-install reload, photo/form protection, cancelled update, queued writes, data retained after real SW update, other-tab form preserved, write failure blocks update, offline.')
