/* App state and small helpers used everywhere. */
import {seedTrips} from './data.js';
import {ART} from './art.js';

export const state={sid:100,
  screen:'loading',view:'collect',theme:'moss',
  draft:{items:[],promptIdx:0,sampleIdx:0},
  trips:seedTrips(),openTrip:null,selected:new Set(),
  storyDraft:{theme:'',place:''},pendingStory:null,busy:false,justAdded:false
};

export const $=s=>document.querySelector(s);

export const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

export const artHTML=it=>it.img?`<img src="${it.img}" alt="">`:ART[it.art];

export const tripById=id=>state.trips.find(t=>t.id===id);

export const cap1=s=>s.charAt(0).toUpperCase()+s.slice(1);

export function toast(msg){const t=$('#toast');t.textContent=msg;t.classList.add('on');clearTimeout(toast.h);toast.h=setTimeout(()=>t.classList.remove('on'),2400);}
