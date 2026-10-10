/* Albums list and opening a walk. */
import {$, artHTML, esc, state, tripById} from '../state.js';
import {render} from '../router.js';

export function renderAlbums(){
  const finds=state.trips.reduce((a,t)=>a+t.items.length,0),stories=state.trips.reduce((a,t)=>a+t.stories.length,0);
  $('#app').innerHTML=`<div class="page"><h1>Albums</h1>
    <p class="sub" style="margin-bottom:18px">${state.trips.length} walks, ${finds} finds, ${stories} stories.</p>
    ${state.trips.length?'<div class="albums">'+state.trips.map(t=>`
      <button class="trip" data-trip="${t.id}">
        <div class="row between"><strong>${esc(t.name)}</strong><span class="sub" style="font-size:14px">${esc(t.date)}</span></div>
        <div class="sub" style="font-size:14px">${t.items.length} finds, ${t.stories.length} ${t.stories.length===1?'story':'stories'}</div>
        <div class="strip">${t.items.slice(0,6).map(i=>`<div class="thumb">${artHTML(i)}</div>`).join('')}</div>
      </button>`).join('')+'</div>':`<div class="empty">No walks saved yet. Go collect something.</div>`}</div>`;
  document.querySelectorAll('[data-trip]').forEach(b=>b.onclick=()=>openTripView(+b.dataset.trip));
}

export function openTripView(id){
  state.openTrip=id;state.selected=new Set();state.pendingStory=null;
  state.storyDraft={theme:'',place:tripById(id).place||''};
  state.view='trip';render();$('#app').scrollTop=0;
}
