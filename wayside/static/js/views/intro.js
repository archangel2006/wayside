/* Loading screen and landing page. */
import {THEMES, applyTheme} from '../themes.js';
import {$, state} from '../state.js';
import {ART, LEAF_LOGO} from '../art.js';
import {enterApp, showScreen} from '../router.js';

export function boot(){
  let saved=null;try{saved=localStorage.getItem('wayside-theme')}catch(e){}
  applyTheme(THEMES.some(t=>t.id===saved)?saved:'moss');
  $('#ld-art').innerHTML=ART.leaf;
  const msgs=['Waking the cutout model…','Loading the vision model…','Sharpening the story pen…','Ready.'];
  msgs.forEach((m,i)=>setTimeout(()=>{$('#ld-msg').textContent=m},i*850));
  setTimeout(finishLoading,3200);
  $('#skip').onclick=finishLoading;
}

function finishLoading(){
  if(state.screen!=='loading')return;
  showScreen('landing');
  const l=$('#loading');l.classList.add('out');setTimeout(()=>{l.hidden=true},550);
}

function shelfBox(art,label,tilt){
  return `<div class="box static" style="--tilt:${tilt}deg"><div class="art">${ART[art]}</div><div class="tag">${label}</div></div>`;
}

export function renderLanding(){
  $('#landing').innerHTML=`
  <div class="l-wrap">
    <header class="l-top">
      <div class="brandmark">${LEAF_LOGO}Wayside</div>
      <button class="btn sm" data-enter>Open app</button>
    </header>

    <section class="hero">
      <div>
        <h1>Collect your walk.</h1>
        <p class="lead">Snap the odd little things you pass on the way home. Wayside pins each one in a glass box, then turns your finds into a short story.</p>
        <div class="hero-actions">
          <button class="btn" data-enter>Start a walk</button>
          <button class="btn ghost" id="how-btn">See how it works</button>
        </div>
      </div>
      <div class="hero-shelf" aria-label="Example collection">
        ${shelfBox('leaf','Red leaf',-6)}${shelfBox('acorn','Acorn',5)}${shelfBox('candy','Wrapper',-3)}
        ${shelfBox('feather','Feather',7)}${shelfBox('pebble','Pebble',-4)}
        <div class="box static empty-box"><div class="tag" style="border-style:dashed;color:var(--soft)">Yours next</div></div>
      </div>
    </section>

    <section class="section" id="how">
      <h2>How it works</h2>
      <div class="steps">
        <div class="step"><div class="n">1</div><h3>Walk and snap</h3><p>Take a photo of anything that catches your eye. A challenge on the screen nudges you to look closer.</p></div>
        <div class="step"><div class="n">2</div><h3>Pin it in glass</h3><p>The background is cut away and your find gets a name and a one-line description in its own box.</p></div>
        <div class="step"><div class="n">3</div><h3>Read your story</h3><p>Back home, pick finds, add a theme and a place, and get a short story built from your real walk. Then paint a cover for it.</p></div>
      </div>
    </section>

    <section class="section">
      <h2>Why open models</h2>
      <div class="why">
        <div><h3>Open models only</h3><p>Cutouts, labels and stories come from open-weight models. No closed AI service sits behind it.</p></div>
        <div><h3>Albums stay with you</h3><p>Your walks and stories are saved in your own browser, not in a server database.</p></div>
        <div><h3>Free to run</h3><p>Small models on free hosting. No API keys and no cost per photo.</p></div>
        <div><h3>Swap the models</h3><p>A model is a setting, so a better one can replace a small one.</p></div>
      </div>
    </section>

    <section class="section">
      <h2>What is under the hood</h2>
      <p class="sub" style="max-width:56ch">Every smart step uses an open model from the Hugging Face Hub. Photos are processed on the server and then discarded. The page you are looking at is a prototype with stand-in answers.</p>
      <div class="stack" style="margin-top:18px">
        <span class="chip">rembg for cutouts</span><span class="chip">A small vision model for labels</span>
        <span class="chip">A small language model for stories</span><span class="chip">A small image model for covers</span><span class="chip">FastAPI on Hugging Face Spaces</span><span class="chip">Piper voice, planned</span>
      </div>
    </section>

    <section class="cta">
      <h2>Your walk home is a collection.</h2>
      <button class="btn" data-enter>Start a walk</button>
    </section>
    <footer class="foot">Built for the Hacktoberfest Open-Source AI Challenge, theme Touch Grass.</footer>
  </div>`;
  document.querySelectorAll('[data-enter]').forEach(b=>b.onclick=()=>enterApp('collect'));
  $('#how-btn').onclick=()=>$('#how').scrollIntoView({behavior:'smooth'});
}
