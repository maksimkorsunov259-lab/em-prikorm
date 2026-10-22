"""Food marks, clinician clarification, draft protection and retained history."""
import os,tempfile,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 c=pw.chromium.launch_persistent_context(tmp,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],viewport={'width':390,'height':844})
 page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.dismiss());page.goto(URL);page.wait_for_function('!loading&&!pendingWrites')
 page.evaluate("""()=>{p.dob=before(270);Object.keys(p.risks).forEach(k=>p.risks[k]='no');const now=new Date(Date.now()-10000).toISOString();p.meals=[{id:'meal',date:before(8),time:'12:00',createdAt:now,updatedAt:now,kind:'eaten',foodIds:['cod','pistachio'],unknown:false,dish:'Рыба и орех',amount:'Немного',texture:'Подходящая форма',result:'none',note:''},{id:'pending',date:before(1),time:'12:00',createdAt:now,updatedAt:now,kind:'eaten',foodIds:['apple'],unknown:false,dish:'',amount:'',texture:'',result:'pending',note:''}];p.symptoms=[{id:'symptom',date:before(8),time:'13:00',createdAt:now,updatedAt:now,codes:['local'],onset:'soon',mealId:'meal',note:'Первоначальное наблюдение',photo:null}];render('foods');}""")
 expect(page.locator('[data-food=cod] .food-mark')).to_have_text('!');expect(page.locator('[data-food=apple] .food-mark')).to_have_text('◌');expect(page.locator('[data-food=beef] .food-mark')).to_have_text('·')
 original=page.evaluate('JSON.stringify(p.symptoms)');page.locator('[data-food=cod]').click();page.locator('.food-review summary').click();page.locator('[name=reviewMode]').select_option('excluded');page.locator('#food-review-form [type=submit]').click();expect(page.locator('#food-review-error')).to_contain_text('Укажите врача')
 page.locator('[name=reviewNote]').fill('Врач: связь с треской исключена. <img src=x onerror=alert(1)>')
 page.locator('[data-go=help]').first.click();expect(page.locator('#family-help')).to_be_visible();page.locator('#family-help [data-family-about-close]').click();assert 'связь с треской исключена' in page.locator('[name=reviewNote]').input_value()
 page.locator('#food-review-form [type=submit]').click();page.wait_for_function('!pendingWrites');expect(page.locator('.food-status-detail .food-mark')).to_have_text('✓');assert page.evaluate('JSON.stringify(p.symptoms)')==original
 assert 'не реже одного раза в неделю' in page.locator('#screen').inner_text();assert page.locator('#screen img[src=x]').count()==0
 page.evaluate("render('foods')");expect(page.locator('[data-food=cod] .food-mark')).to_have_text('✓');expect(page.locator('[data-food=pistachio] .food-mark')).to_have_text('!')
 for width in [320,390,1440]:
  page.set_viewport_size({'width':width,'height':900});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 page.evaluate("catalogFilter='recorded';render('foods')");expect(page.locator('[data-food=cod] .food-mark')).to_have_text('✓')
 page.evaluate("render('allergens')");page.locator('[data-allergen-group=fish]>summary').click();expect(page.locator('[data-food=cod] .food-mark')).to_have_text('✓')
 page.evaluate("render('report')");text=page.locator('#report-body').inner_text();assert 'Уточнения после консультации' in text and 'Первоначальное наблюдение' in text
 # Native backup includes the clarification; original symptom entries remain intact.
 page.evaluate("render('settings')")
 with page.expect_download() as download:page.locator('[data-runtime=export]').click()
 data=json.loads(Path(download.value.path()).read_text());assert data['patients'][0]['foodReviews'][0]['foodId']=='cod';assert data['patients'][0]['symptoms'][0]['note']=='Первоначальное наблюдение'
 page.reload();page.wait_for_function('!loading&&!pendingWrites');assert page.evaluate("productState(food('cod')).tone")=='green'
 # Returning to automatic interpretation restores the unresolved mark.
 page.evaluate("selectedFood='cod';render('food')");page.locator('.food-review summary').click();page.locator('[name=reviewMode]').select_option('auto');page.locator('#food-review-form [type=submit]').click();expect(page.locator('.food-status-detail .food-mark')).to_have_text('!')
 page.locator('.food-review summary').click();page.locator('[name=reviewMode]').select_option('excluded');page.locator('[name=reviewNote]').fill('Повторное уточнение врача');page.locator('#food-review-form [type=submit]').click();expect(page.locator('.food-status-detail .food-mark')).to_have_text('✓')
 # A second patient inherits neither marks nor clinician conclusions.
 page.evaluate("profiles.push(PrikormModel.patient('Другой ребёнок'));active=1;p=profiles[1];render('foods')");expect(page.locator('[data-food=cod] .food-mark')).to_have_text('·');assert page.evaluate('p.foodReviews.length')==0
 page.evaluate("active=0;p=profiles[0];p.symptoms.push({...p.symptoms[0],id:'new-symptom',date:TODAY,time:'00:00'});render('foods')");expect(page.locator('[data-food=cod] .food-mark')).to_have_text('!')
 page.wait_for_function('!pendingWrites');page.evaluate('navigator.serviceWorker.ready');c.set_offline(True);page.reload();page.wait_for_function('!loading');page.evaluate("render('foods')");expect(page.locator('[data-food=cod] .food-mark')).to_have_text('!');assert page.evaluate('p.foodReviews.length')==1;assert page.evaluate('p.symptoms.length')==2
 assert not errors,errors;c.close()
print('PASS: food marks, incomplete observations, clinician correction and reversal, unchanged symptoms, draft preservation, safe text, separate ingredients/patients, weekly note, catalogue/allergens/report, backup, reload, new symptoms and offline.')
