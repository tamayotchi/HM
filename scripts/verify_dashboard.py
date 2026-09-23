"""Verify all configured views, responsive layouts, and every light-layer binding.
--preview injects local cards/images into the browser only, before publication.
UI simulations below never change HA state. Optional --live tests briefly toggle
one circuit per floor via the actual dashboard and restore its previous state.
Add --floor-2-only with --live to leave first-floor devices untouched.
"""
import os, json, time, sys, hashlib
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
from mcp_client import HomeAssistantMCP
from dashboard_config import build_dashboard,VIEW_PATHS
from project_paths import ROOT, CONFIG, DASHBOARD, IMAGES, PREPARED, PREVIEWS, REPORTS, load_config, ensure_output_dirs
ensure_output_dirs()
URL=os.environ['PI_MCP_HOMEASSISTANT_URL'].rstrip('/')
TOKEN=os.environ['PI_MCP_HOMEASSISTANT_TOKEN']
api=requests.Session();api.headers['Authorization']='Bearer '+TOKEN
PREVIEW='--preview' in sys.argv
assert not (PREVIEW and '--live' in sys.argv),'Preflight must never actuate hardware'
source=load_config()
prefix='preflight-' if PREVIEW else ''
desired=build_dashboard(json.loads(PREPARED.read_text()),source,lambda name:'/__floorplan_preview__/'+name) if PREVIEW else None
report={'mode':'local preflight' if PREVIEW else 'deployed','screenshots':[],'simulated_circuits':[],'live_roundtrips':[],'browser_errors':[],'all_off':[],
        'inputs':{key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in [('source_sha256',CONFIG),('prepared_sha256',PREPARED),('runtime_sha256',DASHBOARD/'house-floorplan-card.js')]}}

def screenshot(page,name):
    if 'simulated' in name:
        page.locator('house-floorplan-card').evaluate('c=>{c.shadowRoot.querySelector("h1").textContent=c._config.title+" · SIMULATED";}')
    page.screenshot(path=str(PREVIEWS/(prefix+name)),full_page=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--disable-dev-shm-usage'])
    context=browser.new_context(viewport={'width':1440,'height':1050})
    tokens={'hassUrl':URL,'access_token':TOKEN,'token_type':'Bearer','expires_in':86400,'expires':int(time.time()*1000)+86400000,'clientId':URL+'/'}
    context.add_init_script('localStorage.setItem("hassTokens",'+json.dumps(json.dumps(tokens))+');')
    if PREVIEW:
        # Register the local runtime before HA loads its inline module. This is browser-only.
        context.add_init_script((DASHBOARD/'house-floorplan-card.js').read_text())
        context.route(URL+'/__floorplan_preview__/*',lambda route:route.fulfill(path=str(IMAGES/route.request.url.rsplit('/',1)[-1]),content_type='image/png'))
    page=context.new_page();page.on('pageerror',lambda error:report['browser_errors'].append(str(error)))
    for floor in source['floors']:
        num=floor['floor'];path=VIEW_PATHS[num]
        page.goto(URL+'/house-3d/'+('first-floor' if PREVIEW else path),wait_until='domcontentloaded')
        card=page.locator('house-floorplan-card');card.wait_for(state='visible',timeout=45000)
        if PREVIEW:
            config=next(v['cards'][0] for v in desired['views'] if v['path']==path)
            card.evaluate('(c,config)=>c.setConfig(config)',config)
        card.locator('.base').wait_for(state='visible')
        page.wait_for_function("""() => {
          const search=root=>{for(const e of root.querySelectorAll('*')){if(e.tagName==='HOUSE-FLOORPLAN-CARD')return e;if(e.shadowRoot){const c=search(e.shadowRoot);if(c)return c;}}};
          const c=search(document);return c && c._hass && [...c.shadowRoot.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0);
        }""",timeout=45000)
        page.wait_for_timeout(800)
        attribution=card.locator('.footer span').first.text_content()
        expected_source='SketchUp + references → Blender' if num==1 else 'Reference plan → Blender'
        assert attribution==f'{expected_source} · Floor {num} / 4',attribution
        alt=card.locator('.base').get_attribute('alt')
        assert ('SketchUp' in alt) if num==1 else ('stairs top-right' in alt and 'SketchUp' not in alt),alt
        report.setdefault('source_attribution',[]).append({'floor':num,'text':attribution,'correct':True})
        bound=card.evaluate('c=>c._config.lights.map(l=>l.entity)')
        assert bound==[l['entity'] for l in floor['lights']],(num,bound)
        report.setdefault('observed_states',[]).append({'floor':num,'entities':card.evaluate('c=>c._config.lights.map(l=>({entity:l.entity,state:c._hass.states[l.entity]?.state||"missing"}))')})
        if num==1:
            assert len(bound)==2 and bound[0]=='light.first_floor_front_door_light'
            assert card.evaluate('c=>c._config.lights[0].name')=='Car & front door'
            assert card.evaluate('c=>c._config.lights[0].room')=='Garage & entrance'
        if num==3:
            assert len(bound)==5
            names=card.evaluate('c=>c._config.lights.map(l=>l.name)')
            assert bound[1:3]==['switch.juan_room_light_1','switch.juan_room_light_2']
            assert names[1:3]==['Light 1 · neutral','Light 2 · warm']
            assert bound[3:]==['switch.third_floor_corridor_light_1','switch.third_floor_corridor_light_2']
            assert names[3:]==['Light 1 · balcony','Light 2 · corridor']
            assert card.evaluate('c=>c._config.lights.slice(3).map(l=>l.room)')==['Balcony','Corridor']
        for label,w,h in [('desktop',1440,1050),('tablet',1024,768),('tablet-short',1024,600),('phone',390,844),('phone-small',320,740)]:
            page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(400)
            filename=f'floor-{num}-{label}-live.png'
            screenshot(page,filename)
            dims=card.evaluate('(c)=>({width:c.getBoundingClientRect().width,scroll:c.shadowRoot.querySelector(".shell").scrollWidth,client:c.shadowRoot.querySelector(".shell").clientWidth})')
            assert dims['scroll']<=dims['client']+2,(label,dims)
            overlaps=card.evaluate('''c=>{
              const selector=c._config.model_only?'.room-label':'.marker,.opening-marker';
              const pins=[...c.shadowRoot.querySelectorAll(selector)].map(e=>({id:e.dataset.light!==undefined?'light:'+e.dataset.light:e.dataset.opening!==undefined?'opening:'+e.dataset.opening:e.textContent,r:e.getBoundingClientRect()})).filter(e=>e.r.width&&e.r.height),pairs=[];
              for(let i=0;i<pins.length;i++)for(let j=i+1;j<pins.length;j++){
                const a=pins[i].r,b=pins[j].r;
                if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)pairs.push([pins[i].id,pins[j].id]);
              }return pairs;
            }''')
            assert not overlaps,(num,label,'Overlapping touch targets / model labels',overlaps)
            report['screenshots'].append({'floor':num,'device':label,'width':w,'height':h,'file':prefix+filename,'no_horizontal_overflow':True,'hotspots_non_overlapping':True})
        page.set_viewport_size({'width':1440,'height':1050});page.wait_for_timeout(300)
        assert card.locator('.visual .marker').count()==len(floor['lights'])
        assert card.locator('.drawer:visible').count()==0
        base_size=card.locator('.stage').evaluate('e=>e.getBoundingClientRect().width')
        card.locator('[data-action="in"]').click()
        assert card.locator('.stage').evaluate('e=>e.getBoundingClientRect().width')>base_size*1.15
        canvas_box=card.locator('.canvas').bounding_box()
        page.mouse.move(canvas_box['x']+10,canvas_box['y']+canvas_box['height']/2)
        page.mouse.down();page.mouse.move(canvas_box['x']+10,canvas_box['y']+canvas_box['height']/2+35,steps=5);page.mouse.up()
        assert card.evaluate('c=>c._pan.y')>0,'Zoomed render did not pan'
        card.locator('[data-action="fit"]').click()
        assert abs(card.locator('.stage').evaluate('e=>e.getBoundingClientRect().width')-base_size)<1
        assert card.evaluate('c=>c._pan')=={'x':0,'y':0}
        if card.locator('[data-action="fullscreen"]').is_visible():
            card.locator('[data-action="fullscreen"]').click();page.wait_for_timeout(300)
            assert page.evaluate('Boolean(document.fullscreenElement)')
            screenshot(page,f'floor-{num}-fullscreen-live.png')
            card.locator('[data-action="fullscreen"]').click();page.wait_for_timeout(300)
            assert not page.evaluate('Boolean(document.fullscreenElement)')
        report.setdefault('render_layout',[]).append({'floor':num,'in_render_controls':True,'zoom_reset':True,'fullscreen':True,'sidebar_removed':True})
        if floor.get('model_only'):
            assert not bound and not floor.get('openings')
            assert card.locator('.marker,.layer,.circuit,.opening-marker,.opening-row,.off-all,.summary,.legend').count()==0
            assert card.locator('.top .connection').inner_text()=='Model only'
            assert 'No connected devices' in card.locator('.footer').text_content()
            card.locator('[data-action="labels"]').click()
            assert card.locator('.stage').evaluate('e=>e.classList.contains("labels-hidden")')
            card.locator('[data-action="labels"]').click()
            calls=card.evaluate('''async c=>{const original=c._hass,calls=[];c._hass={connected:false,states:{},callService:async(...args)=>calls.push(args)};c._update();await c._allOff();await c._toggle(0);c._hass=original;c._update();return calls;}''')
            assert calls==[], 'Model-only card attempted a device service'
            assert card.locator('.top .connection').inner_text()=='Model only'
            report.setdefault('model_only_floors',[]).append({'floor':num,'no_entity_bindings':True,'no_device_controls':True,'no_service_calls':True,'labels_toggle':True})
            continue
        # Freeze this one card's setter during frontend simulations. No state API writes.
        entities=card.evaluate("""c=>{
          c.__realHass=c._hass;c.__calls=[];
          Object.defineProperty(c,'hass',{configurable:true,get:()=>c._hass,set:()=>{}});
          const states={...c._hass.states};
          for(const l of c._config.lights)states[l.entity]={...states[l.entity],state:'off'};
          c._hass={...c.__realHass,states,callService:async(...args)=>{c.__calls.push(args);}};c._update();
          return c._config.lights.map(l=>l.entity);
        }""")
        for i,entity in enumerate(entities):
            card.evaluate("""(c,i)=>{for(const [j,l] of c._config.lights.entries())c._hass.states[l.entity]={...c._hass.states[l.entity],state:i===j?'on':'off'};c._update();}""",i)
            opacity=card.evaluate('(c)=>[...c.shadowRoot.querySelectorAll(".layer")].map(x=>x.style.opacity)')
            assert opacity==['1' if j==i else '0' for j in range(len(entities))],opacity
            assert card.locator('.on-count').inner_text()=='1'
            card.locator('[data-action="controls"]').click()
            card.locator(f'.circuit[data-light="{i}"]').click()
            last=card.evaluate('c=>c.__calls[c.__calls.length-1]')
            assert last==[entity.split('.')[0],'toggle',{'entity_id':entity}],last
            card.locator('[data-action="close-controls"]').click()
            card.locator(f'.marker[data-light="{i}"]').click()
            assert card.evaluate('c=>c.__calls[c.__calls.length-1]')==last
            report['simulated_circuits'].append({'floor':num,'entity':entity,'independent_overlay':True,'button_service_binding':True,'hotspot_service_binding':True})
        if num==1:
            card.evaluate('''c=>{for(const [i,l] of c._config.lights.entries())c._hass.states[l.entity]={...c._hass.states[l.entity],state:i===0?'on':'off'};c._update();c.shadowRoot.querySelector('.footer').firstElementChild.textContent='SIMULATED CAR / FRONT-DOOR LIGHT · not actual device states';}''')
            assert card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].map(l=>l.style.opacity)')==['1','0']
            page.wait_for_timeout(400);screenshot(page,'floor-1-car-door-only-simulated.png')
            report['first_floor_shared_light']={'entity':bound[0],'covers_car_and_front_door':True,'single_control':True,'independent_from_mini_kitchen':True}
        if num==3:
            for label,indices in [('neutral',[1]),('warm',[2]),('combined',[1,2])]:
                card.evaluate('''(c,indices)=>{for(const [i,l] of c._config.lights.entries())c._hass.states[l.entity]={...c._hass.states[l.entity],state:indices.includes(i)?'on':'off'};c._update();c.shadowRoot.querySelector('.footer').firstElementChild.textContent='SIMULATED JUAN LIGHTING · not actual device states';}''',indices)
                assert card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].map(l=>l.style.opacity)')==['1' if i in indices else '0' for i in range(5)]
                assert card.locator('.on-count').inner_text()==str(len(indices))
                page.wait_for_timeout(400);screenshot(page,f'floor-3-juan-{label}-simulated.png')
            report['juan_colour_controls']={'neutral':'switch.juan_room_light_1','warm':'switch.juan_room_light_2','separate_and_combined_overlays':True,'on_off_only':True}
            for label,index in [('balcony',3),('corridor',4)]:
                card.evaluate('''(c,index)=>{for(const [i,l] of c._config.lights.entries())c._hass.states[l.entity]={...c._hass.states[l.entity],state:i===index?'on':'off'};c._update();c.shadowRoot.querySelector('.footer').firstElementChild.textContent='SIMULATED SINGLE-CIRCUIT PREVIEW · not actual device states';}''',index)
                assert card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].map(l=>l.style.opacity)')==['1' if i==index else '0' for i in range(5)]
                page.wait_for_timeout(400);screenshot(page,f'floor-3-{label}-only-simulated.png')
            report['balcony_corridor_mapping']={'balcony':'switch.third_floor_corridor_light_1','corridor':'switch.third_floor_corridor_light_2','independent_overlays':True}
        # Opening contacts are read-only: binary states update badges, never services.
        opening_entities=card.evaluate("c=>(c._config.openings||[]).map(o=>o.entity)")
        card.evaluate("""c=>{c.__details=[];c.__openingListener=e=>{c.__details.push(e.detail.entityId);e.stopPropagation();};c.addEventListener('hass-more-info',c.__openingListener);}""")
        for i,entity in enumerate(opening_entities):
            before_calls=card.evaluate('c=>c.__calls.length')
            baseline=card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].map(e=>e.style.opacity)')
            for raw,expected,label in [('on','open','Open'),('off','closed','Closed'),('unavailable','unavailable','Unavailable'),('unknown','unavailable','Unavailable')]:
                card.evaluate("""(c,arg)=>{c._hass.states[arg.entity]={...c._hass.states[arg.entity],state:arg.raw};c._update();}""",{'entity':entity,'raw':raw})
                assert card.locator(f'.opening-marker[data-opening="{i}"]').get_attribute('data-state')==expected
                assert card.locator(f'.opening-row[data-opening="{i}"] .state').inner_text()==label
                assert card.evaluate('c=>[...c.shadowRoot.querySelectorAll(".layer")].map(e=>e.style.opacity)')==baseline
            for selector in ['.opening-row','.opening-marker']:
                if selector=='.opening-row':card.locator('[data-action="controls"]').click()
                else:card.locator('[data-action="close-controls"]').click()
                card.locator(f'{selector}[data-opening="{i}"]').click()
                assert card.evaluate('c=>c.__details[c.__details.length-1]')==entity
            assert card.evaluate('c=>c.__calls.length')==before_calls,'Opening indicator invoked a service!'
            card.evaluate('(c,e)=>{delete c._hass.states[e];c._update();}',entity)
            assert card.locator(f'.opening-row[data-opening="{i}"] .state').inner_text()=='Unavailable'
            assert card.locator(f'.opening-marker[data-opening="{i}"]').is_disabled()
            card.evaluate('(c,e)=>{c._hass.states[e]={...c.__realHass.states[e]};c._update();}',entity)
            report.setdefault('opening_sensors',[]).append({'floor':num,'entity':entity,'open_closed_unknown_unavailable_missing':True,'status_only_no_service_calls':True})
        if opening_entities:
            card.evaluate("""c=>{for(const o of c._config.openings)c._hass.states[o.entity]={...c._hass.states[o.entity],state:'on'};c._update();c.shadowRoot.querySelector('.footer').firstElementChild.textContent='SIMULATED DOOR-OPEN PREVIEW · not actual sensor states';}""")
            screenshot(page,f'floor-{num}-doors-open-simulated.png')
            card.evaluate("""c=>{for(const o of c._config.openings)c._hass.states[o.entity]={...c.__realHass.states[o.entity]};c._update();}""")
        card.evaluate("c=>{c.removeEventListener('hass-more-info',c.__openingListener);delete c.__openingListener;delete c.__details;}")
        # Unknown and unavailable must never be presented as a known off state.
        for bad_state in ['unavailable','unknown',None]:
            card.evaluate('''(c,state)=>{for(const l of c._config.lights){if(state===null)delete c._hass.states[l.entity];else c._hass.states[l.entity]={...c._hass.states[l.entity],state};}c._update();}''',bad_state)
            assert card.locator('.circuit:disabled').count()==len(entities)
            assert card.locator('.off-all').is_disabled()
            assert all(x=='0' for x in card.evaluate('(c)=>[...c.shadowRoot.querySelectorAll(".layer")].map(x=>x.style.opacity)'))
        card.evaluate('''c=>{for(const l of c._config.lights)c._hass.states[l.entity]={...c.__realHass.states[l.entity],state:'on'};c._hass.connected=false;c._update();}''')
        assert card.locator('.circuit:disabled').count()==len(entities)
        assert card.locator('.off-all').is_disabled()
        assert card.locator('.top .connection').inner_text()=='Disconnected'
        for i in range(len(opening_entities)):
            assert card.locator(f'.opening-row[data-opening="{i}"] .state').inner_text()=='Unavailable'
        card.evaluate('c=>{c._hass.connected=true;c._update();}')
        report.setdefault('invalid_state_handling',[]).append({'floor':num,'unknown_unavailable_missing_disconnected':True})
        card.evaluate("""c=>{for(const l of c._config.lights)c._hass.states[l.entity]={...c._hass.states[l.entity],state:'on'};c._update();const footer=c.shadowRoot.querySelector('.footer');footer.firstElementChild.textContent='SIMULATED ALL-ON PREVIEW · not actual device states';}""")
        page.wait_for_timeout(500)
        screenshot(page,f'floor-{num}-desktop-all-on-simulated.png')
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400)
        screenshot(page,f'floor-{num}-phone-all-on-simulated.png')
        # All off may target only explicitly configured on circuits, never groups or other floors.
        before=card.evaluate('c=>c.__calls.length');card.locator('.off-all').click();page.wait_for_timeout(100)
        calls=card.evaluate('(c,start)=>c.__calls.slice(start)',before)
        target_ids=[eid for call in calls for eid in call[2]['entity_id']]
        assert sorted(target_ids)==sorted(entities)
        assert all(call[1]=='turn_off' for call in calls)
        report['all_off'].append({'floor':num,'targets':target_ids,'excludes_contacts_and_other_floors':True})
        card.evaluate('c=>{delete c.hass;c.hass=c.__realHass;delete c.__realHass;delete c.__calls;c._render();c._update();}')
        if '--live' in sys.argv and ('--floor-2-only' not in sys.argv or num==2):
            page.set_viewport_size({'width':1440,'height':1050})
            entity=entities[0]
            initial=api.get(URL+'/api/states/'+entity,timeout=20).json()
            if initial['state'] not in ('on','off'):raise RuntimeError('Cannot safely test unavailable '+entity)
            expected='off' if initial['state']=='on' else 'on'
            try:
                card.locator('[data-action="controls"]').click()
                card.locator('.circuit[data-light="0"]').click()
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    state=api.get(URL+'/api/states/'+entity,timeout=10).json()
                    if state['state']==expected:break
                    time.sleep(.4)
                else:raise AssertionError('Dashboard click did not change '+entity)
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    opacity=card.locator('[data-layer="0"]').evaluate('(e)=>e.style.opacity')
                    if opacity==('1' if expected=='on' else '0'):break
                    time.sleep(.2)
                else:raise AssertionError('Live state did not update layer')
                page.wait_for_timeout(450)
                page.screenshot(path=str(PREVIEWS/f'floor-{num}-live-switch-verification.png'),full_page=True)
                report['live_roundtrips'].append({'floor':num,'entity':entity,'before':initial['state'],'observed':expected,'overlay_updated':True,'restored':False})
            finally:
                mcp=HomeAssistantMCP()
                mcp.call('ha_call_service',{'domain':entity.split('.')[0],'service':'turn_on' if initial['state']=='on' else 'turn_off','entity_id':entity,'wait':True})
                current=api.get(URL+'/api/states/'+entity,timeout=15).json()
                assert current['state']==initial['state'],'Restoration failed!'
                if report['live_roundtrips']:report['live_roundtrips'][-1]['restored']=True
    browser.close()
assert not report['browser_errors'],report['browser_errors']
assert len(report['simulated_circuits'])==sum(len(f['lights']) for f in source['floors'])
report['success']=True
(REPORTS/('verification-preflight.json' if PREVIEW else 'verification-report.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
