/* Theme picker, model status, replay intro, reset. */
import {$, state, toast} from '../state.js';
import {THEMES, applyTheme} from '../themes.js';
import {boot} from './intro.js';
import {seedTrips} from '../data.js';

export function renderSettings(){
  $('#app').innerHTML=`<div class="page" style="max-width:760px"><h1>Settings</h1>
    <p class="sub">Make Wayside feel like yours.</p>
    <section class="set-sec"><h2>Theme</h2>
      <div class="swatches" role="group" aria-label="Theme">${THEMES.map(t=>`
        <button class="sw" data-theme-id="${t.id}" aria-pressed="${state.theme===t.id}">
          <span class="dots">${t.c.map(c=>`<i style="background:${c}"></i>`).join('')}</span>${t.name}</button>`).join('')}</div>
    </section>
    <section class="set-sec"><h2>Open models</h2>
      <p class="sub" style="margin-bottom:6px">These are placeholders. The backend is not connected in this prototype.</p>
      <div class="mrow"><div><strong>Cutout</strong><div class="sub">rembg (U2-Net)</div></div><span class="pill">Demo</span></div>
      <div class="mrow"><div><strong>Vision labels</strong><div class="sub">Small vision model, Hugging Face</div></div><span class="pill">Demo</span></div>
      <div class="mrow"><div><strong>Story writer</strong><div class="sub">Small instruct model, Hugging Face</div></div><span class="pill">Demo</span></div>
      <div class="mrow"><div><strong>Cover image</strong><div class="sub">Small image model, Hugging Face</div></div><span class="pill">Demo</span></div>
      <div class="mrow"><div><strong>Voice</strong><div class="sub">Browser voice now, Piper planned</div></div><span class="pill">Browser</span></div>
    </section>
    <section class="set-sec"><h2>Data</h2>
      <div class="row" style="flex-wrap:wrap;gap:12px">
        <button class="btn ghost sm" id="intro">Replay intro</button>
        <button class="btn ghost sm" id="reset">Reset demo data</button>
      </div>
    </section></div>`;
  document.querySelectorAll('[data-theme-id]').forEach(b=>b.onclick=()=>{
    applyTheme(b.dataset.themeId);
    document.querySelectorAll('[data-theme-id]').forEach(x=>x.setAttribute('aria-pressed',x===b));
  });
  $('#intro').onclick=()=>{
    const l=$('#loading');l.hidden=false;l.classList.remove('out');
    l.querySelector('.ld-bar i').style.animation='none';void l.offsetWidth;l.querySelector('.ld-bar i').style.animation='';
    state.screen='loading';boot();
  };
  $('#reset').onclick=()=>{state.trips=seedTrips();state.draft={items:[],promptIdx:0,sampleIdx:0};toast('Demo data restored.')};
}
