"""Synthetic persistence, backup, report, triage and offline flows. No real patient data."""
import os,json,tempfile,datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
ROOT=Path(__file__).resolve().parents[1]
def saved(p):
 p.wait_for_function('!loading&&!pendingWrites');assert not p.evaluate('storageFailed'),p.locator('#storage-error').inner_text()
def go(p,v):p.evaluate('(v)=>render(v)',v)
def init(p):p.goto(URL);p.wait_for_function('!loading');saved(p)
def profile(p,name,dob):
 p.locator('[name=name]').fill(name);p.locator('[name=dob]').fill(dob)
 for key in ['severeEczema','eggAllergy','milkAllergy','peanutReaction','complex']:p.locator('[name='+key+']').select_option('no')
 p.locator('#patient-form [type=submit]').click();saved(p)
with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
 c=pw.chromium.launch_persistent_context(str(Path(tmp)/'browser'),executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],viewport={'width':390,'height':844},accept_downloads=True,timezone_id='Europe/Moscow');p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());init(p)
 p.wait_for_function('offlineReady');assert p.evaluate('view')=='profile';assert p.evaluate('p.meals.length')==0
 dob=(datetime.date.today()-datetime.timedelta(days=240)).isoformat();profile(p,'Тестовый Миша',dob)
 p.reload();saved(p);assert p.evaluate('p.name')=='Тестовый Миша';assert p.evaluate('TODAY')==p.evaluate('PrikormModel.localDate()')
 p.locator('[data-action=new-meal]').first.click();p.locator('#ingredient-search').fill('треска');p.locator('[name=foodIds][value=cod]').check();p.locator('#ingredient-search').fill('фисташка');p.locator('[name=foodIds][value=pistachio]').check();p.locator('[name=amount]').fill('Две ложки');p.locator('[name=result]').select_option('none');p.locator('#meal-form [type=submit]').click();saved(p)
 assert p.evaluate('p.meals.length')==1;meal_id=p.evaluate('p.meals[0].id')
 p.locator('[data-action=new-symptom]').click();p.locator('[name=date]').fill('');p.locator('[name=codes][value=breathing]').check();assert p.locator('#triage-dialog').is_visible();assert p.locator('#triage-dialog a[href="tel:112"]').count()==1
 p.locator('[data-action=close-triage]').click();p.locator('[name=codes][value=breathing]').uncheck();p.locator('[name=codes][value=repeatVomit]').check();p.locator('[name=onset]').select_option('hours');assert 'срочная медицинская оценка' in p.locator('#triage-body').inner_text();p.locator('[data-action=close-triage]').click()
 p.locator('[name=codes][value=repeatVomit]').uncheck();p.locator('[name=codes][value=local]').check();p.locator('[name=date]').fill(p.evaluate('TODAY'));p.locator('[name=mealId]').select_option(meal_id);p.locator('#symptom-photo').set_input_files(str(ROOT/'assets/image-9bfbd99af1d3.png'));p.wait_for_function('!photoReading&&!!photoDraft');p.locator('#symptom-form [type=submit]').click();saved(p)
 p.reload();saved(p);assert p.evaluate('p.symptoms.length')==1;assert p.evaluate('p.symptoms[0].photo.startsWith("data:image/png")')
 go(p,'readiness');p.locator('[data-ready=head]').check();saved(p);go(p,'observation');p.locator('#observation-mode').check();saved(p)
 go(p,'plan');p.locator('[name=plan]').fill('Тестовый план врача');p.locator('[name=foodId]').select_option('pistachio');p.locator('[name=doctorStatus]').select_option('avoid');p.locator('[name=doctorNote]').fill('Не предлагать до оценки врача');p.locator('[name=confirmed]').check();p.locator('#plan-form [type=submit]').click();saved(p);assert not p.evaluate("reminderAllowed('pistachio')")
 go(p,'report');p.locator('#report-questions').fill('Вопрос для врача');saved(p)
 assert p.locator('.report-photo').count()==0
 with p.expect_download() as d:p.locator('[data-action=download-report]').click()
 dest=Path(tmp)/'report.html';d.value.save_as(dest);assert 'Вопрос для врача' in dest.read_text();assert '<img class="report-photo"' not in dest.read_text();assert 'Учеб' not in dest.read_text()
 p.locator('#include-photos').check();assert p.locator('.report-photo').count()==1
 p.pdf(path=str(Path(tmp)/'report.pdf'),format='A4');assert (Path(tmp)/'report.pdf').stat().st_size>1000
 go(p,'patients');p.locator('[data-go=newPatient]').click();profile(p,'Тестовая Лиза',dob);assert p.evaluate('p.meals.length')==0;assert p.evaluate('p.symptoms.length')==0
 go(p,'patients');p.locator('[data-patient="0"]').click();saved(p);assert p.evaluate('p.meals.length')==1;assert p.evaluate('p.ready.head&&p.observationMode')
 go(p,'settings')
 with p.expect_download() as d:p.locator('[data-runtime=export]').click()
 backup=Path(tmp)/'backup.json';d.value.save_as(backup);data=json.loads(backup.read_text());assert len(data['patients'])==2
 bad=Path(tmp)/'bad.json';bad.write_text('{"app":"em-yaytso","schemaVersion":1}')
 p.locator('#import-file').set_input_files(str(bad));p.wait_for_function('!!document.querySelector("#import-error").textContent');assert p.evaluate('profiles.length')==2
 p.locator('#import-file').set_input_files(str(backup));p.wait_for_selector('[data-runtime=import-add]');p.locator('[data-runtime=import-add]').click();saved(p);assert p.evaluate('profiles.length')==4;assert p.evaluate('new Set(profiles.map(q=>q.id)).size')==4
 go(p,'settings');p.locator('#import-file').set_input_files(str(backup));p.wait_for_selector('[data-runtime=import-replace]');p.locator('[data-runtime=import-replace]').click();saved(p);assert p.evaluate('profiles.length')==2
 go(p,'diary');p.locator('[data-remove-meal]').click();saved(p);assert p.evaluate('p.meals.length')==0;assert p.evaluate('p.symptoms[0].mealId') is None
 p.reload();saved(p);assert p.evaluate('p.symptoms.length')==1
 # Date validation and safe rendering of user text.
 go(p,'profile');profile(p,'<img src=x onerror="window.pwned=1">',dob);assert p.locator('#patient-name img').count()==0;assert p.evaluate('window.pwned') is None
 go(p,'meal');p.locator('[name=date]').fill('2999-01-01');p.locator('[name=foodIds][value=egg]').check();p.locator('#meal-form [type=submit]').click();assert p.evaluate('p.meals.length')==0
 # Read every screen on narrow and desktop widths with a real saved profile.
 p.evaluate('dirty=false')
 for width in [320,390,768,1440]:
  p.set_viewport_size({'width':width,'height':900})
  for view in p.evaluate('Object.keys(screens)'):
   go(p,view);assert p.evaluate('view')==view;assert p.evaluate('Array.from(document.querySelectorAll("[data-go]")).every(b=>Object.hasOwn(screens,b.dataset.go))');assert not p.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,view);assert p.locator('#author-slot img').count()==2
 go(p,'foods');assert p.locator('.food-row').count()==187;go(p,'allergens');assert p.locator('.allergen-group').count()==12
 # Readiness and entire app shell survive offline reload, including catalogue.
 p.evaluate('dirty=false');p.wait_for_function('offlineReady');c.set_offline(True);p.reload();saved(p);go(p,'foods');p.wait_for_function('Array.from(document.querySelectorAll(".food-art")).every(i=>i.complete&&i.naturalWidth>0)');assert p.locator('.food-row').count()==187
 c.set_offline(False)
 # Distinct installation identity and service-worker scope.
 manifest=p.evaluate("fetch('./manifest.webmanifest').then(r=>r.json())");assert manifest['id']=='/em-prikorm/';assert manifest['name']=='ЕмПрикорм';assert p.evaluate('navigator.serviceWorker.controller.scriptURL').endswith('/em-prikorm/sw.js')
 cdp=c.new_cdp_session(p);install=cdp.send('Page.getInstallabilityErrors');assert not install.get('installabilityErrors'),install
 assert not errors,errors
 print('PASS: persistence/reload, two patients, photos, readiness/plan/questions, backup merge/replace, invalid imports, report/PDF, deletion/link integrity, XSS escaping, triage before validation, 84 responsive screens, offline, manifest and Chromium installability.')
 c.close()
