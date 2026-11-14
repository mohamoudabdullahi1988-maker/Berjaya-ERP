"""Isolated browser tests. Synthetic responses are used only by this test."""
from playwright.sync_api import sync_playwright, expect
import json
from pathlib import Path
Path('/tmp/berjaya-dashboard-checks').mkdir(exist_ok=True)
keys=['sales_value','cash_collected','overdue_balance','due_next_30_days','overdue_milestones','available_units']
fixture={'summary':{},'schedule':{'available':True,'buckets':[{'label':'Next 30 days','amount':2000}]},'jobs':{'available':True,'open':4,'completed':2},'payments':{'available':True,'received':1000,'collection_rate':50},'scope':{'company_id':'Synthetic','company_name':'Synthetic Company'},'companies':[{'id':'Synthetic','name':'Synthetic Company'}],'currency':'USD','as_of':'2026-11-14T12:00:00+03:00','executive':{'available':True,'metrics':{key:{'available':True,'value':1000+index,'detail':'Synthetic saved records'} for index,key in enumerate(keys)},'trends':{'available':True,'period_label':'Six months; current month to date','months':[{'label':label,'sales_value':amount,'received':amount/2} for label,amount in [('Jun',1000),('Jul',2000),('Aug',1500),('Sep',3000),('Oct',2200),('Nov',2400)]]},'exposure':{'available':True,'items':[{'label':'Active reservations past expiry','available':True,'value':3,'kind':'count','detail':'Recorded exceptions'}]},'decisions':{'available':True,'items':[]}}}
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in [1440,390]:
  page=browser.new_page(viewport={'width':width,'height':1000})
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script('window.berjaya_boot='+json.dumps({'product_name':'Berjaya','user':{'name':'Synthetic','full_name':'Synthetic Reviewer'},'company':'Synthetic','currencies':{'Synthetic':'USD'},'nav':[{'key':'dashboard','label':'Dashboard'}]}))
  page.route('**/api/**',lambda route:route.fulfill(json={'message':fixture}))
  page.goto('http://127.0.0.1:8080/berjaya/dashboard')
  expect(page.get_by_role('heading',name='Scheduled amounts by due window')).to_be_visible()
  expect(page.get_by_role('heading',name='Operations at a glance')).to_be_visible()
  expect(page.locator('.chart')).to_have_count(2)
  page.get_by_label('Period',exact=True).select_option('last_90_days')
  expect(page.get_by_role('heading',name='Operations at a glance')).to_be_visible()
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
  assert not errors,errors
  page.screenshot(path=f'/tmp/berjaya-dashboard-checks/dashboard-{width}.png',full_page=True)
  page.unroute('**/api/**')
  restricted={**fixture,'executive':{'available':False,'reason':'Management reporting access required'}}
  page.route('**/api/**',lambda route:route.fulfill(json={'message':restricted}))
  page.get_by_role('button',name='Refresh',exact=True).click()
  expect(page.get_by_text('Management reporting unavailable to this role.')).to_be_visible()
  expect(page.locator('.chart-card').nth(1).get_by_text('Unavailable',exact=True)).to_be_visible()
  page.unroute('**/api/**')
  page.route('**/api/**',lambda route:route.fulfill(status=500,json={'exception':'Error: Dashboard unavailable'}))
  page.get_by_role('button',name='Refresh',exact=True).click()
  expect(page.get_by_text('The dashboard could not be loaded')).to_be_visible()
  expect(page.locator('.chart-card')).to_have_count(0)
  print(f'PASS {width}px: cards, charts, filter, restriction, error and overflow checks')
  page.close()
 browser.close()
