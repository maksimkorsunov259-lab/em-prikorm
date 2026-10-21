"""Legacy diary migration, milk allergy context, new species and Russian guidance."""
import json,os,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
def saved(p):
 p.wait_for_function('!loading&&!pendingWrites');assert not p.evaluate('storageFailed')
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 b=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
 c=b.new_context(viewport={'width':390,'height':844},accept_downloads=True);p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(URL);saved(p);p.wait_for_function('offlineReady')
 # A pre-1.0.4 diary with linked symptoms and a second patient survives upgrade.
 p.evaluate("""async()=>{const data=PrikormModel.fresh(),a=data.patients[0],now=new Date().toISOString();a.name='Старый дневник';a.dob=before(240);Object.keys(a.risks).forEach(k=>a.risks[k]='no');delete a.risks.milkAllergy;a.meals=[{id:'old-meal',date:before(8),time:'12:00',createdAt:now,updatedAt:now,kind:'eaten',foodIds:['milk'],unknown:false,dish:'',amount:'ложка',texture:'мягкая',result:'none',note:'Сохранить запись'}];a.symptoms=[{id:'old-symptom',date:before(8),time:'12:30',createdAt:now,updatedAt:now,codes:['local'],onset:'soon',mealId:'old-meal',note:'Сохранить связь',photo:null}];data.patients.push(PrikormModel.patient('Второй'));await DiaryStore.write(data)}""")
 p.reload();saved(p);assert p.evaluate('p.risks.milkAllergy')=='unknown';assert p.evaluate('p.symptoms[0].mealId')=='old-meal';assert p.evaluate('profiles.length')==2
 p.evaluate("render('allergens')");assert p.locator('[data-allergen-group=egg] .allergen-context').count()==0;assert p.locator('[data-allergen-group=peanut] .allergen-context').count()==0
 p.evaluate("render('profile')");p.get_by_label('Установленная аллергия на белки коровьего молока').select_option('yes');p.locator('#patient-form [type=submit]').click();saved(p);p.reload();saved(p);assert p.evaluate('p.risks.milkAllergy')=='yes'
 p.evaluate("render('allergens')");p.locator('[data-allergen-group=milk] summary').click();assert 'установленная аллергия на белки коровьего молока' in p.locator('[data-allergen-group=milk]').inner_text()
 assert 'Перед введением — обсудить с врачом' in p.locator('[data-allergen-group=peanut] summary').inner_text();assert not p.evaluate("reminderAllowed('milk')")
 # Compound milk products, not only the milk entry, get the profile advice.
 dairy=p.evaluate("foods.find(f=>f.id!=='milk'&&f.allergens.includes('milk')).id");p.evaluate("id=>{selectedFood=id;render('food')}",dairy);assert 'перед введением обсудите план с врачом' in p.locator('#screen').inner_text()
 p.evaluate("render('meal')");p.locator('[name=foodIds][value="'+dairy+'"]').check();assert 'перед введением обсудите план с врачом' in p.locator('#screen').inner_text();p.evaluate('dirty=false')
 p.evaluate("render('report')");assert 'установленная аллергия на белки коровьего молока: да' in p.locator('#report-body').inner_text()
 with p.expect_download() as d:p.locator('[data-action=download-report]').click()
 report=Path(tmp)/'report.html';d.value.save_as(report);assert 'установленная аллергия на белки коровьего молока: да' in report.read_text()
 p.evaluate("render('settings')")
 with p.expect_download() as d:p.locator('[data-runtime=export]').click()
 backup=Path(tmp)/'backup.json';d.value.save_as(backup);data=json.loads(backup.read_text());assert data['patients'][0]['risks']['milkAllergy']=='yes';assert data['patients'][0]['meals'][0]['note']=='Сохранить запись'
 p.evaluate("render('patients')");p.locator('[data-patient="1"]').click();saved(p);assert p.evaluate('p.risks.milkAllergy')=='unknown';assert p.evaluate('p.meals.length')==0
 p.evaluate("render('allergens')");assert 'Сведения профиля не уточнены' in p.locator('[data-allergen-group=egg] summary').inner_text();assert 'Перед введением' not in p.locator('[data-allergen-group=egg] summary').inner_text()
 for group,ids in {'shellfish':['shrimp','crab','crayfish','langoustine','lobster'],'molluscs':['squid','mussels','oysters','roman-snail'],'tree-nuts':['brazil-nut']}.items():
  g=p.locator('[data-allergen-group='+group+']');g.locator('summary').click()
  for id in ids:assert g.locator('[data-allergen-food='+id+']').count()==1
 p.evaluate("render('foods')");assert p.locator('.food-row').count()==188;p.wait_for_function('Array.from(document.querySelectorAll(".food-art")).every(i=>i.complete&&i.naturalWidth>0)')
 p.evaluate("render('nutrition')");text=p.locator('#screen').inner_text();assert 'Responsive feeding' not in text;assert 'Кормление с вниманием к сигналам ребёнка' in text;assert 'необходимость обследования на дефицит железа' in text
 p.evaluate("render('safe')");text=p.locator('#screen').inner_text();assert 'Нежелательные и запрещённые продукты' in text and 'Грибы не включайте' in text and 'не обязательный пункт меню' in text
 p.evaluate("render('observation')");text=p.locator('#screen').inner_text();assert 'многодневных пауз' in text and '3–5 дней' in text and 'В практике автора приложения' not in text
 p.evaluate("render('today')");assert p.locator('.hero [data-app-icon]').count()==0;assert p.locator('.app-logo').count()==1
 p.evaluate("render('readiness')");p.locator('#choking-help summary').click();assert 'Раздел дополнится видео об оказании помощи от автора приложения.' in p.locator('#choking-help').inner_text();assert p.locator('#choking-help a[href="tel:112"]').count()==1
 # Author block is consistent across screens and adapts to narrow phones.
 for width in [320,390,768,1440]:
  p.set_viewport_size({'width':width,'height':900})
  for screen in ['today','profile','allergens','safe','nutrition','observation','report']:
   p.evaluate('(s)=>render(s)',screen);assert not p.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,screen);assert p.locator('#author-slot .em-author-qr img').bounding_box()['width']==(94 if width<=380 else 112)
 p.locator('#author-slot').screenshot(path=str(Path(tmp)/'author-desktop.png'))
 assert not errors,errors;c.close();b.close()
print('PASS: old diary migration, separate patient milk history, dairy warnings, report/backup, six distinct new foods and images, Russian guidance, conditional risk labels, author block and responsive layouts.')
