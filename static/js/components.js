/* Shared UI: specimen boxes and bottom sheets. */
import {$, artHTML, esc, state, tripById} from './state.js';
import {renderTrip} from './views/trip.js';
import {render} from './router.js';

export function boxHTML(it,o={}){
  return `<div style="position:relative">
    <button class="box ${o.fresh?'pop':''}" data-open="${it.id}" style="--tilt:${it.tilt}deg" aria-label="Open ${esc(it.label)}">
      <div class="art">${artHTML(it)}</div><div class="tag">${esc(it.label)}</div>
    </button>
    ${o.pickable?`<button class="pick" data-pick="${it.id}" aria-pressed="${state.selected.has(it.id)}" aria-label="Include ${esc(it.label)} in story">${state.selected.has(it.id)?'✓':''}</button>`:''}
  </div>`;
}

export function bindBoxes(items){
  document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openSpecimen(items.find(i=>i.id==b.dataset.open)));
  document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=()=>{
    const id=+b.dataset.pick;state.selected.has(id)?state.selected.delete(id):state.selected.add(id);renderTrip(true);
  });
}

export function sheet(html){
  closeSheet();
  const s=document.createElement('div');s.className='scrim';s.id='scrim';
  s.innerHTML=`<div class="sheet" role="dialog" aria-modal="true"><div class="grab"></div>${html}</div>`;
  s.addEventListener('click',e=>{if(e.target===s)closeSheet()});
  $('#shell').appendChild(s);return s;
}

export function closeSheet(){const s=$('#scrim');if(s)s.remove()}

function openSpecimen(it){
  const s=sheet(`<div class="big">${artHTML(it)}</div>
    <h2 style="margin-top:12px">${esc(it.label)}</h2><p class="sub">${esc(it.desc)}</p>
    <label class="f" for="note">Your note</label>
    <textarea class="in" id="note" placeholder="Where was it? What did it smell like?">${esc(it.note)}</textarea>
    <div class="row between" style="margin-top:14px"><button class="danger" id="del">Remove</button><button class="btn" id="done">Save note</button></div>`);
  s.querySelector('#note').oninput=e=>{it.note=e.target.value};
  s.querySelector('#done').onclick=()=>{closeSheet();render()};
  s.querySelector('#del').onclick=()=>{
    const list=state.view==='collect'?state.draft.items:tripById(state.openTrip).items;
    list.splice(list.indexOf(it),1);state.selected.delete(it.id);closeSheet();render();
  };
}
