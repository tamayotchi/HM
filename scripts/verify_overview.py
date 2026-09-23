"""Browser checks for the tablet monitor. No device service calls; simulations stay in-browser."""
import json
import os
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PREVIEW='--preview' in sys.argv
URL=(os.environ.get('HOMEASSISTANT_URL') or os.environ['PI_MCP_HOMEASSISTANT_URL']).rstrip('/')
TOKEN=os.environ.get('HOMEASSISTANT_TOKEN') or os.environ['PI_MCP_HOMEASSISTANT_TOKEN']
config=json.loads((ROOT/'build/overview-view.json').read_text())['cards'][0]
report={'mode':'preflight' if PREVIEW else 'published','errors':[],'screenshots':[],'physical_device_operations':0}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--disable-dev-shm-usage'])
    context=browser.new_context(viewport={'width':1280,'height':800})
    tokens={'hassUrl':URL,'access_token':TOKEN,'token_type':'Bearer','expires_in':86400,'expires':int(time.time()*1000)+86400000,'clientId':URL+'/'}
    context.add_init_script('localStorage.setItem("hassTokens",'+json.dumps(json.dumps(tokens))+');')
    if PREVIEW:context.add_init_script((ROOT/'dashboard/house-overview-card.js').read_text())
    page=context.new_page()
    page.on('pageerror',lambda e:report['errors'].append(str(e)))
    # The view already exists; override its element implementation locally, not Lit-owned DOM.
    page.goto(URL+'/house-3d/all-floors',wait_until='domcontentloaded')
    card=page.locator('house-overview-card');card.wait_for(state='visible',timeout=45000)
    assert card.evaluate('c=>c._config')==config
    for _ in range(100):
        if card.evaluate('c=>Boolean(c._hass)&&[...c.shadowRoot.querySelectorAll("img")].every(i=>i.complete&&i.naturalWidth>0)'):break
        page.wait_for_timeout(300)
    else:raise AssertionError('Images/HA failed to load')
    assert card.locator('.floor').count()==4
    assert card.locator('.layer').count()==13
    assert card.locator('[data-opening]').count()==2
    for width,height in [(1280,800),(1024,768),(1024,600),(800,600),(1920,1080),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(600)
        metrics=card.evaluate('''c=>{const s=c.shadowRoot.querySelector('.shell'),r=s.getBoundingClientRect();return {top:r.top,bottom:r.bottom,width:r.width,client:s.clientWidth,scroll:s.scrollWidth,columns:getComputedStyle(c.shadowRoot.querySelector('.grid')).gridTemplateColumns,panels:[...c.shadowRoot.querySelectorAll('.floor')].map(e=>{const r=e.getBoundingClientRect(),status=e.querySelector('.status');return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,statusScroll:status.scrollHeight,statusClient:status.clientHeight};})};}''')
        assert metrics['scroll']<=metrics['client']+1,metrics
        if width>height:
            assert metrics['bottom']<=height+1,metrics
            assert len(metrics['columns'].split())==2,metrics
            assert all(x['bottom']<=height for x in metrics['panels']),metrics
            assert card.locator('.status:visible').count()==0,'Status drawers must not consume render space'
        filename=f"overview-{'preflight' if PREVIEW else 'published'}-{width}x{height}.png"
        page.screenshot(path=str(ROOT/'build/previews'/filename),full_page=True)
        report['screenshots'].append({'file':filename,'width':width,'height':height,'metrics':metrics})
    page.set_viewport_size({'width':1280,'height':800});page.wait_for_timeout(300)
    if card.locator('.fullscreen').is_visible():
        card.locator('.fullscreen').click();page.wait_for_timeout(300)
        assert page.evaluate('Boolean(document.fullscreenElement)')
        page.screenshot(path=str(ROOT/'build/previews'/f"overview-{'preflight' if PREVIEW else 'published'}-fullscreen.png"))
        card.locator('.fullscreen').click();page.wait_for_timeout(300)
        assert not page.evaluate('Boolean(document.fullscreenElement)')
        report['fullscreen']=True
    # Zoom uses the same transform for every image layer and can be reset without navigation.
    initial=card.locator('.stage').first.evaluate('e=>e.getBoundingClientRect().width')
    card.locator('[data-zoom="in"]').click()
    assert card.locator('.stage').first.evaluate('e=>e.getBoundingClientRect().width')>initial*1.15
    visual_box=card.locator('.visual').first.bounding_box()
    page.mouse.move(visual_box['x']+20,visual_box['y']+visual_box['height']/2)
    page.mouse.down();page.mouse.move(visual_box['x']+20,visual_box['y']+visual_box['height']/2+30,steps=5);page.mouse.up()
    assert card.evaluate('c=>c._tiles[0].pan.y')>0
    assert page.url.endswith('/house-3d/all-floors'),'Dragging navigated away'
    card.locator('[data-zoom="fit"]').click()
    assert abs(card.locator('.stage').first.evaluate('e=>e.getBoundingClientRect().width')-initial)<1
    assert card.evaluate('c=>c._tiles[0].pan')=={'x':0,'y':0}
    report['zoom_reset']=True
    # Freeze HA inputs; all remaining state changes are local and service calls are trapped.
    card.evaluate('''c=>{c.__real=c.hass;Object.defineProperty(c,'hass',{configurable:true,get:()=>c._hass,set:()=>{}});c.__calls=[];c.__details=[];c.addEventListener('hass-more-info',e=>{e.stopPropagation();c.__details.push(e.detail.entityId);});c._hass={...c.__real,connected:true,states:structuredClone(c.__real.states),callService:(...a)=>{c.__calls.push(a);throw Error('Overview must not call services');}};}''')
    bindings=card.evaluate('c=>c._config.floors.flatMap(f=>f.lights.map(l=>l.entity))')
    for entity in bindings:
        card.evaluate('''(c,entity)=>{for(const f of c._config.floors)for(const l of f.lights)c._hass.states[l.entity]={state:l.entity===entity?'on':'off',last_changed:new Date().toISOString()};c._update();}''',entity)
        assert card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].map(e=>e.style.opacity)')==['1' if e==entity else '0' for e in bindings]
        assert card.locator('.global').inner_text().startswith('1 / 13 lights on')
    for floor in range(3):
        card.locator(f'[data-floor="{floor}"] .status-toggle').click()
        for j in range(card.locator(f'[data-floor="{floor}"] [data-light]').count()):
            card.locator(f'[data-floor="{floor}"] [data-light="{j}"]').click()
            assert card.evaluate('c=>c.__details.at(-1)')==config['floors'][floor]['lights'][j]['entity']
    for index,opening in enumerate(config['floors'][0]['openings']):
        entity=opening['entity']
        for raw,expected in [('on','open'),('off','closed'),('unknown','unavailable'),('unavailable','unavailable'),(None,'unavailable')]:
            card.evaluate('''(c,a)=>{if(a.raw===null)delete c._hass.states[a.entity];else c._hass.states[a.entity]={state:a.raw};c._update();}''',{'entity':entity,'raw':raw})
            assert card.locator(f'[data-opening="{index}"]').get_attribute('data-state')==expected
        card.evaluate('(c,e)=>{c._hass.states[e]={state:"on"};c._update();}',entity)
        card.locator(f'[data-opening="{index}"]').click()
        assert card.evaluate('c=>c.__details.at(-1)')==entity
    for bad in ['unknown','unavailable',None]:
        card.evaluate('''(c,bad)=>{for(const f of c._config.floors)for(const l of f.lights){if(bad===null)delete c._hass.states[l.entity];else c._hass.states[l.entity]={state:bad};}c._update();}''',bad)
        assert card.locator('[data-light][data-state="unavailable"]').count()==13
        assert card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].every(e=>e.style.opacity==="0")')
    card.evaluate('''c=>{for(const f of c._config.floors)for(const l of f.lights)c._hass.states[l.entity]={state:'on',last_changed:new Date().toISOString()};c._hass.connected=false;c._update();}''')
    assert card.locator('.global').inner_text()=='Disconnected · states unavailable'
    assert card.locator('.device[data-state="unavailable"]').count()==15
    assert card.locator('[data-floor="3"] .floor-count').inner_text()=='Model only'
    assert card.locator('[data-floor="3"] .device').count()==0
    card.evaluate("c=>{c._hass.connected=true;c._update();c.shadowRoot.querySelector('.latest').textContent='SIMULATED ALL-ON · not actual device states';}")
    assert card.locator('.global').inner_text().startswith('13 / 13 lights on')
    page.wait_for_timeout(400)
    page.screenshot(path=str(ROOT/'build/previews'/f"overview-{'preflight' if PREVIEW else 'published'}-simulated-all-on.png"),full_page=True)
    assert card.evaluate('c=>c.__calls')==[]
    report.update(simulated_independent_layers=13,contacts_read_only=True,invalid_and_disconnected_states=True,model_only_fourth=True)
    # Navigation uses the existing floor paths and does not invoke device services.
    card.locator('[data-floor="2"] .floor-link').click()
    page.wait_for_url('**/house-3d/third-floor')
    page.locator('house-floorplan-card').wait_for(state='visible',timeout=30000)
    report['floor_navigation']=True
    browser.close()
assert not report['errors'],report['errors']
report['success']=True
(ROOT/'build/reports'/('overview-preflight.json' if PREVIEW else 'overview-verification.json')).write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='screenshots'},indent=2))
