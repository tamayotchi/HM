/* Local, dependency-free Home Assistant floorplan. Assets are hosted by HA. */
class HouseFloorplanCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode: 'open'}); this._pending = new Set(); }
  setConfig(config) {
    if (!config.image || !Array.isArray(config.lights)) throw new Error('Floorplan requires image and lights.');
    if (config.model_only && (config.lights.length || config.openings?.length)) throw new Error('Model-only floorplans cannot bind devices.');
    this._config = structuredClone(config);
    this._render();
    if (this._hass) this._update();
  }
  set hass(value) { this._hass = value; if (this._config) this._update(); }
  get hass() { return this._hass; }
  getCardSize() { return 10; }
  static getStubConfig() { return {title: 'House', image: '', lights: []}; }
  _escape(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  _render() {
    const c=this._config, e=s=>this._escape(s), rooms=[...new Set(c.lights.map(l=>l.room))], openings=c.openings||[];
    const modelOnly=!c.lights.length && !openings.length;
    const bulb='<ha-icon icon="mdi:lightbulb-outline"></ha-icon>';
    this.shadowRoot.innerHTML=`
      <style>
      :host { display:block; color:#e7edf8; --fp-muted:#91a1ba; --fp-line:rgba(165,191,226,.13); font-family:var(--primary-font-family,system-ui,sans-serif); }
      * { box-sizing:border-box; } button { font:inherit; cursor:pointer; -webkit-tap-highlight-color:transparent; }
      button:focus-visible { outline:3px solid #83bdff; outline-offset:3px; } button:disabled { cursor:default; }
      ha-icon { --mdc-icon-size:21px; width:21px; height:21px; }
      .shell { max-width:1480px; margin:0 auto; padding:30px; background:#0c1423; border:1px solid var(--fp-line); border-radius:22px; }
      .top { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:24px; }
      .eyebrow { font-size:10px; letter-spacing:.22em; font-weight:700; color:#7eaddc; margin-bottom:8px; }
      h1 { font-size:clamp(24px,3vw,36px); letter-spacing:-.045em; font-weight:600; margin:0; }
      .subtitle { margin:8px 0 0; font-size:13px; color:var(--fp-muted); line-height:1.5; }
      .connection { display:flex; align-items:center; gap:8px; color:#95d9c4; font-size:11px; background:#102c2d; border:1px solid #20453f; border-radius:30px; padding:9px 13px; white-space:nowrap; }
      .connection::before { content:''; width:6px; height:6px; border-radius:50%; background:#76dfb5; box-shadow:0 0 9px #76dfb555; }
      .connection.offline { color:#d9a780; background:#38291e; border-color:#62432d; }
      .connection.offline::before { background:#d9a780; box-shadow:none; }
      .layout { display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:24px; align-items:start; }
      .visual { min-width:0; background:radial-gradient(ellipse at 48% 45%,#1c2b42 0%,#131e30 58%,#101929 100%); border:1px solid var(--fp-line); border-radius:18px; overflow:hidden; }
      .visual-head { display:flex; justify-content:space-between; align-items:center; padding:16px 18px 0; color:#93a8c5; font-size:10px; font-weight:600; letter-spacing:.15em; }
      .view-control { border:1px solid var(--fp-line); border-radius:8px; background:#1b2940; color:#b7cae4; padding:7px 9px; font-size:11px; letter-spacing:0; min-height:34px; }
      .stage { position:relative; width:100%; aspect-ratio:1; isolation:isolate; }
      .stage img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; pointer-events:none; user-select:none; -webkit-user-drag:none; }
      .layer { mix-blend-mode:screen; opacity:0; transition:opacity .3s ease; }
      .marker { position:absolute; transform:translate(-50%,-50%); width:44px; height:44px; border-radius:50%; display:grid; place-items:center; color:#c2cfe3; border:1px solid #7892b566; background:#172338ee; box-shadow:0 3px 12px #0006; transition:background .2s,color .2s,box-shadow .2s; z-index:2; }
      .marker ha-icon { --mdc-icon-size:19px; width:19px; height:19px; }
      .marker[data-on="true"] { color:#fff0b4; border-color:#ffd77c; background:#614421ed; box-shadow:0 0 20px #ffba5655,0 3px 12px #0006; }
      .marker[data-unavailable="true"] { opacity:.6; color:#e9b7a1; border-style:dashed; }
      .opening-marker { position:absolute; transform:translate(-50%,-50%); width:48px; min-height:44px; display:grid; place-items:center; gap:1px; padding:4px; border:1px solid #426c66; border-radius:10px; background:#143432ee; color:#a9ddcf; box-shadow:0 3px 12px #0006; z-index:2; }
      .opening-marker ha-icon { --mdc-icon-size:19px; width:19px; height:19px; }.opening-marker .state { font-size:8px; line-height:1.2; }
      [data-opening][data-state="open"] { color:#ffd49b; border-color:#be8950; background:#49351feF; }
      [data-opening][data-state="unavailable"] { color:#bcc3cf; border-color:#67768b; border-style:dashed; opacity:.7; }
      .opening-list { display:grid; gap:7px; }.opening-row { width:100%; min-height:56px; display:flex; align-items:center; gap:11px; text-align:left; padding:10px 12px; border:1px solid #31544f; border-radius:11px; background:#102726; color:#a9ddcf; }
      .opening-row .name { display:block; color:#d5dfed; font-size:12px; }.opening-row .state { display:block; font-size:10px; margin-top:3px; }.opening-row .status-only { margin-left:auto; font-size:9px; color:#8196a9; }
      .room-label { position:absolute; transform:translate(-50%,-50%); color:#d3deee; text-shadow:0 1px 5px #000; font-size:clamp(8px,1vw,11px); font-weight:600; letter-spacing:.07em; pointer-events:none; z-index:1; white-space:nowrap; background:#0a14277a; padding:4px 6px; border-radius:4px; }
      .labels-hidden .room-label { display:none; }
      .legend { display:flex; gap:15px; align-items:center; justify-content:center; padding:0 12px 17px; color:var(--fp-muted); font-size:10px; flex-wrap:wrap; }
      .legend span { display:inline-flex; align-items:center; gap:6px; }.dot { width:6px; height:6px; border-radius:50%; background:#6e809d; }.dot.on { background:#ffd17e; }
      .summary { display:flex; align-items:baseline; justify-content:space-between; padding:0 0 17px; border-bottom:1px solid var(--fp-line); }
      .summary strong { font-size:30px; font-weight:500; letter-spacing:-.05em; }.summary .total { font-size:15px; color:#62758f; margin-left:5px; }
      .summary-label { display:block; color:var(--fp-muted); font-size:11px; margin-top:3px; }
      .off-all { border:1px solid var(--fp-line); background:#172237; color:#c1cfe3; border-radius:10px; padding:10px 12px; min-height:42px; font-size:11px; }
      .off-all:disabled { opacity:.4; }
      h2 { font-size:10px; text-transform:uppercase; letter-spacing:.16em; color:#8fa1bc; margin:21px 0 10px; font-weight:600; }
      .row { display:flex; align-items:stretch; gap:4px; margin-bottom:7px; }
      .circuit { flex:1; min-width:0; display:flex; align-items:center; gap:11px; text-align:left; border:1px solid var(--fp-line); border-radius:12px; background:#131e30; color:#d5dfed; padding:11px 12px; min-height:64px; }
      .circuit .bulb { display:grid; place-items:center; flex-shrink:0; width:34px; height:34px; background:#202e43; color:#8ea3c1; border-radius:10px; }
      .circuit .name { display:block; font-size:12px; font-weight:500; line-height:1.35; }.circuit .state { display:block; font-size:10px; color:#8193ad; margin-top:3px; }
      .circuit[data-on="true"] { border-color:#795b32; background:linear-gradient(105deg,#30271f,#192232); }
      .circuit[data-on="true"] .bulb { background:#5d4523; color:#ffda8d; }.circuit[data-on="true"] .state { color:#e7c98d; }
      .circuit[data-unavailable="true"] { opacity:.65; border-style:dashed; }
      .info { width:32px; flex-shrink:0; border:0; background:transparent; color:#7890ad; border-radius:8px; }.info:hover { background:#1c2c43; }
      .info ha-icon { --mdc-icon-size:17px; width:17px; height:17px; }
      .row [aria-busy="true"] { opacity:.6; }
      .note { font-size:11px; line-height:1.6; color:#869bb7; margin:19px 0 0; padding:13px; border:1px solid var(--fp-line); border-radius:11px; background:#101a2b; }
      .footer { margin-top:22px; padding-top:16px; border-top:1px solid var(--fp-line); display:flex; gap:12px; justify-content:space-between; color:#697f9c; font-size:10px; line-height:1.5; }
      .error { color:#ffc6b9; background:#432e31; padding:12px; border-radius:8px; font-size:12px; margin:12px 0 0; }.error:empty { display:none; }
      @media(max-width:1050px) { .shell { padding:20px; }.layout { grid-template-columns:minmax(0,1fr) 245px; gap:17px; }.marker { width:40px; height:40px; }.marker[data-compact-hide="true"] { display:none; } }
      @media(max-width:760px) { .shell { padding:16px; border-radius:16px; }.layout { grid-template-columns:1fr; gap:22px; }.top { margin-bottom:18px; align-items:flex-start; }.connection { font-size:10px; padding:7px 9px; }.subtitle { font-size:11px; max-width:235px; }.visual-head { padding:12px 12px 0; font-size:9px; }.marker { width:40px; height:40px; }.rooms { display:grid; grid-template-columns:1fr 1fr; gap:0 14px; }.room { min-width:0; }.circuit { padding:10px 8px; gap:7px; }.circuit .bulb { width:27px; height:30px; }.circuit .name { font-size:11px; }.info { width:26px; }.footer { margin-top:17px; }.room-label { font-size:8px; }.legend { font-size:9px; gap:11px; } }
      @media(max-width:760px) { .room.wide { grid-column:1/-1; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); column-gap:8px; }.room.wide h2 { grid-column:1/-1; }.room.wide .bulb { display:none; }.room.wide .circuit { justify-content:center; text-align:center; }.room.wide .info { width:24px; } }
      @media(max-width:350px) { .rooms { grid-template-columns:1fr; }.shell { padding:12px; }.marker { width:36px; height:36px; }.connection { font-size:9px; } }
      .layout.model-only { grid-template-columns:minmax(0,1fr); max-width:920px; margin:0 auto; gap:0; }
      .connection.model-only { color:#aac0dc; background:#1b2940; border-color:#35465f; }.connection.model-only::before { display:none; }
      .model-only .note { margin-top:16px; }
      @media(prefers-reduced-motion:reduce) { * { transition:none!important; } }
      </style>
      <section class="shell" aria-label="${e(c.title)} ${modelOnly?'model-only':'interactive'} floorplan">
        <header class="top"><div><div class="eyebrow">HOME · DIGITAL TWIN</div><h1>${e(c.title)}</h1><p class="subtitle">${e(c.subtitle || 'Your home, in a different light.')}</p></div><div class="connection${modelOnly?' model-only':''}">${modelOnly?'Model only':'Live'}</div></header>
        <div class="layout${modelOnly?' model-only':''}">
          <div class="visual"><div class="visual-head"><span>3D FLOOR PLAN</span><button class="view-control" data-action="labels" aria-pressed="true">Room labels</button></div>
            <div class="stage">
              <img class="base" src="${e(c.image)}" alt="${e(c.image_alt || '3D cutaway of '+c.title+' from the house SketchUp model')}" draggable="false">
              ${c.lights.map((l,i)=>`<img class="layer" data-layer="${i}" src="${e(l.image)}" alt="" aria-hidden="true" draggable="false">`).join('')}
              ${(c.labels||[]).map(l=>`<span class="room-label" style="left:${Number(l.x)}%;top:${Number(l.y)}%">${e(l.text)}</span>`).join('')}
              ${c.lights.map((l,i)=>`<button class="marker" data-light="${i}" data-compact-hide="${Boolean(l.compact_hide)}" style="left:${Number(l.x)}%;top:${Number(l.y)}%" aria-label="Toggle ${e(l.room+' '+l.name)}" title="${e(l.room+' · '+l.name)}">${bulb}</button>`).join('')}
              ${openings.map((o,i)=>`<button class="opening-marker" data-opening="${i}" data-state="unavailable" style="left:${Number(o.x)}%;top:${Number(o.y)}%" aria-label="${e(o.name)} status"><ha-icon icon="mdi:help-circle-outline"></ha-icon><span class="state">—</span></button>`).join('')}
            </div>${c.lights.length?'<div class="legend"><span><i class="dot on"></i>On</span><span><i class="dot"></i>Off</span><span>Tap a light to toggle</span></div>':''}
          </div>
          <aside aria-label="${modelOnly?'Floor information':'Lighting controls and status'}">${c.lights.length?`<div class="summary"><div><strong class="on-count">0</strong><span class="total">/ ${c.lights.length}</span><span class="summary-label">lights on</span></div><button class="off-all" data-action="off">All off</button></div>`:''}
            <div class="rooms">${rooms.map(room=>`<section class="room ${c.lights.filter(l=>l.room===room).length>2?'wide':''}"><h2>${e(room)}</h2>${c.lights.map((l,i)=>l.room!==room?'':`<div class="row"><button class="circuit" data-light="${i}"><span class="bulb">${bulb}</span><span><span class="name">${e(l.name)}</span><span class="state">Connecting</span></span></button><button class="info" data-info="${i}" aria-label="Details for ${e(l.room+' '+l.name)}" title="Details"><ha-icon icon="mdi:dots-horizontal"></ha-icon></button></div>`).join('')}</section>`).join('')}</div>
            ${openings.length?`<section class="openings"><h2>Doors · live status</h2><div class="opening-list">${openings.map((o,i)=>`<button class="opening-row" data-opening="${i}" data-state="unavailable"><ha-icon icon="mdi:help-circle-outline"></ha-icon><span><span class="name">${e(o.name)}</span><span class="state">Connecting</span></span><span class="status-only">Status only</span></button>`).join('')}</div></section>`:''}
            ${c.note?`<p class="note">${e(c.note)}</p>`:''}<div class="error" role="alert"></div>
          </aside>
        </div><footer class="footer"><span>${e(c.model_source || 'SketchUp → Blender')} · ${e(c.floor_label || c.title)}</span><span>${modelOnly?'Reference model · No connected devices':openings.length?'Lights and door status follow Home Assistant':'Lighting follows Home Assistant'}</span></footer>
      </section>`;
    this.shadowRoot.querySelectorAll('[data-light]').forEach(b=>b.addEventListener('click',()=>this._toggle(Number(b.dataset.light))));
    this.shadowRoot.querySelectorAll('[data-info]').forEach(b=>b.addEventListener('click',()=>this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:c.lights[Number(b.dataset.info)].entity},bubbles:true,composed:true}))));
    this.shadowRoot.querySelectorAll('[data-opening]').forEach(b=>b.addEventListener('click',()=>this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:openings[Number(b.dataset.opening)].entity},bubbles:true,composed:true}))));
    this.shadowRoot.querySelector('[data-action="labels"]').addEventListener('click',ev=>{const hidden=this.shadowRoot.querySelector('.stage').classList.toggle('labels-hidden');ev.currentTarget.setAttribute('aria-pressed',String(!hidden));});
    this.shadowRoot.querySelector('[data-action="off"]')?.addEventListener('click',()=>this._allOff());
    this.shadowRoot.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>this._error('A floorplan image could not load. Check your connection and reload.')));
  }
  _update() {
    const root=this.shadowRoot, c=this._config;
    let on=0, unavailable=0;
    const connected=this._hass?.connected !== false;
    c.lights.forEach((l,i)=>{
      const state=this._hass.states[l.entity]?.state;
      const valid=connected && ['on','off'].includes(state), active=valid && state==='on';
      on+=Number(active); unavailable+=Number(!valid);
      root.querySelector(`[data-layer="${i}"]`).style.opacity=active?'1':'0';
      root.querySelectorAll(`[data-light="${i}"]`).forEach(b=>{
        b.dataset.on=String(active); b.dataset.unavailable=String(!valid);
        b.setAttribute('aria-pressed',String(active)); b.setAttribute('aria-busy',String(this._pending.has(l.entity)));
        b.disabled=!valid || this._pending.has(l.entity);
        const status=b.querySelector('.state');if(status)status.textContent=!valid?'Unavailable':active?'On':'Off';
      });
    });
    (c.openings||[]).forEach((o,i)=>{
      const value=this._hass.states[o.entity]?.state, valid=connected && ['on','off'].includes(value);
      const state=valid?(value==='on'?'open':'closed'):'unavailable', text=valid?(state==='open'?'Open':'Closed'):'Unavailable';
      const icon=!valid?'mdi:help-circle-outline':o.kind==='garage'?(state==='open'?'mdi:garage-open':'mdi:garage'):(state==='open'?'mdi:door-open':'mdi:door-closed');
      unavailable+=Number(!valid);
      root.querySelectorAll(`[data-opening="${i}"]`).forEach(b=>{
        b.dataset.state=state;b.setAttribute('aria-label',`${o.name}: ${text}. View sensor details.`);b.title=`${o.name} · ${text} · status only`;
        b.querySelector('ha-icon').setAttribute('icon',icon);
        b.querySelector('.state').textContent=b.classList.contains('opening-marker')&&!valid?'—':text;
        b.disabled=!connected || !this._hass.states[o.entity];
      });
    });
    const count=root.querySelector('.on-count'), allOff=root.querySelector('[data-action="off"]');
    if(count)count.textContent=String(on);
    if(allOff)allOff.disabled=!on || this._pending.size>0;
    const live=root.querySelector('.connection'), modelOnly=!c.lights.length && !(c.openings||[]).length;
    live.textContent=modelOnly?'Model only':!connected?'Disconnected':unavailable?`${unavailable} unavailable`:'Live';
    live.classList.toggle('offline',!modelOnly && (!connected || unavailable>0));
  }
  _error(text) { this.shadowRoot.querySelector('.error').textContent=text; }
  async _toggle(i) {
    const l=this._config.lights[i];
    if(!l || this._pending.has(l.entity) || !['on','off'].includes(this._hass.states[l.entity]?.state)) return;
    this._pending.add(l.entity);this._error('');this._update();
    try { await this._hass.callService(l.entity.split('.')[0],'toggle',{entity_id:l.entity}); }
    catch(err) { this._error(`Could not control ${l.name}: ${err.message || 'request failed'}`); }
    finally { this._pending.delete(l.entity);this._update(); }
  }
  async _allOff() {
    const groups={};
    this._config.lights.forEach(l=>{if(this._hass.states[l.entity]?.state==='on'){const d=l.entity.split('.')[0];(groups[d]??=[]).push(l.entity);}});
    this._error('');
    const targets=Object.values(groups).flat();targets.forEach(id=>this._pending.add(id));this._update();
    try { await Promise.all(Object.entries(groups).map(([domain,ids])=>this._hass.callService(domain,'turn_off',{entity_id:ids}))); }
    catch(err) { this._error(`Could not turn all lights off: ${err.message || 'request failed'}`); }
    finally { targets.forEach(id=>this._pending.delete(id));this._update(); }
  }
}
if(!customElements.get('house-floorplan-card')) customElements.define('house-floorplan-card',HouseFloorplanCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'house-floorplan-card',name:'House 3D Floorplan',description:'Locally rendered house with live, individual lighting layers.'});
