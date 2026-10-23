"""The report uses navigation group order and actual consumed foods, including exports."""
import os,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);c=b.new_context(viewport={'width':390,'height':844});page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(os.environ.get('APP_URL','http://127.0.0.1:8055/em-prikorm/'));page.wait_for_function('!loading&&!pendingWrites')
 page.evaluate("""()=>{const now=new Date().toISOString(),row=(id,foodIds,kind='eaten',unknown=false)=>({id,date:TODAY,time:'00:00',createdAt:now,updatedAt:now,kind,foodIds,unknown,dish:'Блюдо <тест>',amount:'немного',texture:'мягкая',result:kind==='eaten'?'none':'unknown',note:''});p.risks.peanutReaction='yes';p.risks.peanutAllergy='unknown';p.meals=[row('fish',['cod','atlantic-salmon']),row('roe',['fish-roe']),row('nuts',['almond','walnut']),row('refused',['egg'],'refused'),row('legacy',['peanut'],'offered'),row('unknown',[],'eaten',true),row('mustard',['mustard'])];render('report');}""")
 page.wait_for_function('!pendingWrites');assert not page.evaluate('storageFailed')
 labels=page.locator('.report-context dt').all_text_contents();assert labels==['Тяжёлый атопический дерматит','Установленная аллергия на яйцо','Установленная аллергия на белки коровьего молока','Установленная аллергия на арахис','Индивидуальные особенности'];assert page.locator('.report-context dd').nth(3).inner_text()=='не уточнено';assert 'В анамнезе отмечена реакция на арахис' in page.locator('#report-body').inner_text()
 expected=page.evaluate('allergenGroups.map(g=>g.id)');actual=page.locator('[data-report-allergen]').evaluate_all('(rows)=>rows.map(r=>r.dataset.reportAllergen)');assert actual==expected+['mustard']
 fish=page.locator('[data-report-allergen=fish]');expect(fish.locator('td').first).to_have_text('1');assert 'Треска' in fish.inner_text() and 'лосось' in fish.inner_text().lower();assert 'икра' not in fish.inner_text().lower()
 for key in ['egg','peanut']:expect(page.locator('[data-report-allergen='+key+'] td').first).to_have_text('Нет записей');assert page.locator('[data-report-allergen='+key+'] .report-foods').count()==0
 assert page.locator('[data-report-allergen=fishRoe] .report-foods').count()==1;assert page.locator('[data-report-allergen=tree-nuts] .report-foods').count()==1
 assert '1 записей об употреблении с неуточнённым составом' in page.locator('#report-body').inner_text()
 for width in [320,390,1440]:
  page.set_viewport_size({'width':width,'height':900});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path='/tmp/report-summary-'+str(width)+'.png',full_page=True)
 with page.expect_download() as download:page.locator('[data-action=download-report]').click()
 path=Path(tmp)/'report.html';download.value.save_as(path);html=path.read_text();assert 'Тяжёлый АД' not in html;assert 'Установленная аллергия на арахис' in html
 export=c.new_page();export.set_content(html);assert export.locator('[data-report-allergen]').evaluate_all('(rows)=>rows.map(r=>r.dataset.reportAllergen)')==actual;expect(export.locator('.report-context dd').nth(3)).to_have_text('не уточнено');export.emulate_media(media='print');assert export.locator('.report-context dt').count()==5;export.pdf(path=str(Path(tmp)/'report.pdf'));export.close()
 page.evaluate("render('profile')");page.locator('[name=peanutAllergy]').select_option('yes');page.locator('#patient-form [type=submit]').click();page.wait_for_function('!pendingWrites');page.evaluate("render('report')");expect(page.locator('.report-context dd').nth(3)).to_have_text('да')
 page.evaluate('navigator.serviceWorker.ready');c.set_offline(True);page.reload();page.wait_for_function('!loading&&!pendingWrites');page.evaluate("render('report')");expect(page.locator('.report-context dd').nth(3)).to_have_text('да');assert page.locator('[data-report-allergen]').count()==len(actual);assert not errors,errors;c.close();b.close()
print('PASS: context lines, explicit peanut allergy, ordered allergen groups, consumed foods only, mixed-meal deduplication, separate roe, legacy entries, HTML/PDF and offline.')
