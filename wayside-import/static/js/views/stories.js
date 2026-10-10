/* Every story across all walks. */
import {$, cap1, esc, state} from '../state.js';
import {voiceBtns} from '../voice.js';
import {openTripView} from './albums.js';
import {bindStory} from './trip.js';

export function renderStories(){
  const all=state.trips.flatMap(t=>t.stories.map(s=>({s,t})));
  $('#app').innerHTML=`<div class="page"><h1>Stories</h1>
    <p class="sub" style="margin-bottom:18px">Everything you have written, across all walks.</p>
    ${all.length?'<div class="albums wide">'+all.map(({s,t})=>`
      <article class="story" data-key="${esc(s.title)}">${s.cover?`<img class="cover" src="${s.cover}" alt="Cover for ${esc(s.title)}">`:''}<div class="row" style="margin-bottom:8px;flex-wrap:wrap"><span class="pill">${esc(cap1(s.theme||'story'))}</span><span class="sub" style="font-size:14px">From ${esc(t.name)}</span></div>
        <h3>${esc(s.title)}</h3>${s.text.split('\n').map(p=>`<p>${esc(p)}</p>`).join('')}
        <div class="row" style="gap:10px;flex-wrap:wrap">${voiceBtns()}<button class="link" data-trip="${t.id}">Open walk</button></div>
      </article>`).join('')+'</div>'
      :`<div class="empty">No stories yet. Open a walk, tick a few finds and write one.</div>`}</div>`;
  document.querySelectorAll('[data-trip]').forEach(b=>b.onclick=()=>openTripView(+b.dataset.trip));
  bindStory();
}
