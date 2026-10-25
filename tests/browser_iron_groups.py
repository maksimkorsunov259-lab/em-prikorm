"""Iron categories collapse initially and search/filter preserve product access."""
import os
from playwright.sync_api import sync_playwright,expect
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);p=b.new_page(viewport={'width':390,'height':844});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
 p.goto(os.environ.get('APP_URL','http://127.0.0.1:8056/em-prikorm/'));p.wait_for_function('!loading&&!pendingWrites');p.evaluate("render('foods')");p.locator('[data-filter=iron]').click()
 expected=p.evaluate('availableFoods.filter(f=>f.iron).map(f=>f.id).sort()')
 assert p.locator('#food-list [data-food]').evaluate_all('(els)=>els.map(e=>e.dataset.food).sort()')==expected
 assert p.locator('.iron-category').count()==7;assert p.locator('.iron-category[open]').count()==0
 expect(p.locator('[data-food=beef]')).to_be_hidden();p.locator('[data-iron-group=Мясо] summary').click();p.locator('[data-food=beef]').click();expect(p.locator('#screen h1')).to_have_text('Говядина')
 p.locator('#screen [data-back]').first.click();assert p.locator('.iron-category[open]').count()==0
 p.locator('#food-search').fill('шпинат');expect(p.locator('[data-food=spinach]')).to_be_visible();assert p.locator('.iron-category').count()==1
 p.locator('#food-search').fill('');assert p.locator('.iron-category[open]').count()==0
 p.locator('#food-group').select_option(label='Рыба');assert p.locator('.iron-category').count()==1;expect(p.locator('[data-food=cod]')).to_be_hidden();p.locator('.iron-category summary').click();expect(p.locator('[data-food=cod]')).to_be_visible()
 p.locator('#food-group').select_option('all');p.locator('[data-filter=all]').click();assert p.locator('.iron-category').count()==0;expect(p.locator('[data-food=apple]')).to_be_visible()
 for width in [320,390,1440]:
  p.set_viewport_size({'width':width,'height':900});p.locator('[data-filter=iron]').click();p.locator('[data-iron-group="Крупы, хлеб и клубнеплоды"] summary').click();assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
 assert not errors,errors;b.close()
print('PASS: collapsed iron groups, product identities, search, category filter, product/back navigation and mobile/desktop widths.')
