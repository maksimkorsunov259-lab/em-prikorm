"""Weekly in-app reminders and upper-right return from choking help."""
import os,tempfile
from playwright.sync_api import sync_playwright,expect
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 c=pw.chromium.launch_persistent_context(tmp,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],viewport={'width':390,'height':844})
 page=c.new_page();errors=[];prompts=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:(prompts.append(d.type),d.dismiss()));page.goto(URL);page.wait_for_function('!loading&&!pendingWrites')
 page.evaluate("render('profile')");page.locator('[name=name]').fill('Несохранённое имя');trigger=page.locator('[data-action=choking-help]');dialog=page.locator('#triage-dialog');close=dialog.locator('[data-action=close-triage]')
 for width in [320,390,1440]:
  page.set_viewport_size({'width':width,'height':900});trigger.click();expect(dialog).to_be_visible();expect(close).to_have_text('← Вернуться');expect(close).to_be_focused()
  assert dialog.evaluate('e=>e.matches(":modal")');assert not dialog.evaluate('e=>e.scrollWidth>e.clientWidth')
  cb=close.bounding_box();db=dialog.bounding_box();assert cb['x']+cb['width']/2>db['x']+db['width']/2;assert 15<=db['x']+db['width']-cb['x']-cb['width']<=23;assert cb['y']<db['y']+35
  assert cb['y']+cb['height']<=dialog.locator('h2').bounding_box()['y']
  assert dialog.locator('a[href="tel:112"]').count()==1
  dialog.evaluate('e=>e.scrollTop=e.scrollHeight');cb=close.bounding_box();assert cb['y']<db['y']+35
  close.click();expect(dialog).not_to_be_visible();expect(trigger).to_be_focused();assert page.locator('[name=name]').input_value()=='Несохранённое имя'
  trigger.click();page.keyboard.press('Escape');expect(dialog).not_to_be_visible()
 assert not prompts,prompts
 # Reuse for urgent triage must restore the original bottom action and label.
 page.evaluate("dirty=false;showTriage('emergency')");expect(close).to_have_text('Помощь оказана — вернуться к записи');assert 'choking-help' not in (dialog.get_attribute('class') or '');assert dialog.evaluate('e=>e.lastElementChild.classList.contains("modal-actions")');close.click()
 page.evaluate("""()=>{p.dob=before(270);Object.keys(p.risks).forEach(k=>p.risks[k]='no');const now=new Date().toISOString();p.meals=[['beef',8],['apple',7],['pear',6],['cod',9],['chicken',8],['honey',8],['peas',10],['lentils',12],['turkey',11],['milk',15]].map(([id,days])=>({id:'meal-'+id,date:before(days),time:'12:00',createdAt:now,updatedAt:now,kind:'eaten',foodIds:[id],unknown:false,dish:'',amount:'',texture:'',result:id==='milk'?'pending':'none',note:''}));p.symptoms=[{id:'symptom',date:before(9),time:'13:00',createdAt:now,updatedAt:now,codes:['local'],onset:'soon',mealId:'meal-cod',note:'',photo:null}];p.doctorFoods=[{foodId:'chicken',status:'avoid',note:'Не предлагать'}];render('today');}""")
 assert page.evaluate('foodsToRepeat().map(f=>f.id)')==['lentils','turkey','peas','beef']
 card=page.locator('.repeat-foods');expect(card).to_be_visible();assert card.locator('[data-repeat-food]').count()==4;assert card.locator('[data-repeat-food]:visible').count()==3
 assert 'гарантирующая профилактику аллергии, неизвестна' in card.inner_text()
 for width in [320,390,1440]:
  page.set_viewport_size({'width':width,'height':900});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 card.locator('summary').click();card.locator('[data-record-food=beef]').click();expect(page.locator('[name=foodIds][value=beef]')).to_be_checked();page.locator('[name=result]').select_option('none');page.locator('#meal-form [type=submit]').click();page.wait_for_function('!pendingWrites');page.locator('.nav [data-go=today]').click();assert page.locator('[data-repeat-food=beef]').count()==0
 # Uncompleted observation, a new symptom or individual plan must suppress a reminder.
 page.evaluate("p.meals.find(m=>m.id==='meal-peas').result='pending';render('today')");assert page.locator('[data-repeat-food=peas]').count()==0
 page.evaluate("p.doctorFoods.push({foodId:'turkey',status:'individual',note:'По индивидуальному плану'});render('today')");assert page.locator('[data-repeat-food=turkey]').count()==0
 page.evaluate("profiles.push(PrikormModel.patient('Другой'));active=1;p=profiles[1];render('today')");expect(card).to_have_count(0)
 page.evaluate("active=0;p=profiles[0];render('today')");page.wait_for_function('!pendingWrites');page.evaluate('navigator.serviceWorker.ready');c.set_offline(True);page.reload();page.wait_for_function('!loading');expect(page.locator('[data-repeat-food=lentils]')).to_be_visible();page.locator('[data-action=choking-help]').click();expect(page.locator('#triage-dialog.choking-help')).to_be_visible();close.click()
 assert not errors,errors;c.close()
print('PASS: choking return upper-right/sticky, button/Escape/focus/draft preservation, urgent triage unchanged; >7-day boundary, conditions, oldest-first/collapsed list, recording resets reminder, patient isolation, responsive and offline.')
