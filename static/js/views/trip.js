/* A walk: specimen grid, story builder, story vault, covers. */
import * as api from '../api.js?v=2';
import {$, esc, state, toast, tripById} from '../state.js';
import {bindBoxes, boxHTML} from '../components.js';
import {STORY_THEMES} from '../data.js';
import {go} from '../router.js';
import {coverBtn, coverHTML} from '../cover.js';
import {refreshVoice, toggleVoice, voiceBtns} from '../voice.js';

export function renderTrip(keep){
  const t=tripById(state.openTrip),sd=state.storyDraft,y=$('#app').scrollTop,n=state.selected.size;
  $('#app').innerHTML=`<div class="page"><div class="two trip-two"><section class="pane-a">
    <div class="row between"><button class="back" id="back">‹ Albums</button><button class="btn ghost sm" id="export">Export photo book</button></div>
    <h1>${esc(t.name)}</h1>
    <p class="sub" style="margin-bottom:18px">${esc(t.date)}${t.place?', '+esc(t.place):''}</p>
    <div class="grid">${t.items.map(i=>boxHTML(i,{pickable:true})).join('')}</div>
  </section><section class="pane-b"><div class="builder">
      <h2>Make a story</h2><p class="sub">Tick the finds to include (${n} chosen).</p>
      <label class="f" for="place">Setting</label><input class="in" id="place" value="${esc(sd.place)}" placeholder="Where does it happen?">
      <label class="f" for="theme">Theme</label><input class="in" id="theme" value="${esc(sd.theme)}" placeholder="Pick one or write your own">
      <div class="chips">${STORY_THEMES.map(x=>`<button class="chip" data-chip="${x}" aria-pressed="${sd.theme===x}">${x}</button>`).join('')}</div>
      <div style="margin-top:18px"><button class="btn block" id="gen" ${n>0&&!state.busy?'':'disabled'}>${state.busy?'Writing…':'Write my story'}</button></div>
      <div id="out">${state.pendingStory?storyHTML(state.pendingStory,true):''}</div>
    </div>
    ${t.stories.length?`<div class="vault" style="margin-top:28px"><h2>Story vault</h2>${t.stories.map(s=>storyHTML(s,false)).join('')}</div>`:''}
  </section></div></div>`;
  if(keep===true)$('#app').scrollTop=y;
  $('#back').onclick=()=>go('albums');
  $('#export').onclick=()=>toast('Photo book export arrives with the backend.');
  $('#place').oninput=e=>sd.place=e.target.value;
  $('#theme').oninput=e=>{sd.theme=e.target.value;document.querySelectorAll('[data-chip]').forEach(c=>c.setAttribute('aria-pressed',c.dataset.chip===sd.theme))};
  document.querySelectorAll('[data-chip]').forEach(c=>c.onclick=()=>{sd.theme=c.dataset.chip;$('#theme').value=sd.theme;
    document.querySelectorAll('[data-chip]').forEach(x=>x.setAttribute('aria-pressed',x===c))});
  $('#gen').onclick=generate;
  bindBoxes(t.items);bindStory();
}

function storyHTML(s,isNew){
  return `<article class="story" data-key="${esc(s.title)}${isNew?'*':''}" data-sid="${s.id||''}">${coverHTML(s)}<h3>${esc(s.title)}</h3>
    ${s.text.split('\n').map(p=>`<p>${esc(p)}</p>`).join('')}
    <div class="row" style="gap:10px;flex-wrap:wrap">${voiceBtns()}${coverBtn(s)}
    ${isNew?`<button class="btn sm" id="keep">Save to vault</button><button class="link" id="redo">Try again</button>`:''}</div></article>`;
}

export function bindStory(){
  document.querySelectorAll('[data-listen]').forEach(b=>b.onclick=()=>toggleVoice(b.closest('.story')));
  refreshVoice();
  document.querySelectorAll('[data-cover]').forEach(b=>b.onclick=()=>makeCover(b.closest('.story')));
  const keep=$('#keep');if(keep)keep.onclick=()=>{
    const t=tripById(state.openTrip),s=state.pendingStory;s.id=++state.sid;t.stories.unshift(s);state.pendingStory=null;renderTrip(true);toast('Saved to the story vault.');
  };
  const redo=$('#redo');if(redo)redo.onclick=generate;
}

async function generate(){
  if(state.busy)return;state.busy=true;renderTrip(true);
  const t=tripById(state.openTrip),sd=state.storyDraft;
  try{
    state.pendingStory=await api.writeStory({
      items:t.items.filter(i=>state.selected.has(i.id)),
      theme:sd.theme.trim(),place:sd.place.trim()
    });
  }catch(err){
    toast(err.message||'The story did not work out. Try again.');
  }
  state.busy=false;
  if(state.view==='trip'){renderTrip(true);const o=$('#out');if(o)o.scrollIntoView({behavior:'smooth',block:'nearest'})}
}

async function makeCover(el){
  const isNew=el.dataset.key.endsWith('*');
  const t=tripById(state.openTrip);
  const s=isNew?state.pendingStory:t.stories.find(x=>String(x.id)===el.dataset.sid);
  if(!s||s._busy)return;
  s._busy=true;renderTrip(true);
  try{
    const storyItems=(s.items&&s.items.length)
      ? s.items
      : (t&&t.items?t.items.filter(i=>(s.labels||[]).includes(i.label)):[]);
    const itemsToUse=(storyItems&&storyItems.length)?storyItems:(t&&t.items?t.items:[]);
    const out=await api.coverImage(s,itemsToUse);
    s.cover=out.cover;s.coverPrompt=out.prompt;
  }catch(err){
    toast(err.message||'The cover did not work out. Try again.');
  }
  s._busy=false;
  if(state.view==='trip')renderTrip(true);
}

