"""Catalog selection changes must preserve historical meals and symptoms."""
import os
from playwright.sync_api import sync_playwright,expect
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
NEW=['rabbit','lamb','quail','duck','fish-roe','octopus','scallop','krill','amaranth']
OLD=['chinook','brown-trout','arctic-char','nelma','blue-whiting','baltic-herring','iwashi','sole']
with sync_playwright() as w:
 b=w.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox']);c=b.new_context();p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(URL);p.wait_for_function('!loading&&!pendingWrites&&offlineReady')
 p.evaluate("render('foods')")
 for id in NEW:assert p.locator('[data-food="'+id+'"]').count()==1
 for id in OLD:assert p.locator('[data-food="'+id+'"]').count()==0
 p.wait_for_function('Array.from(document.querySelectorAll(".food-art")).every(i=>i.complete&&i.naturalWidth>0)')
 p.evaluate("render('allergens')")
 for id in OLD:assert p.locator('[data-allergen-food="'+id+'"]').count()==0
 for id,group in [('fish-roe','fishRoe'),('octopus','molluscs'),('scallop','molluscs'),('krill','shellfish')]:assert p.locator('[data-allergen-group="'+group+'"] [data-allergen-food="'+id+'"]').count()==1
 p.evaluate("render('meal')")
 for id in OLD:assert p.locator('[name=foodIds][value="'+id+'"]').count()==0
 for id in NEW:p.locator('[name=foodIds][value="'+id+'"]').check()
 p.locator('#meal-form [type=submit]').click();p.wait_for_function('!pendingWrites')
 assert set(p.evaluate('p.meals[0].foodIds'))==set(NEW)
 # Load an archive that still references all retired fish, plus a linked symptom.
 p.evaluate('''async ids=>{const data=PrikormModel.fresh(),q=data.patients[0],now=new Date().toISOString();q.name='Архив рыб';q.meals=[{id:'legacy-meal',date:before(1),time:'12:00',createdAt:now,updatedAt:now,kind:'eaten',foodIds:ids,unknown:false,dish:'',amount:'Немного',texture:'Мягкая',result:'unknown',note:''}];q.symptoms=[{id:'legacy-symptom',date:before(1),time:'13:00',createdAt:now,updatedAt:now,codes:['local'],onset:'soon',mealId:'legacy-meal',note:'Сохранить связь',photo:null}];await DiaryStore.write(PrikormModel.validate(JSON.parse(JSON.stringify(data))));}''',OLD)
 p.reload();p.wait_for_function('!loading&&!pendingWrites');p.evaluate("render('diary')");assert 'Чавыча' in p.locator('#screen').inner_text();p.locator('[data-edit-meal="legacy-meal"]').click()
 for id in OLD:expect(p.locator('[name=foodIds][value="'+id+'"]')).to_be_checked()
 p.locator('[name=note]').fill('Уточнение без удаления рыбы');p.locator('#meal-form [type=submit]').click();p.wait_for_function('!pendingWrites');assert p.evaluate('p.meals[0].foodIds')==OLD;assert p.evaluate('p.symptoms[0].mealId')=='legacy-meal'
 p.evaluate("render('report')");assert 'Чавыча' in p.locator('#screen').inner_text()
 # Catalog and legacy editing remain available offline; removed items never enter new selections.
 c.set_offline(True);p.reload();p.wait_for_function('!loading');p.evaluate("render('foods')");assert p.locator('[data-food=rabbit]').count()==1;assert p.locator('[data-food=chinook]').count()==0
 p.evaluate("render('meal')");assert p.locator('[name=foodIds][value=chinook]').count()==0;assert not errors,errors;b.close()
print('PASS: additions, allergen groups, illustrations, removed choices, saved meals, legacy backup/edit/report/symptom links and offline.')
