/* Local, dependency-free Home Assistant floorplan. Assets are hosted by HA. */
class HouseFloorplanCard extends HTMLElement {
  constructor() {
    super();this.attachShadow({mode:'open'});this._pending=new Set();this._zoom=1;this._pan={x:0,y:0};
    this._resize=()=>this._fit();this._fullscreen=()=>{this._fit();this._syncFullscreen();};
  }
  connectedCallback() {
    window.addEventListener('resize',this._resize);document.addEventListener('fullscreenchange',this._fullscreen);
    this._observer=new ResizeObserver(()=>this._fit());this._observer.observe(this);this._fit();
  }
  disconnectedCallback() {
    window.removeEventListener('resize',this._resize);document.removeEventListener('fullscreenchange',this._fullscreen);this._observer?.disconnect();
  }
  setConfig(config) {
    if(!config.image||!Array.isArray(config.lights))throw new Error('Floorplan requires image and lights.');
    if(config.model_only&&(config.lights.length||config.openings?.length))throw new Error('Model-only floorplans cannot bind devices.');
    this._config=structuredClone(config);this._zoom=1;this._pan={x:0,y:0};this._bounds=[0,0,1,1];this._render();this._update();this._fit();
  }
  set hass(value) {this._hass=value;if(this._config)this._update();}
  get hass() {return this._hass;}
  getCardSize() {return 10;}
  static getStubConfig() {return {title:'House',image:'',lights:[]};}
  _escape(s) {return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  _imageBounds(img) {
    // Fit the actual model, not the transparent square around it. No asset changes.
    try {
      const canvas=document.createElement('canvas');canvas.width=canvas.height=256;
      const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0,256,256);
      const pixels=ctx.getImageData(0,0,256,256).data;let x0=256,y0=256,x1=0,y1=0;
      for(let y=0;y<256;y++)for(let x=0;x<256;x++)if(pixels[(y*256+x)*4+3]>8){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x+1);y1=Math.max(y1,y+1);}
      this._bounds=x1>x0?[x0/256,y0/256,x1/256,y1/256]:[0,0,1,1];
    } catch {this._bounds=[0,0,1,1];}
    this._fit();
  }
  _fit() {
    if(!this.isConnected||!this._config)return;
    const top=Math.max(0,this.getBoundingClientRect().top),height=Math.max(420,Math.floor(window.innerHeight-top-8));
    if(this.style.getPropertyValue('--floor-height')!==height+'px')this.style.setProperty('--floor-height',height+'px');
    const canvas=this.shadowRoot.querySelector('.canvas'),stage=this.shadowRoot.querySelector('.stage');if(!canvas||!stage)return;
    let [x0,y0,x1,y1]=this._bounds||[0,0,1,1];
    // Labels and touch targets must also stay within the fitted viewport.
    for(const p of [...(this._config.labels||[]),...this._config.lights,...(this._config.openings||[])]) {
      x0=Math.min(x0,Number(p.x)/100);x1=Math.max(x1,Number(p.x)/100);y0=Math.min(y0,Number(p.y)/100);y1=Math.max(y1,Number(p.y)/100);
    }
    const w=canvas.clientWidth,h=canvas.clientHeight,padding=w<500?34:26;
    const size=Math.max(1,Math.min((w-padding*2)/(x1-x0),(h-padding*2)/(y1-y0)))*this._zoom;
    const maxPanX=Math.max(0,(size*(x1-x0)-w+padding*2)/2),maxPanY=Math.max(0,(size*(y1-y0)-h+padding*2)/2);
    this._pan.x=Math.max(-maxPanX,Math.min(maxPanX,this._pan.x));this._pan.y=Math.max(-maxPanY,Math.min(maxPanY,this._pan.y));
    Object.assign(stage.style,{width:size+'px',height:size+'px',left:(w-size*(x0+x1))/2+this._pan.x+'px',top:(h-size*(y0+y1))/2+this._pan.y+'px'});
    canvas.dataset.zoomed=String(this._zoom>1);
    const reset=this.shadowRoot.querySelector('[data-action="fit"]');if(reset)reset.textContent=this._zoom===1?'Fit':Math.round(this._zoom*100)+'%';
    // Keep optional crowded bathroom markers out of compact renderings; their drawer controls remain.
    stage.classList.toggle('compact',size<700);
  }
  _setZoom(value) {this._zoom=Math.max(1,Math.min(2.2,Math.round(value*10)/10));if(this._zoom===1)this._pan={x:0,y:0};this._fit();}
  _syncFullscreen() {const b=this.shadowRoot.querySelector('[data-action="fullscreen"]');if(b){b.textContent=document.fullscreenElement?'Exit full screen':'Full screen';b.setAttribute('aria-pressed',String(Boolean(document.fullscreenElement)));}}
  _render() {
    const c=this._config,e=s=>this._escape(s),rooms=[...new Set(c.lights.map(l=>l.room))],openings=c.openings||[],modelOnly=!c.lights.length&&!openings.length;
    const bulb='<ha-icon icon="mdi:lightbulb-outline"></ha-icon>';
    this.shadowRoot.innerHTML=`
      <style>
      :host {display:block;color:#e7edf8;--fp-muted:#9eafc5;--fp-line:#9cb6d32e;font-family:var(--primary-font-family,system-ui,sans-serif);}
      * {box-sizing:border-box;}[hidden] {display:none!important;}button,summary {font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent;}button:focus-visible,summary:focus-visible {outline:3px solid #83bdff;outline-offset:2px;}button:disabled {cursor:default;opacity:.55;}
      ha-icon {--mdc-icon-size:21px;width:21px;height:21px;}
      .shell {height:var(--floor-height,calc(100dvh - 72px));min-height:420px;padding:4px;background:#080f1b;}
      .visual {height:100%;width:100%;position:relative;isolation:isolate;display:grid;grid-template-rows:auto minmax(0,1fr) auto;overflow:hidden;border:1px solid var(--fp-line);border-radius:16px;background:radial-gradient(ellipse at 50% 46%,#1c2c43,#101b2c 72%);}
      .visual:fullscreen {height:100dvh;width:100vw;border-radius:0;}
      .top {position:relative;z-index:4;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;background:linear-gradient(#0b1424e8,#0b14249c);}
      h1 {font-size:24px;letter-spacing:-.035em;line-height:1.2;margin:0;font-weight:600;}.subtitle {font-size:11px;color:var(--fp-muted);margin:4px 0 0;}
      .top-actions,.tools,.summary,.zoom {display:flex;align-items:center;gap:8px;}.top-actions {flex-wrap:wrap;justify-content:flex-end;}
      .view-control,.off-all {min-height:40px;padding:7px 12px;font-size:12px;border:1px solid #6984a94a;border-radius:10px;background:#142239eb;color:#d3e1f3;}
      .view-control[aria-expanded="true"],.view-control[aria-pressed="true"] {border-color:#648bb3;}
      .connection {font-size:11px;color:#9cdfca;white-space:nowrap;}.connection::before {content:'●';margin-right:5px;font-size:8px;color:#7de1b5;}.connection.offline {color:#f2b38a;}.connection.offline::before {color:#f2b38a;}.connection.model-only {color:#acbed5;}.connection.model-only::before {display:none;}
      .canvas {position:relative;min-height:0;overflow:hidden;isolation:isolate;touch-action:pan-y;}.canvas[data-zoomed="true"] {cursor:grab;touch-action:none;}.canvas.dragging {cursor:grabbing;}
      .stage {position:absolute;isolation:isolate;}.stage img {position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none;user-select:none;-webkit-user-drag:none;}
      .layer {mix-blend-mode:screen;opacity:0;transition:opacity .3s ease;}
      .marker {position:absolute;transform:translate(-50%,-50%);width:44px;height:44px;border-radius:50%;display:grid;place-items:center;color:#c2cfe3;border:1px solid #7892b588;background:#172338ef;box-shadow:0 3px 12px #0008;z-index:2;}
      .marker ha-icon {--mdc-icon-size:20px;width:20px;height:20px;}.marker[data-on="true"] {color:#fff0b4;border-color:#ffd77c;background:#614421ed;box-shadow:0 0 20px #ffba5655,0 3px 12px #0006;}.marker[data-unavailable="true"] {color:#e9b7a1;border-style:dashed;}
      .stage.compact .marker[data-compact-hide="true"] {display:none;}
      .opening-marker {position:absolute;transform:translate(-50%,-50%);width:48px;min-height:44px;display:grid;place-items:center;gap:1px;padding:4px;border:1px solid #426c66;border-radius:10px;background:#143432ef;color:#a9ddcf;box-shadow:0 3px 12px #0006;z-index:2;}
      .opening-marker ha-icon {--mdc-icon-size:19px;width:19px;height:19px;}.opening-marker .state {font-size:8px;line-height:1.2;}
      [data-opening][data-state="open"] {color:#ffd49b;border-color:#be8950;background:#49351fef;}[data-opening][data-state="unavailable"] {color:#bcc3cf;border-color:#67768b;border-style:dashed;}
      .room-label {position:absolute;transform:translate(-50%,-50%);color:#e0e8f3;text-shadow:0 1px 5px #000;font-size:11px;font-weight:600;letter-spacing:.06em;pointer-events:none;z-index:1;white-space:nowrap;background:#0a1427a0;padding:4px 6px;border-radius:4px;}.labels-hidden .room-label {display:none;}
      .dock {position:relative;z-index:4;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 14px;background:linear-gradient(#0b142499,#0b1424ed);}
      .summary {font-size:12px;color:#c6d5e8;}.summary strong {font-size:19px;color:#ffdda6;}.total,.summary-label {color:var(--fp-muted);}.off-all {margin-left:8px;}
      .zoom {gap:3px;}.zoom button {min-width:40px;}.zoom .step {font-size:20px;}.zoom [data-action="fit"] {font-size:11px;min-width:46px;}
      .legend {font-size:11px;color:var(--fp-muted);}.legend .dot {display:inline-block;width:6px;height:6px;border-radius:50%;background:#ffd17e;margin-right:5px;}
      .drawer {position:absolute;right:12px;top:74px;bottom:66px;width:min(340px,calc(100% - 24px));overflow:auto;z-index:6;padding:14px;border:1px solid #506586;border-radius:14px;background:#0e192bf5;box-shadow:0 8px 28px #0008;}
      .drawer-head {display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:13px;font-weight:600;}.drawer h2 {font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:#a5b8d2;margin:18px 0 8px;}.row {display:flex;gap:4px;margin-bottom:7px;}
      .circuit {flex:1;min-width:0;display:flex;align-items:center;gap:10px;text-align:left;border:1px solid var(--fp-line);border-radius:10px;background:#17253a;color:#dae4f3;padding:10px;min-height:54px;}.circuit .bulb {display:grid;place-items:center;flex-shrink:0;width:32px;height:32px;background:#253851;color:#9bb1ce;border-radius:8px;}.circuit .name {display:block;font-size:12px;line-height:1.35;}.circuit .state {display:block;font-size:10px;color:#9aacc5;margin-top:3px;}
      .circuit[data-on="true"] {border-color:#95713c;background:#342a22;}.circuit[data-on="true"] .bulb {color:#ffda8d;background:#5d4523;}.circuit[data-on="true"] .state {color:#e7c98d;}.circuit[data-unavailable="true"] {border-style:dashed;}
      .info {width:40px;flex-shrink:0;border:0;background:#18253a;color:#a7bcda;border-radius:8px;}.row [aria-busy="true"] {opacity:.6;}
      .opening-list {display:grid;gap:7px;}.opening-row {width:100%;min-height:54px;display:flex;align-items:center;gap:10px;text-align:left;padding:10px;border:1px solid #31544f;border-radius:10px;background:#102726;color:#a9ddcf;}.opening-row .name {display:block;color:#d5dfed;font-size:12px;}.opening-row .state {display:block;font-size:10px;margin-top:3px;}.status-only {margin-left:auto;font-size:9px;color:#99aec5;}
      .model-info {position:absolute;left:16px;bottom:68px;z-index:5;font-size:11px;color:var(--fp-muted);max-width:min(420px,calc(100% - 32px));}.model-info summary {background:#0c182acf;border:1px solid var(--fp-line);border-radius:8px;padding:8px 10px;width:max-content;}.model-info[open] {padding:10px;background:#0e192bf5;border:1px solid var(--fp-line);border-radius:12px;}.note {font-size:11px;line-height:1.6;margin:10px 0;}.footer {font-size:10px;line-height:1.6;display:grid;gap:4px;}
      .error {position:absolute;top:80px;left:12px;max-width:calc(100% - 24px);z-index:8;color:#ffc6b9;background:#432e31;padding:12px;border-radius:8px;font-size:12px;}.error:empty {display:none;}
      @media(max-width:760px) {.top {padding:8px 10px;gap:8px;flex-wrap:wrap;}h1 {font-size:21px;}.subtitle {font-size:10px;}.top-actions {gap:6px;}.view-control,.off-all {padding:6px 10px;}.dock {padding:7px 9px;gap:6px;flex-wrap:wrap;}.legend {display:none;}.tools {gap:5px;}.room-label {font-size:9px;}.drawer {top:106px;}.model-info {bottom:108px;}.marker {width:40px;height:40px;}}
      @media(max-width:350px) {.marker {width:36px;height:36px;}.opening-marker {width:42px;min-height:40px;}.room-label {font-size:8px;}.top-actions .view-control {font-size:10px;}.summary {font-size:11px;}.off-all {margin-left:0;}}
      @media(max-height:650px) and (orientation:landscape) {.top {padding:6px 12px;}h1 {font-size:20px;}.subtitle {display:none;}.dock {padding:5px 10px;}.drawer {top:58px;bottom:60px;}.model-info {bottom:62px;}.room-label {font-size:9px;}}
      @media(prefers-reduced-motion:reduce) {* {transition:none!important;}}
      </style>
      <section class="shell" aria-label="${e(c.title)} ${modelOnly?'model-only':'interactive'} floorplan"><div class="visual">
        <header class="top"><div><h1>${e(c.title)}</h1><p class="subtitle">${e(c.subtitle||'Your home, in a different light.')}</p></div><div class="top-actions"><span class="connection${modelOnly?' model-only':''}">${modelOnly?'Model only':'Connecting'}</span><button class="view-control" data-action="overview">All floors</button><button class="view-control" data-action="fullscreen" aria-pressed="false">Full screen</button></div></header>
        <div class="canvas"><div class="stage">
          <img class="base" src="${e(c.image)}" alt="${e(c.image_alt||'3D cutaway of '+c.title+' from the house SketchUp model')}" draggable="false">
          ${c.lights.map((l,i)=>`<img class="layer" data-layer="${i}" src="${e(l.image)}" alt="" aria-hidden="true" draggable="false">`).join('')}
          ${(c.labels||[]).map(l=>`<span class="room-label" style="left:${Number(l.x)}%;top:${Number(l.y)}%">${e(l.text)}</span>`).join('')}
          ${c.lights.map((l,i)=>`<button class="marker" data-light="${i}" data-compact-hide="${Boolean(l.compact_hide)}" style="left:${Number(l.x)}%;top:${Number(l.y)}%" aria-label="Toggle ${e(l.room+' '+l.name)}" title="${e(l.room+' · '+l.name)}">${bulb}</button>`).join('')}
          ${openings.map((o,i)=>`<button class="opening-marker" data-opening="${i}" data-state="unavailable" style="left:${Number(o.x)}%;top:${Number(o.y)}%" aria-label="${e(o.name)} status"><ha-icon icon="mdi:help-circle-outline"></ha-icon><span class="state">—</span></button>`).join('')}
        </div></div>
        <div class="dock">${c.lights.length?`<div class="summary"><span><strong class="on-count">0</strong><span class="total"> / ${c.lights.length}</span> <span class="summary-label">on</span></span><button class="off-all" data-action="off">All off</button></div>`:'<span class="connection model-only">No connected devices</span>'}
          ${c.lights.length?'<div class="legend"><span class="dot"></span>Tap a bulb to toggle</div>':''}
          <div class="tools"><div class="zoom" aria-label="Render zoom"><button class="view-control step" data-action="out" aria-label="Zoom out">−</button><button class="view-control" data-action="fit" title="Reset zoom and pan">Fit</button><button class="view-control step" data-action="in" aria-label="Zoom in">+</button></div><button class="view-control" data-action="labels" aria-pressed="true">Labels</button>${!modelOnly?'<button class="view-control" data-action="controls" aria-expanded="false" aria-controls="controls">Controls</button>':''}</div>
        </div>
        ${!modelOnly?`<aside class="drawer" id="controls" hidden aria-label="Lighting controls and status"><div class="drawer-head">${e(c.title)} · controls<button class="view-control" data-action="close-controls" aria-label="Close controls">✕</button></div><div class="rooms">${rooms.map(room=>`<section class="room"><h2>${e(room)}</h2>${c.lights.map((l,i)=>l.room!==room?'':`<div class="row"><button class="circuit" data-light="${i}"><span class="bulb">${bulb}</span><span><span class="name">${e(l.name)}</span><span class="state">Connecting</span></span></button><button class="info" data-info="${i}" aria-label="Details for ${e(l.room+' '+l.name)}"><ha-icon icon="mdi:dots-horizontal"></ha-icon></button></div>`).join('')}</section>`).join('')}</div>
          ${openings.length?`<section class="openings"><h2>Doors · status only</h2><div class="opening-list">${openings.map((o,i)=>`<button class="opening-row" data-opening="${i}" data-state="unavailable"><ha-icon icon="mdi:help-circle-outline"></ha-icon><span><span class="name">${e(o.name)}</span><span class="state">Connecting</span></span><span class="status-only">Status only</span></button>`).join('')}</div></section>`:''}</aside>`:''}
        <details class="model-info"><summary>About this model</summary>${c.note?`<p class="note">${e(c.note)}</p>`:''}<footer class="footer"><span>${e(c.model_source||'SketchUp → Blender')} · ${e(c.floor_label||c.title)}</span><span>${modelOnly?'Reference model · No connected devices':openings.length?'Lights and door status follow Home Assistant':'Lighting follows Home Assistant'}</span></footer></details><div class="error" role="alert"></div>
      </div></section>`;
    const root=this.shadowRoot;
    root.querySelectorAll('[data-light]').forEach(b=>b.addEventListener('click',()=>this._toggle(Number(b.dataset.light))));
    const details=entityId=>this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId},bubbles:true,composed:true}));
    root.querySelectorAll('[data-info]').forEach(b=>b.addEventListener('click',()=>details(c.lights[Number(b.dataset.info)].entity)));
    root.querySelectorAll('[data-opening]').forEach(b=>b.addEventListener('click',()=>details(openings[Number(b.dataset.opening)].entity)));
    root.querySelector('[data-action="labels"]').addEventListener('click',ev=>{const hidden=root.querySelector('.stage').classList.toggle('labels-hidden');ev.currentTarget.setAttribute('aria-pressed',String(!hidden));});
    root.querySelector('[data-action="off"]')?.addEventListener('click',()=>this._allOff());
    const toggleControls=show=>{const drawer=root.querySelector('.drawer'),button=root.querySelector('[data-action="controls"]');if(drawer){drawer.hidden=!show;button.setAttribute('aria-expanded',String(show));if(!show)button.focus();}};
    root.querySelector('[data-action="controls"]')?.addEventListener('click',()=>toggleControls(root.querySelector('.drawer').hidden));
    root.querySelector('[data-action="close-controls"]')?.addEventListener('click',()=>toggleControls(false));
    root.querySelector('.visual').addEventListener('keydown',ev=>{if(ev.key==='Escape')toggleControls(false);});
    root.querySelector('[data-action="in"]').addEventListener('click',()=>this._setZoom(this._zoom+.2));
    root.querySelector('[data-action="out"]').addEventListener('click',()=>this._setZoom(this._zoom-.2));
    root.querySelector('[data-action="fit"]').addEventListener('click',()=>this._setZoom(1));
    root.querySelector('[data-action="overview"]').addEventListener('click',()=>{history.pushState(null,'','/house-3d/all-floors');window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));});
    const fullscreen=root.querySelector('[data-action="fullscreen"]');fullscreen.hidden=!document.fullscreenEnabled;
    fullscreen.addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await root.querySelector('.visual').requestFullscreen();}catch{this._error('Full screen unavailable. Use your browser full-screen option.');}});
    const canvas=root.querySelector('.canvas');let drag=null;
    canvas.addEventListener('pointerdown',ev=>{if(this._zoom===1||ev.target.closest('button')||ev.button!==0)return;drag={x:ev.clientX,y:ev.clientY,pan:{...this._pan}};canvas.setPointerCapture(ev.pointerId);canvas.classList.add('dragging');});
    canvas.addEventListener('pointermove',ev=>{if(drag){this._pan={x:drag.pan.x+ev.clientX-drag.x,y:drag.pan.y+ev.clientY-drag.y};this._fit();}});
    const stop=()=>{drag=null;canvas.classList.remove('dragging');};canvas.addEventListener('pointerup',stop);canvas.addEventListener('pointercancel',stop);
    root.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>this._error('A floorplan image could not load. Check your connection and reload.')));
    const base=root.querySelector('.base');base.addEventListener('load',()=>this._imageBounds(base));if(base.complete&&base.naturalWidth)this._imageBounds(base);
    this._syncFullscreen();
  }
  _update() {
    const root=this.shadowRoot,c=this._config,states=this._hass?.states||{};
    let on=0,unavailable=0;const connected=Boolean(this._hass)&&this._hass.connected!==false;
    c.lights.forEach((l,i)=>{
      const state=states[l.entity]?.state,valid=connected&&['on','off'].includes(state),active=valid&&state==='on';on+=Number(active);unavailable+=Number(!valid);
      root.querySelector(`[data-layer="${i}"]`).style.opacity=active?'1':'0';
      root.querySelectorAll(`[data-light="${i}"]`).forEach(b=>{b.dataset.on=String(active);b.dataset.unavailable=String(!valid);b.setAttribute('aria-pressed',String(active));b.setAttribute('aria-busy',String(this._pending.has(l.entity)));b.disabled=!valid||this._pending.has(l.entity);const status=b.querySelector('.state');if(status)status.textContent=!valid?'Unavailable':active?'On':'Off';});
    });
    (c.openings||[]).forEach((o,i)=>{
      const value=states[o.entity]?.state,valid=connected&&['on','off'].includes(value),state=valid?(value==='on'?'open':'closed'):'unavailable',text=valid?(state==='open'?'Open':'Closed'):'Unavailable';
      const icon=!valid?'mdi:help-circle-outline':o.kind==='garage'?(state==='open'?'mdi:garage-open':'mdi:garage'):(state==='open'?'mdi:door-open':'mdi:door-closed');unavailable+=Number(!valid);
      root.querySelectorAll(`[data-opening="${i}"]`).forEach(b=>{b.dataset.state=state;b.setAttribute('aria-label',`${o.name}: ${text}. View sensor details.`);b.title=`${o.name} · ${text} · status only`;b.querySelector('ha-icon').setAttribute('icon',icon);b.querySelector('.state').textContent=b.classList.contains('opening-marker')&&!valid?'—':text;b.disabled=!connected||!states[o.entity];});
    });
    const count=root.querySelector('.on-count'),allOff=root.querySelector('[data-action="off"]');if(count)count.textContent=String(on);if(allOff)allOff.disabled=!on||this._pending.size>0;
    const live=root.querySelector('.top .connection'),modelOnly=!c.lights.length&&!(c.openings||[]).length;
    live.textContent=modelOnly?'Model only':!connected?'Disconnected':unavailable?`${unavailable} unavailable`:'Live';live.classList.toggle('offline',!modelOnly&&(!connected||unavailable>0));
  }
  _error(text) {this.shadowRoot.querySelector('.error').textContent=text;}
  async _toggle(i) {
    const l=this._config.lights[i];
    if(!l||!this._hass||this._hass.connected===false||this._pending.has(l.entity)||!['on','off'].includes(this._hass.states[l.entity]?.state))return;
    this._pending.add(l.entity);this._error('');this._update();
    try{await this._hass.callService(l.entity.split('.')[0],'toggle',{entity_id:l.entity});}catch(err){this._error(`Could not control ${l.name}: ${err.message||'request failed'}`);}finally{this._pending.delete(l.entity);this._update();}
  }
  async _allOff() {
    if(!this._hass||this._hass.connected===false||this._pending.size)return;
    const groups={};this._config.lights.forEach(l=>{if(this._hass.states[l.entity]?.state==='on'){const d=l.entity.split('.')[0];(groups[d]??=[]).push(l.entity);}});
    this._error('');const targets=Object.values(groups).flat();targets.forEach(id=>this._pending.add(id));this._update();
    try{await Promise.all(Object.entries(groups).map(([domain,ids])=>this._hass.callService(domain,'turn_off',{entity_id:ids})));}catch(err){this._error(`Could not turn all lights off: ${err.message||'request failed'}`);}finally{targets.forEach(id=>this._pending.delete(id));this._update();}
  }
}
if(!customElements.get('house-floorplan-card'))customElements.define('house-floorplan-card',HouseFloorplanCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'house-floorplan-card',name:'House 3D Floorplan',description:'Full-panel house render with live lighting, in-render controls, zoom and fullscreen.'});
