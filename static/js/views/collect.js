/* Collect page: challenge, shutter, this walk, end walk. */
import * as api from '../api.js';
import {$, esc, state, toast} from '../state.js';
import {PROMPTS} from '../data.js';
import {bindBoxes, boxHTML, closeSheet, sheet} from '../components.js';
import {SAMPLES} from '../art.js';
import {openTripView} from './albums.js';

export function renderCollect(){
  const d=state.draft;
  $('#app').innerHTML=`<div class="page"><div class="two"><section class="cap">
    <h1>Out for a walk?</h1>
    <p class="sub">Snap things you find. Come back for a story.</p>
    <div class="challenge"><p id="challenge">${esc(PROMPTS[d.promptIdx])}</p></div>
    <button class="link" id="stuck">Can't find anything? Give me another idea</button>
    <div class="shutter-wrap">
      <button class="shutter" id="shutter" aria-label="Take a photo" ${state.busy?'disabled':''}><span></span></button>
      <button class="link" id="sample">No camera? Add a sample</button>
    </div>
    <div class="status" id="status" aria-live="polite"></div>
  </section>
  <section class="shelf">
    <div class="row between" style="margin:8px 0 12px"><h2 style="margin:0">This walk</h2><span class="sub">${d.items.length} collected</span></div>
    ${d.items.length?`<div class="grid">${d.items.slice().reverse().map((it,i)=>boxHTML(it,{fresh:i===0&&state.justAdded})).join('')}</div>`
      :`<div class="empty">Nothing yet. Your first find goes in a glass box here.</div>`}
    <div style="margin-top:22px"><button class="btn block" id="end" ${d.items.length?'':'disabled'}>End walk</button></div>
  </section></div></div>`;
  state.justAdded=false;
  $('#stuck').onclick=()=>{d.promptIdx=(d.promptIdx+1)%PROMPTS.length;$('#challenge').textContent=PROMPTS[d.promptIdx]};
  $('#shutter').onclick=()=>$('#file').click();
  $('#sample').onclick=()=>capture({sample:SAMPLES[d.sampleIdx++%SAMPLES.length]});
  $('#end').onclick=openEndSheet;
  bindBoxes(d.items);
}

function openEndSheet(){
  const n=state.draft.items.length;
  const s=sheet(`<h2>Name this walk</h2><p class="sub">${n} ${n===1?'find':'finds'} ready for the album.</p>
    <label class="f" for="tn">Walk name</label><input class="in" id="tn" placeholder="Walk home from college" maxlength="40">
    <label class="f" for="tp">Place (optional)</label><input class="in" id="tp" placeholder="The old bridge" maxlength="40">
    <div style="margin-top:20px"><button class="btn block" id="save">Save to albums</button></div>`);
  s.querySelector('#save').onclick=()=>{
    const t={id:++state.sid,name:s.querySelector('#tn').value.trim()||'Untitled walk',place:s.querySelector('#tp').value.trim(),
      date:new Date().toLocaleDateString('en-GB',{weekday:'short',day:'numeric',month:'short'}),items:state.draft.items,stories:[]};
    state.trips.unshift(t);state.draft={items:[],promptIdx:0,sampleIdx:state.draft.sampleIdx};
    closeSheet();openTripView(t.id);
  };
  setTimeout(()=>s.querySelector('#tn').focus(),50);
}

/* Take a photo (or add a sample): the shutter calls this. All AI work goes through api.snap(). */
async function capture(input){
  if(state.busy)return;state.busy=true;
  const sh=$('#shutter');if(sh)sh.disabled=true;
  const setStatus=m=>{const st=$('#status');if(st&&state.view==='collect')st.textContent=m};
  try{
    const found=await api.snap(input,setStatus);
    state.draft.items.push({id:++state.sid,note:'',tilt:Math.round(Math.random()*14-7),...found});
    state.justAdded=true;
  }catch(err){
    toast(err.message||'That photo did not work out. Try again.');
  }finally{
    state.busy=false;
    if(state.view==='collect')renderCollect();
  }
}

/* Called once from main.js: listens for the camera or file picker. */
export function initCollect(){
  $('#file').addEventListener('change',e=>{
    const f=e.target.files[0];if(!f)return;
    capture({file:f});e.target.value='';
  });
}
