/* Whole-house monitor. Read-only: navigation/details only, never device services. */
class HouseOverviewCard extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'});
    this._resize=()=>this._fit();
    this._fullscreen=()=>{this._fit();this._syncFullscreen();};
  }
  connectedCallback() {
    window.addEventListener('resize',this._resize);
    document.addEventListener('fullscreenchange',this._fullscreen);
    this._observer=new ResizeObserver(()=>this._fit());
    this._observer.observe(this);
    this._fit();
  }
  disconnectedCallback() {
    window.removeEventListener('resize',this._resize);
    document.removeEventListener('fullscreenchange',this._fullscreen);
    this._observer?.disconnect();
  }
  setConfig(config) {
    if(!Array.isArray(config.floors)||config.floors.length!==4) throw new Error('Overview needs four floor configurations.');
    for(const f of config.floors) {
      if(!f.image||!Array.isArray(f.lights)||!/^\/(?!\/)/.test(f.navigation_path||'')) throw new Error('Each floor needs an image, lights and local navigation path.');
      if(f.model_only&&(f.lights.length||f.openings?.length)) throw new Error('Model-only floors cannot bind devices.');
    }
    this._config=structuredClone(config);this._render();this._update();this._fit();
  }
  set hass(value) { this._hass=value;if(this._config)this._update(); }
  get hass() { return this._hass; }
  getCardSize() { return 10; }
  _escape(value) { return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  _fit() {
    if(!this.isConnected)return;
    const top=this.getBoundingClientRect().top;
    // HA's toolbar/tabs remain outside the card. Recompute for viewport/fullscreen changes.
    const height=Math.max(320,Math.floor(window.innerHeight-Math.max(0,top)-8));
    if(this.style.getPropertyValue('--overview-height')!==height+'px')this.style.setProperty('--overview-height',height+'px');
  }
  _navigate(index) {
    history.pushState(null,'',this._config.floors[index].navigation_path);
    window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));
  }
  _details(entity) {
    this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:entity},bubbles:true,composed:true}));
  }
  _syncFullscreen() {
    const button=this.shadowRoot.querySelector('.fullscreen');
    if(button){button.textContent=document.fullscreenElement?'Exit full screen':'Full screen';button.setAttribute('aria-pressed',String(Boolean(document.fullscreenElement)));}
  }
  _label(f,l) {
    const room=l.room.replace(/ room$/i,'').replace('Lorena bathroom','Bathroom').replace('Garage & entrance','Garage / entry');
    const name=l.name.replace(/^Light (\d+)/,'$1').replace('Bar pendants','Bar');
    return f.lights.filter(x=>x.room===l.room).length>1?`${room} · ${name}`:room;
  }
  _render() {
    const e=x=>this._escape(x);
    this.shadowRoot.innerHTML=`
      <style>
        :host {display:block;color:#e7edf8;font-family:var(--primary-font-family,system-ui,sans-serif);--muted:#91a4bd;}
        * {box-sizing:border-box;} button {font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent;}
        button:focus-visible {outline:3px solid #89c8ff;outline-offset:-3px;} button:disabled {cursor:default;}
        .shell {height:var(--overview-height,calc(100dvh - 120px));min-height:320px;padding:12px;background:#080f1b;display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:10px;}
        .shell:fullscreen {width:100vw;height:100dvh;padding:14px;}
        .top {display:flex;align-items:center;gap:16px;min-height:42px;min-width:0;}
        h1 {font-size:20px;letter-spacing:-.035em;margin:0;font-weight:600;white-space:nowrap;}
        .global {font-size:12px;color:#a6c6bb;flex:1;}.global[data-warning="true"] {color:#f4bf87;}
        .fullscreen {background:#172538;color:#bcd1e8;border:1px solid #304158;border-radius:9px;padding:0 12px;min-height:40px;font-size:11px;}
        .grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(2,minmax(0,1fr));gap:10px;min-height:0;}
        .floor {min-width:0;min-height:0;display:grid;grid-template-rows:auto minmax(0,1fr);border:1px solid #293951;border-radius:14px;overflow:hidden;background:#101c2e;}
        .floor-head {display:flex;gap:8px;align-items:center;justify-content:space-between;padding:0 12px;border-bottom:1px solid #25364c;min-height:40px;}
        .floor-link {padding:0;text-align:left;min-height:40px;border:0;color:#e5eefb;background:none;font-size:14px;font-weight:600;}
        .floor-link span {color:#6e92bd;margin-left:6px;}.floor-count {font-size:11px;color:#91a4bd;white-space:nowrap;}
        .floor-count[data-on="true"] {color:#ffd390;}.floor-count[data-warning="true"] {color:#f4bf87;}
        .body {display:grid;grid-template-columns:minmax(0,1fr) minmax(116px,32%);min-height:0;}
        .visual {border:0;position:relative;isolation:isolate;overflow:hidden;min-width:0;min-height:0;background:radial-gradient(ellipse at 50% 48%,#1c2d47,#101c2e 72%);padding:0;}
        .visual img {position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none;user-select:none;}
        .layer {mix-blend-mode:screen;opacity:0;transition:opacity .35s ease;}
        .image-error {position:absolute;bottom:6px;left:6px;right:6px;color:#ffccaa;background:#342019;padding:6px;font-size:11px;}.image-error:empty {display:none;}
        .status {min-width:0;overflow:auto;padding:6px 8px 6px 0;scrollbar-width:thin;}
        .device {display:flex;align-items:center;gap:7px;width:100%;min-height:30px;padding:5px 4px;text-align:left;color:var(--muted);border:0;border-radius:6px;background:none;font-size:11px;line-height:1.2;}
        .device:hover {background:#203149;}.device .dot {flex:0 0 6px;width:6px;height:6px;border-radius:50%;background:#536781;}
        .device[data-state="on"],.device[data-state="open"] {color:#ffda9d;}.device[data-state="on"] .dot,.device[data-state="open"] .dot {background:#ffd18a;box-shadow:0 0 7px #ffc97560;}
        .device[data-state="unavailable"] {color:#e3aa89;}.device[data-state="unavailable"] .dot {background:transparent;border:1px dashed #e3aa89;}
        .device .label {flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}.device .value {font-size:9px;white-space:nowrap;}
        .doors {border-top:1px solid #2b3b50;margin-top:4px;padding-top:4px;}
        .model-note {font-size:11px;color:var(--muted);line-height:1.6;padding:6px 4px;margin:0;}
        .bottom {display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--muted);font-size:10px;min-height:18px;min-width:0;}
        .latest {overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}.hint {white-space:nowrap;}
        @media(max-height:650px) {.shell {padding:6px;gap:6px;}.grid {gap:6px;}.top {min-height:34px;}h1 {font-size:17px;}.fullscreen {min-height:34px;}.floor-head,.floor-link {min-height:32px;}.floor-head {padding:0 9px;}.device {min-height:24px;font-size:10px;padding:3px;}.body {grid-template-columns:minmax(0,1fr) minmax(110px,32%);}.bottom {font-size:9px;}}
        @media(max-width:700px) and (orientation:portrait) {.shell {height:auto;min-height:calc(100dvh - 120px);}.grid {grid-template-columns:minmax(0,1fr);grid-template-rows:none;}.floor {min-height:270px;}.body {min-height:230px;}.top {flex-wrap:wrap;gap:8px;}.global {order:3;flex-basis:100%;}.fullscreen {margin-left:auto;}.hint {display:none;}}
        @media(prefers-reduced-motion:reduce) {.layer {transition:none;}}
      </style>
      <section class="shell" aria-label="Whole-house live overview">
        <header class="top"><h1>${e(this._config.title||'House · All floors')}</h1><div class="global" role="status">Connecting…</div><button class="fullscreen" aria-pressed="false">Full screen</button></header>
        <div class="grid">${this._config.floors.map((f,i)=>`<section class="floor" data-floor="${i}" aria-label="${e(f.title)}">
          <header class="floor-head"><button class="floor-link" data-navigate="${i}" title="Open ${e(f.title)} controls">${e(f.title)}<span aria-hidden="true">↗</span></button><span class="floor-count">${f.model_only?'Model only':'Connecting…'}</span></header>
          <div class="body"><button class="visual" data-navigate="${i}" aria-label="Open ${e(f.title)} detailed floorplan">
            <img class="base" src="${e(f.image)}" alt="${e(f.image_alt||f.title)}" draggable="false">
            ${f.lights.map((l,j)=>`<img class="layer" data-layer="${j}" src="${e(l.image)}" alt="" aria-hidden="true" draggable="false">`).join('')}
            <span class="image-error" role="alert"></span>
          </button><aside class="status" aria-label="${e(f.title)} device status">
            ${f.lights.map((l,j)=>`<button class="device" data-light="${j}" data-state="unavailable"><span class="dot"></span><span class="label">${e(this._label(f,l))}</span><span class="value">—</span></button>`).join('')}
            ${(f.openings||[]).length?`<div class="doors">${f.openings.map((o,j)=>`<button class="device" data-opening="${j}" data-state="unavailable"><span class="dot"></span><span class="label">${e(o.name)}</span><span class="value">—</span></button>`).join('')}</div>`:''}
            ${f.model_only?'<p class="model-note">Laundry · Stairs · Roof<br><br>Reference model<br>No connected devices</p>':''}
          </aside></div></section>`).join('')}</div>
        <footer class="bottom"><span class="latest">Waiting for Home Assistant</span><span class="hint">Tap a floor to open controls · Status dots: gold = on</span></footer>
      </section>`;
    this._tiles=[...this.shadowRoot.querySelectorAll('.floor')].map((node,i)=>({
      node,count:node.querySelector('.floor-count'),
      lights:[...node.querySelectorAll('[data-light]')],layers:[...node.querySelectorAll('.layer')],
      openings:[...node.querySelectorAll('[data-opening]')]
    }));
    this.shadowRoot.querySelectorAll('[data-navigate]').forEach(b=>b.addEventListener('click',()=>this._navigate(Number(b.dataset.navigate))));
    this._tiles.forEach((tile,i)=>{
      tile.lights.forEach((b,j)=>b.addEventListener('click',()=>this._details(this._config.floors[i].lights[j].entity)));
      tile.openings.forEach((b,j)=>b.addEventListener('click',()=>this._details(this._config.floors[i].openings[j].entity)));
      tile.node.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{tile.node.querySelector('.image-error').textContent='Image unavailable — reload to retry';}));
    });
    const fullscreen=this.shadowRoot.querySelector('.fullscreen');
    fullscreen.hidden=!document.fullscreenEnabled;
    fullscreen.addEventListener('click',async()=>{
      try {if(document.fullscreenElement)await document.exitFullscreen();else await this.shadowRoot.querySelector('.shell').requestFullscreen();}
      catch {fullscreen.textContent='Use browser full screen';}
    });
    this._syncFullscreen();
  }
  _update() {
    const connected=Boolean(this._hass)&&this._hass.connected!==false, states=this._hass?.states||{};
    let totalOn=0,totalLights=0,totalUnavailable=0,latest=null;
    const setDevice=(button,entity,label,state)=>{
      button.dataset.state=state;button.querySelector('.value').textContent=state==='unavailable'?'?':state.charAt(0).toUpperCase()+state.slice(1);
      button.setAttribute('aria-label',`${label}: ${state}. View details.`);button.title=`${label} · ${state} · details only`;
      button.disabled=!connected||!states[entity];
    };
    this._config.floors.forEach((f,i)=>{
      const tile=this._tiles[i];let on=0,unavailable=0;
      f.lights.forEach((l,j)=>{
        const s=states[l.entity],valid=connected&&['on','off'].includes(s?.state),active=valid&&s.state==='on';
        on+=Number(active);unavailable+=Number(!valid);
        tile.layers[j].style.opacity=active?'1':'0';
        setDevice(tile.lights[j],l.entity,`${l.room} · ${l.name}`,valid?s.state:'unavailable');
        const time=Date.parse(s?.last_changed);
        if(valid&&Number.isFinite(time)&&(!latest||time>latest.time))latest={time,floor:f.title,light:l,state:s.state};
      });
      (f.openings||[]).forEach((o,j)=>{
        const value=states[o.entity]?.state,valid=connected&&['on','off'].includes(value);
        unavailable+=Number(!valid);setDevice(tile.openings[j],o.entity,o.name,valid?(value==='on'?'open':'closed'):'unavailable');
      });
      tile.count.textContent=f.model_only?'Model only':!connected?'Disconnected':`${on}/${f.lights.length} on${unavailable?' · '+unavailable+' unavailable':''}`;
      tile.count.dataset.on=String(on>0);tile.count.dataset.warning=String(!f.model_only&&(!connected||unavailable>0));
      totalOn+=on;totalLights+=f.lights.length;totalUnavailable+=unavailable;
    });
    const global=this.shadowRoot.querySelector('.global');
    global.textContent=!connected?'Disconnected · states unavailable':`${totalOn} / ${totalLights} lights on${totalUnavailable?' · '+totalUnavailable+' devices unavailable':' · Live'}`;
    global.dataset.warning=String(!connected||totalUnavailable>0);
    this.shadowRoot.querySelector('.latest').textContent=!connected?'Waiting for Home Assistant':latest?`Latest light state · ${latest.floor} · ${latest.light.room} / ${latest.light.name}: ${latest.state} · ${new Date(latest.time).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}`:'No light state timestamps available';
  }
}
if(!customElements.get('house-overview-card'))customElements.define('house-overview-card',HouseOverviewCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'house-overview-card',name:'Whole-house overview',description:'Four floor renders, live lighting and read-only status in one landscape view.'});
