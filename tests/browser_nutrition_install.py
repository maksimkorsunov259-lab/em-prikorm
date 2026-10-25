"""Nutrition guidance, clinician restrictions and Android installation fallbacks."""
import os,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
URL=os.environ.get('APP_URL','http://127.0.0.1:8040/em-prikorm/')
with sync_playwright() as pw,tempfile.TemporaryDirectory() as tmp:
 c=pw.chromium.launch_persistent_context(tmp,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],viewport={'width':393,'height':851},is_mobile=True,has_touch=True,device_scale_factor=2.75,user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36')
 p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(URL);p.wait_for_function('!loading&&!pendingWrites&&offlineReady')
 p.evaluate("catalogFilter='iron';render('foods')");assert p.locator('.food-row').count()==66;assert p.locator('[data-food=turkey]').count()==1;assert p.locator('[data-food=spinach]').count()==1;assert p.locator('[data-food=cod]').count()==1
 p.locator('[data-iron-group=Овощи] summary').click();p.locator('[data-food=spinach]').click();assert 'ограниченной усвояемостью' in p.locator('#screen').inner_text()
 p.evaluate("render('observation')");p.get_by_text('Поддержание употребления продуктов в рационе',exact=True).click();text=p.locator('#screen').inner_text();assert 'не реже одного раза в неделю' in text and 'гарантирующая профилактику аллергии, неизвестна' in text
 # Reminders never recommend repeating a product restricted by an individual plan.
 p.evaluate("p.dob=before(240);Object.keys(p.risks).forEach(k=>p.risks[k]='no');p.meals=[{id:crypto.randomUUID(),date:before(8),time:'12:00',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),kind:'eaten',foodIds:['peanut'],unknown:false,dish:'',amount:'',texture:'',result:'none',note:''}];render('today')")
 assert p.evaluate("reminderAllowed('peanut')");p.evaluate("p.doctorFoods=[{foodId:'peanut',status:'individual',note:'По индивидуальному плану'}]");assert not p.evaluate("reminderAllowed('peanut')")
 p.evaluate("p.doctorFoods=[];p.risks.eggAllergy='yes'");assert not p.evaluate("reminderAllowed('peanut')")
 p.evaluate("p.risks.eggAllergy='no';p.meals[0].result='pending'");assert not p.evaluate("reminderAllowed('peanut')")
 # The native installer can fail even when the manifest passes. Do not claim success.
 p.evaluate("installPrompt={prompt:async()=>{throw new Error('Native install failed')},userChoice:Promise.resolve({outcome:'accepted'})};render('settings')")
 p.locator('[data-runtime=install]').click();p.wait_for_function('!installBusy');assert 'не смог запустить установку' in p.locator('#install-status').inner_text();assert 'Не удаляйте данные сайта' in p.locator('#install-status').inner_text()
 p.evaluate("installPrompt={prompt:async()=>{},userChoice:Promise.resolve({outcome:'dismissed'})};refreshInstallUI()");p.locator('[data-runtime=install]').click();p.wait_for_function('!installBusy');assert 'отменена' in p.locator('#install-status').inner_text()
 p.evaluate("installPrompt={prompt:async()=>{},userChoice:Promise.resolve({outcome:'accepted'})};refreshInstallUI()");p.locator('[data-runtime=install]').click();p.wait_for_function('!installBusy');assert 'Запрос передан Chrome' in p.locator('#install-status').inner_text();assert 'сообщил об установке' not in p.locator('#install-status').inner_text()
 p.evaluate("window.dispatchEvent(new Event('appinstalled'))");assert 'сообщил об установке' in p.locator('#install-status').inner_text();assert p.locator('[data-runtime=install]').is_hidden()
 session=c.new_cdp_session(p);result=session.send('Page.getInstallabilityErrors');assert not result.get('installabilityErrors'),result
 assert not p.evaluate('document.documentElement.scrollWidth>innerWidth');assert not errors,errors;c.close()
print('PASS: 66 practical iron options with main/additional roles and portion notes, weekly guidance with uncertainty, doctor/high-risk/observation reminder suppression, Android-sized viewport and Chromium installability, native installer error/cancel/request/success distinctions.')
