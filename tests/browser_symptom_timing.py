"""Detailed timing survives saving, editing, backup and reports; old timing stays broad."""
import os,json,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
OPTIONS=[('m0_15','Во время еды или в первые 15 минут'),('m15_60','Через 15–60 минут'),('h1_2','Через 1–2 часа'),('h2_4','Через 2–4 часа'),('h4_8','Через 4–8 часов'),('h8_24','Через 8–24 часа'),('d1_3','Через 1–3 дня'),('after3d','Позже чем через 3 дня'),('unknown','Не могу определить время'),('unrelated','Не связываю симптом с приёмом пищи')]
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=b.new_page(viewport={'width':390,'height':844});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept());p.goto(os.environ.get('APP_URL','http://127.0.0.1:8056/em-prikorm/'))
 def saved():p.wait_for_function('!loading&&!pendingWrites');assert not p.evaluate('storageFailed')
 saved()
 for key,label in OPTIONS:
  p.evaluate("editing=null;render('symptom')");sel=p.locator('[name=onset]');assert sel.locator('option').all_text_contents()==[v for k,v in OPTIONS];expect(sel).to_have_value('unknown')
  p.locator('[name=codes][value=local]').check();sel.select_option(key);p.locator('#symptom-form [type=submit]').click();saved();expect(p.locator('#screen')).to_contain_text(label)
 p.reload();saved();assert p.evaluate('p.symptoms.map(s=>s.onset)')==[k for k,v in OPTIONS]
 p.evaluate("render('report')")
 with p.expect_download() as dl:p.locator('[data-action=download-report]').click()
 file=Path(tmp)/'report.html';dl.value.save_as(file);report=file.read_text();assert all(label in report for key,label in OPTIONS)
 p.evaluate("render('settings')")
 with p.expect_download() as dl:p.locator('[data-runtime=export]').click()
 file=Path(tmp)/'backup.json';dl.value.save_as(file);backup=json.loads(file.read_text());assert [s['onset'] for s in backup['patients'][0]['symptoms']]==[k for k,v in OPTIONS]
 # Retained broad timing appears only while editing the original broad record.
 for key,label in [('soon','Во время еды или вскоре после неё'),('hours','Через несколько часов'),('later','Позже / на следующий день'),('gradual','Симптомы развивались постепенно при регулярном употреблении продукта')]:
  p.evaluate("""async key=>{const c=await DiaryStore.read();c.patients[0].symptoms[0].onset=key;await DiaryStore.write(c)}""",key);p.reload();saved();p.evaluate("editing=p.symptoms[0].id;render('symptom')")
  expect(p.locator('[name=onset]')).to_have_value(key);expect(p.locator('[name=onset] option:checked')).to_have_text(label);p.locator('[name=note]').fill('Уточнили описание');p.locator('#symptom-form [type=submit]').click();saved();assert p.evaluate('p.symptoms[0].onset')==key;p.evaluate("render('report')");expect(p.locator('#report-body')).to_contain_text(label)
 for key in ['hours','h1_2','h2_4','h4_8','h8_24']:
  assert p.evaluate("k=>triage(['repeatVomit'],k)",key)=='urgent'
 for key,label in OPTIONS:
  assert p.evaluate("k=>triage(['breathing'],k)",key)=='emergency'
  assert p.evaluate("k=>triage(['hives','repeatVomit'],k)",key)=='emergency'
 for width in [320,390,1440]:
  p.set_viewport_size({'width':width,'height':900})
  for view,headline in [('today','Маленькие шаги.<br>Без паники.'),('foods','Знакомство без гонки.<br>По плану.'),('plan','План — от врача.<br>Наблюдение — от вас.')]:
   p.evaluate('(v)=>render(v)',view);h=p.locator('#screen h1');assert h.inner_html()==headline
   height,line=h.evaluate('(e)=>[e.getBoundingClientRect().height,parseFloat(getComputedStyle(e).lineHeight)]');assert height<=line*2+1,(width,view,height,line)
  p.evaluate("editing=null;render('symptom')");p.locator('[name=onset]').select_option('m0_15');assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
 assert not errors,errors;b.close()
print('PASS: all 10 timing choices, persistence, report/backup, legacy edits, urgency mapping, two-line headings and narrow forms.')
