"""Separate roe from fish and preserve legacy offered meals during the UI simplification."""
import os,tempfile
from playwright.sync_api import sync_playwright,expect
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 c=pw.chromium.launch_persistent_context(tmp,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],viewport={'width':390,'height':844});p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.dismiss());p.goto(URL);p.wait_for_function('!loading&&!pendingWrites')
 p.locator('.nav [data-go=foods]').click();assert p.locator('[data-filter]').all_text_contents()==['Все','Богатые железом','В дневнике'];expect(p.locator('.nav [data-go=allergens]')).to_be_visible()
 p.evaluate("""()=>{const now=new Date().toISOString();p.meals=[{id:'roe-old',date:before(1),time:'12:00',createdAt:now,updatedAt:now,kind:'eaten',foodIds:['fish-roe'],unknown:false,dish:'Икра',amount:'',texture:'',result:'none',note:''},{id:'offered-old',date:before(1),time:'12:00',createdAt:now,updatedAt:now,kind:'offered',foodIds:['beef'],unknown:false,dish:'Предлагали говядину',amount:'',texture:'',result:'unknown',note:'Старая запись'}];p.symptoms=[{id:'roe-symptom',date:before(1),time:'13:00',createdAt:now,updatedAt:now,codes:['local'],onset:'soon',mealId:'roe-old',note:'История икры',photo:null}];render('allergens');}""")
 roe=p.locator('[data-allergen-group=fishRoe]');fish=p.locator('[data-allergen-group=fish]');assert roe.locator('[data-allergen-food=fish-roe]').count()==1;assert fish.locator('[data-allergen-food=fish-roe]').count()==0
 assert p.evaluate("groupMeals(allergenGroups.find(g=>g.id==='fish')).length")==0;assert p.evaluate("groupMeals(allergenGroups.find(g=>g.id==='fishRoe')).length")==1
 assert roe.locator('.allergen-context').count()==1;assert fish.locator('.allergen-context').count()==0
 roe.locator('summary').click();assert 'состав аллергенных белков различается' in roe.inner_text()
 p.evaluate("render('report')");assert p.locator('#report-body tr').filter(has=p.get_by_text('Рыбная икра',exact=True)).count()==1;assert 'История икры' in p.locator('#report-body').inner_text()
 p.evaluate("editing=null;render('meal')");assert p.locator('[name=kind] option').all_text_contents()==['Ел','Отказался','Приёма не было'];assert '3–5 дней' in p.locator('.observation-guidance').inner_text();assert 'При острых симптомах не ждите' in p.locator('.observation-guidance').inner_text()
 # An old 'offered' record is never silently converted to consumed.
 p.evaluate("editing='offered-old';render('meal')");assert p.locator('[name=kind]').input_value()=='';p.locator('#meal-form [type=submit]').click();assert p.evaluate("p.meals.find(m=>m.id==='offered-old').kind")=='offered'
 p.locator('[name=kind]').select_option('refused');p.locator('#meal-form [type=submit]').click();p.wait_for_function('!pendingWrites');assert p.evaluate("p.meals.find(m=>m.id==='offered-old').kind")=='refused';assert p.evaluate("productState(food('beef')).tone")=='neutral'
 p.evaluate("render('more')");assert p.locator('#screen [data-go=report]').count()==0;p.locator('.nav [data-go=allergens]').click();p.locator('.allergen-info > summary').click();p.get_by_text('Исключение молока и/или яйца при подозрении на аллергию',exact=True).click();assert 'Не исключайте автоматически оба продукта' in p.locator('#screen').inner_text()
 p.evaluate("render('diary')");expect(p.locator('#screen [data-go=report]')).to_be_visible()
 p.evaluate("render('readiness')");assert 'выталкивающий рефлекс языка угас' in p.locator('[data-ready=swallow]').locator('..').inner_text()
 p.evaluate("render('observation')");assert '3–5 дней' in p.locator('.observation-guidance').inner_text()
 for width in [320,390,1440]:
  p.set_viewport_size({'width':width,'height':900})
  for screen in ['allergens','meal','readiness','observation','more']:
   p.evaluate('(screen)=>render(screen)',screen);assert not p.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,screen)
 p.wait_for_function('!pendingWrites');p.evaluate('navigator.serviceWorker.ready');c.set_offline(True);p.reload();p.wait_for_function('!loading');p.evaluate("render('allergens')");assert p.locator('[data-allergen-group=fishRoe] [data-allergen-food=fish-roe]').count()==1;assert p.evaluate("p.meals.find(m=>m.id==='roe-old').foodIds")==['fish-roe'];assert not errors,errors;c.close()
print('PASS: three catalogue filters, independent roe history/symptoms/report, old food IDs preserved, offered legacy edit requires an explicit outcome, 3–5-day guidance, readiness, milk/egg advice, diary report access, responsive/offline.')
