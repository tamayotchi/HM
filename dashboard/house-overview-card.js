/* Whole-house monitor. Read-only: navigation/details only, never device services. */
class HouseOverviewCard extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'});this._zoom=1;
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
    for(const tile of this._tiles||[]) {
      const [x0,y0,x1,y1]=tile.bounds||[0,0,1,1],w=tile.visual.clientWidth,h=tile.visual.clientHeight;
      const size=Math.max(1,Math.min((w-20)/(x1-x0),(h-32)/(y1-y0)))*this._zoom;
      const maxX=Math.max(0,(size*(x1-x0)-w+20)/2),maxY=Math.max(0,(size*(y1-y0)-h+32)/2);
      tile.pan.x=Math.max(-maxX,Math.min(maxX,tile.pan.x));tile.pan.y=Math.max(-maxY,Math.min(maxY,tile.pan.y));
      Object.assign(tile.stage.style,{width:size+'px',height:size+'px',left:(w-size*(x0+x1))/2+tile.pan.x+'px',top:(h-size*(y0+y1))/2+tile.pan.y+'px'});
      tile.visual.dataset.zoomed=String(this._zoom>1);
    }
    const reset=this.shadowRoot.querySelector('[data-zoom="fit"]');if(reset)reset.textContent=this._zoom===1?'Fit':Math.round(this._zoom*100)+'%';
  }
  _imageBounds(tile,img) {
    try {
      const canvas=document.createElement('canvas');canvas.width=canvas.height=256;
      const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0,256,256);
      const pixels=ctx.getImageData(0,0,256,256).data;let x0=256,y0=256,x1=0,y1=0;
      for(let y=0;y<256;y++)for(let x=0;x<256;x++)if(pixels[(y*256+x)*4+3]>8){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x+1);y1=Math.max(y1,y+1);}
      tile.bounds=x1>x0?[x0/256,y0/256,x1/256,y1/256]:[0,0,1,1];
    } catch {tile.bounds=[0,0,1,1];}
    this._fit();
  }
  _setZoom(value) {
    this._zoom=Math.max(1,Math.min(2.2,Math.round(value*10)/10));
    if(this._zoom===1)for(const tile of this._tiles)tile.pan={x:0,y:0};
    this._fit();
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
        * {box-sizing:border-box;} [hidden] {display:none!important;} button {font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent;}
        button:focus-visible {outline:3px solid #89c8ff;outline-offset:-3px;} button:disabled {cursor:default;}
        .shell {height:var(--overview-height,calc(100dvh - 120px));min-height:320px;padding:6px;background:#080f1b;display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:6px;}
        .shell:fullscreen {width:100vw;height:100dvh;padding:6px;}
        .top {display:flex;align-items:center;gap:16px;min-height:42px;min-width:0;}
        h1 {font-size:20px;letter-spacing:-.035em;margin:0;font-weight:600;white-space:nowrap;}
        .global {font-size:12px;color:#a6c6bb;flex:1;}.global[data-warning="true"] {color:#f4bf87;}
        .fullscreen {background:#172538;color:#bcd1e8;border:1px solid #304158;border-radius:9px;padding:0 12px;min-height:40px;font-size:11px;}
        .grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(2,minmax(0,1fr));gap:10px;min-height:0;}
        .floor {position:relative;min-width:0;min-height:0;border:1px solid #293951;border-radius:14px;overflow:hidden;background:#101c2e;}
        .floor-head {position:absolute;z-index:3;top:0;left:0;right:0;display:flex;gap:8px;align-items:center;justify-content:space-between;padding:6px 10px;min-height:40px;background:linear-gradient(#0b1526c9,transparent);pointer-events:none;}
        .floor-head button {pointer-events:auto;}
        .floor-link {padding:5px 8px;text-align:left;min-height:34px;border:1px solid #42597855;border-radius:8px;color:#e5eefb;background:#0b172bce;font-size:15px;font-weight:600;}
        .floor-actions {display:flex;align-items:center;gap:8px;}.status-toggle {min-height:32px;border:1px solid #42597888;border-radius:8px;background:#0b172bdf;color:#c6d6eb;font-size:11px;padding:4px 9px;}
        .overview-zoom {display:flex;gap:3px;}.overview-zoom button {background:#172538;color:#cbdcf0;border:1px solid #304158;border-radius:8px;min-height:36px;min-width:36px;font-size:18px;}.overview-zoom [data-zoom="fit"] {font-size:11px;min-width:42px;}
        .floor-link span {color:#6e92bd;margin-left:6px;}.floor-count {font-size:11px;color:#91a4bd;white-space:nowrap;}
        .floor-count[data-on="true"] {color:#ffd390;}.floor-count[data-warning="true"] {color:#f4bf87;}
        .body {position:absolute;inset:0;}
        .visual {display:block;width:100%;height:100%;border:0;position:relative;isolation:isolate;overflow:hidden;background:radial-gradient(ellipse at 50% 48%,#1c2d47,#101c2e 72%);padding:0;touch-action:pan-y;}
        .visual[data-zoomed="true"] {cursor:grab;touch-action:none;}.visual.dragging {cursor:grabbing;}
        .stage {position:absolute;isolation:isolate;pointer-events:none;}
        .stage img {position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none;user-select:none;}
        .layer {mix-blend-mode:screen;opacity:0;transition:opacity .35s ease;}
        .image-error {position:absolute;bottom:6px;left:6px;right:6px;color:#ffccaa;background:#342019;padding:6px;font-size:11px;}.image-error:empty {display:none;}
        .status {position:absolute;z-index:4;right:8px;top:46px;bottom:8px;width:min(220px,calc(100% - 16px));overflow:auto;padding:10px;scrollbar-width:thin;border:1px solid #506586;border-radius:10px;background:#0e192bf5;box-shadow:0 5px 20px #0007;}
        .activity {position:absolute;bottom:8px;left:10px;max-width:calc(100% - 20px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:5px 8px;border-radius:7px;background:#0a162ac9;color:#a4b5cd;font-size:11px;pointer-events:none;}.activity[data-on="true"] {color:#ffda9d;}
        .device {display:flex;align-items:center;gap:7px;width:100%;min-height:30px;padding:5px 4px;text-align:left;color:var(--muted);border:0;border-radius:6px;background:none;font-size:11px;line-height:1.2;}
        .device:hover {background:#203149;}.device .dot {flex:0 0 6px;width:6px;height:6px;border-radius:50%;background:#536781;}
        .device[data-state="on"],.device[data-state="open"] {color:#ffda9d;}.device[data-state="on"] .dot,.device[data-state="open"] .dot {background:#ffd18a;box-shadow:0 0 7px #ffc97560;}
        .device[data-state="unavailable"] {color:#e3aa89;}.device[data-state="unavailable"] .dot {background:transparent;border:1px dashed #e3aa89;}
        .device .label {flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}.device .value {font-size:9px;white-space:nowrap;}
        .doors {border-top:1px solid #2b3b50;margin-top:4px;padding-top:4px;}
        .model-note {font-size:11px;color:var(--muted);line-height:1.6;padding:6px 4px;margin:0;}
        .bottom {display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--muted);font-size:10px;min-height:18px;min-width:0;}
        .latest {overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}.hint {white-space:nowrap;}
        @media(max-height:650px) {.shell {padding:6px;gap:6px;}.grid {gap:6px;}.top {min-height:34px;}h1 {font-size:17px;}.fullscreen {min-height:34px;}.floor-head,.floor-link {min-height:32px;}.floor-head {padding:0 9px;}.device {min-height:24px;font-size:10px;padding:3px;}.floor-link {font-size:13px;}.floor-head {padding:4px 7px;}.activity {font-size:10px;}.bottom {font-size:9px;}}
        @media(max-width:700px) and (orientation:portrait) {.shell {height:auto;min-height:calc(100dvh - 120px);}.grid {grid-template-columns:minmax(0,1fr);grid-template-rows:none;}.floor {min-height:270px;}.body {min-height:230px;}.top {flex-wrap:wrap;gap:8px;}.global {order:3;flex-basis:100%;}.fullscreen {margin-left:auto;}.hint {display:none;}}
        @media(prefers-reduced-motion:reduce) {.layer {transition:none;}}
      </style>
      <section class="shell" aria-label="Whole-house live overview">
        <header class="top"><h1>${e(this._config.title||'House · All floors')}</h1><div class="global" role="status">Connecting…</div><div class="overview-zoom" aria-label="Render zoom"><button data-zoom="out" aria-label="Zoom out">−</button><button data-zoom="fit" title="Reset zoom and pan">Fit</button><button data-zoom="in" aria-label="Zoom in">+</button></div><button class="fullscreen" aria-pressed="false">Full screen</button></header>
        <div class="grid">${this._config.floors.map((f,i)=>`<section class="floor" data-floor="${i}" aria-label="${e(f.title)}">
          <header class="floor-head"><button class="floor-link" data-navigate="${i}" title="Open ${e(f.title)} controls">${e(f.title)}<span aria-hidden="true">↗</span></button><div class="floor-actions"><span class="floor-count">${f.model_only?'Model only':'Connecting…'}</span><button class="status-toggle" aria-expanded="false" aria-controls="status-${i}">Status</button></div></header>
          <div class="body"><button class="visual" data-navigate="${i}" aria-label="Open ${e(f.title)} detailed floorplan">
            <div class="stage"><img class="base" src="${e(f.image)}" alt="${e(f.image_alt||f.title)}" draggable="false">
            ${f.lights.map((l,j)=>`<img class="layer" data-layer="${j}" src="${e(l.image)}" alt="" aria-hidden="true" draggable="false">`).join('')}
            </div><span class="image-error" role="alert"></span>
          </button><span class="activity"></span><aside class="status" id="status-${i}" hidden aria-label="${e(f.title)} device status">
            ${f.lights.map((l,j)=>`<button class="device" data-light="${j}" data-state="unavailable"><span class="dot"></span><span class="label">${e(this._label(f,l))}</span><span class="value">—</span></button>`).join('')}
            ${(f.openings||[]).length?`<div class="doors">${f.openings.map((o,j)=>`<button class="device" data-opening="${j}" data-state="unavailable"><span class="dot"></span><span class="label">${e(o.name)}</span><span class="value">—</span></button>`).join('')}</div>`:''}
            ${f.model_only?'<p class="model-note">Laundry · Stairs · Roof<br><br>Reference model<br>No connected devices</p>':''}
          </aside></div></section>`).join('')}</div>
        <footer class="bottom"><span class="latest">Waiting for Home Assistant</span><span class="hint">Tap a floor for controls · + to zoom · Drag when zoomed</span></footer>
      </section>`;
    this._tiles=[...this.shadowRoot.querySelectorAll('.floor')].map((node,i)=>({
      node,count:node.querySelector('.floor-count'),visual:node.querySelector('.visual'),stage:node.querySelector('.stage'),pan:{x:0,y:0},
      lights:[...node.querySelectorAll('[data-light]')],layers:[...node.querySelectorAll('.layer')],
      openings:[...node.querySelectorAll('[data-opening]')]
    }));
    this.shadowRoot.querySelectorAll('[data-navigate]').forEach(b=>b.addEventListener('click',()=>{if(b.__dragged){b.__dragged=false;return;}this._navigate(Number(b.dataset.navigate));}));
    this.shadowRoot.querySelector('[data-zoom="in"]').addEventListener('click',()=>this._setZoom(this._zoom+.2));
    this.shadowRoot.querySelector('[data-zoom="out"]').addEventListener('click',()=>this._setZoom(this._zoom-.2));
    this.shadowRoot.querySelector('[data-zoom="fit"]').addEventListener('click',()=>this._setZoom(1));
    this._tiles.forEach((tile,i)=>{
      tile.lights.forEach((b,j)=>b.addEventListener('click',()=>this._details(this._config.floors[i].lights[j].entity)));
      tile.openings.forEach((b,j)=>b.addEventListener('click',()=>this._details(this._config.floors[i].openings[j].entity)));
      tile.node.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{tile.node.querySelector('.image-error').textContent='Image unavailable — reload to retry';}));
      const toggle=tile.node.querySelector('.status-toggle'),status=tile.node.querySelector('.status');
      toggle.addEventListener('click',()=>{status.hidden=!status.hidden;toggle.setAttribute('aria-expanded',String(!status.hidden));});
      tile.node.addEventListener('keydown',ev=>{if(ev.key==='Escape'){status.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();}});
      const base=tile.node.querySelector('.base');base.addEventListener('load',()=>this._imageBounds(tile,base));if(base.complete&&base.naturalWidth)this._imageBounds(tile,base);
      let drag=null;
      tile.visual.addEventListener('pointerdown',ev=>{tile.visual.__dragged=false;if(this._zoom===1||ev.button!==0)return;drag={x:ev.clientX,y:ev.clientY,pan:{...tile.pan}};tile.visual.setPointerCapture(ev.pointerId);tile.visual.classList.add('dragging');});
      tile.visual.addEventListener('pointermove',ev=>{if(drag){const dx=ev.clientX-drag.x,dy=ev.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>5)tile.visual.__dragged=true;tile.pan={x:drag.pan.x+dx,y:drag.pan.y+dy};this._fit();}});
      const stop=()=>{drag=null;tile.visual.classList.remove('dragging');};tile.visual.addEventListener('pointerup',stop);tile.visual.addEventListener('pointercancel',stop);
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
      const activeRooms=f.lights.filter(l=>connected&&states[l.entity]?.state==='on').map(l=>this._label(f,l));
      const doors=(f.openings||[]).map(o=>`${o.name}: ${!connected||!['on','off'].includes(states[o.entity]?.state)?'unavailable':states[o.entity].state==='on'?'open':'closed'}`);
      const activity=tile.node.querySelector('.activity');activity.dataset.on=String(on>0);
      activity.textContent=f.model_only?'Laundry · Stairs · Roof — model only':!connected?'Disconnected — states unavailable':[(activeRooms.length?'On: '+activeRooms.join(', '):unavailable?'Check unavailable devices':'All lights off'),...doors].join(' · ');
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
