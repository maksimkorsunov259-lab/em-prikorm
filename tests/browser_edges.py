"""Data recovery, concurrent tabs and late photo loading. Synthetic data only."""
import json, os, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
ROOT=Path(__file__).resolve().parents[1]
def ready(p):
 p.goto(URL);p.wait_for_function('!loading&&!pendingWrites');assert not p.evaluate('storageFailed')
def backup(p,path):
 with p.expect_download() as d:p.locator('#storage-error [data-runtime=export]').click()
 d.value.save_as(path);return json.loads(path.read_text())
with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
 b=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 # Read denial must not create an export of an empty replacement.
 c=b.new_context();p=c.new_page();p.add_init_script("Object.defineProperty(window,'indexedDB',{get(){throw new Error('Storage denied')}})")
 p.goto(URL);p.wait_for_selector('#storage-error:not([hidden])');assert not p.evaluate('canExport');assert p.locator('#storage-error [data-runtime=export]').count()==0;assert p.locator('#screen a[href="tel:112"]').count()==1;c.close()
 # Unsupported snapshot is preserved verbatim for recovery, not replaced by defaults.
 c=b.new_context(accept_downloads=True);p=c.new_page();ready(p)
 original={'app':'em-prikorm','schemaVersion':999,'original':'Keep these data'}
 p.evaluate('(data)=>DiaryStore.write(data)',original);p.reload();p.wait_for_selector('#storage-error:not([hidden])');assert backup(p,Path(tmp)/'raw.json')==original
 assert p.evaluate('DiaryStore.read()')==original;c.close()
 # Optimistic concurrency: second tab cannot overwrite first tab; unsaved changes can be recovered.
 c=b.new_context(accept_downloads=True);p=c.new_page();ready(p);q=c.new_page();ready(q)
 p.evaluate("p.name='First tab';render('today')");p.wait_for_function('!pendingWrites')
 q.evaluate("p.name='Second tab';render('today')");q.wait_for_selector('#storage-error:not([hidden])');assert 'другой вкладке' in q.locator('#storage-error').inner_text();q.evaluate("render('profile')");assert q.locator('[name=name]').is_disabled()
 assert backup(q,Path(tmp)/'conflict.json')['patients'][0]['name']=='Second tab'
 q.on('dialog',lambda d:d.accept());q.reload();q.wait_for_function('!loading');assert q.evaluate('p.name')=='First tab';c.close()
 # Quota failure: editing stops, recovery keeps the unsaved change, disk keeps earlier version.
 c=b.new_context(accept_downloads=True);p=c.new_page();ready(p);p.on('dialog',lambda d:d.accept())
 p.evaluate("DiaryStore.write=async()=>{throw new Error('QuotaExceededError')};p.name='Unsaved name';render('today')")
 p.wait_for_selector('#storage-error:not([hidden])');assert 'QuotaExceededError' in p.locator('#storage-error').inner_text();assert backup(p,Path(tmp)/'quota.json')['patients'][0]['name']=='Unsaved name'
 p.reload();p.wait_for_function('!loading');assert p.evaluate('p.name')=='Новый пациент';c.close()
 # A photo finishing after a patient switch must never attach to the new profile.
 c=b.new_context();p=c.new_page();ready(p);p.on('dialog',lambda d:d.accept())
 p.evaluate("profiles.push(PrikormModel.patient('Second'));render('symptom');readImage=()=>new Promise(resolve=>window.finishPhoto=resolve);void 0")
 p.locator('#symptom-photo').set_input_files(str(ROOT/'assets/image-9bfbd99af1d3.png'));p.wait_for_function('photoReading');assert p.locator('#symptom-form [type=submit]').is_disabled()
 p.evaluate("dirty=false;render('patients')");p.locator('[data-patient="1"]').click();p.evaluate("render('symptom');finishPhoto('data:image/png;base64,iVBORw0KGgo=')");p.wait_for_function('!photoReading');assert p.evaluate('photoDraft') is None;assert p.locator('#photo-preview img').count()==0
 # Cache activation deletes only this application's old versions.
 p.evaluate("Promise.all([caches.open('em-moloko:foreign-test'),caches.open('em-yaytso:foreign-test'),caches.open('dyshu-diary:foreign-test')])")
 p.wait_for_function('offlineReady');assert p.evaluate("caches.keys().then(keys=>['em-moloko:foreign-test','em-yaytso:foreign-test','dyshu-diary:foreign-test'].every(k=>keys.includes(k)))")
 assert p.evaluate("navigator.serviceWorker.controller.scriptURL.endsWith('/em-prikorm/sw.js')")
 c.close();b.close()
 print('PASS: read failure, exact raw recovery, concurrent-tab protection, quota failure recovery, late photo isolation, separate PWA caches.')
