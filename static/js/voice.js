/* Read a story aloud: listen, pause, resume, stop. */
import {ICON} from './icons.js';
import {toast} from './state.js';

const voice={key:null,state:'idle',u:null};

export function voiceBtns(){
  return `<button class="btn ghost sm" data-listen aria-label="Listen to story"><span class="ico">${ICON.play}</span><span class="lbl">Listen</span></button>`;
}

export function refreshVoice(){
  document.querySelectorAll('.story').forEach(el=>{
    const b=el.querySelector('[data-listen]');if(!b)return;
    const mine=voice.key===el.dataset.key&&voice.state!=='idle';
    const s=mine?voice.state:'idle';
    b.querySelector('.ico').innerHTML=s==='playing'?ICON.pause:ICON.play;
    b.querySelector('.lbl').textContent=s==='playing'?'Pause':s==='paused'?'Resume':'Listen';
    b.setAttribute('aria-label',s==='playing'?'Pause story':s==='paused'?'Resume story':'Listen to story');
  });
}

export function stopVoice(){
  if('speechSynthesis' in window)speechSynthesis.cancel();
  voice.key=null;voice.state='idle';voice.u=null;refreshVoice();
}

export function toggleVoice(el){
  if(!('speechSynthesis' in window))return toast('Voice is not available in this browser.');
  const key=el.dataset.key;
  if(voice.key===key&&voice.state==='playing'){speechSynthesis.pause();voice.state='paused';return refreshVoice()}
  if(voice.key===key&&voice.state==='paused'){speechSynthesis.resume();voice.state='playing';return refreshVoice()}
  speechSynthesis.cancel();
  const text=[...el.querySelectorAll('h3,p')].map(x=>x.textContent).join('. ');
  const u=new SpeechSynthesisUtterance(text);
  const done=()=>{if(voice.u===u){voice.key=null;voice.state='idle';voice.u=null;refreshVoice()}};
  u.onend=done;u.onerror=done;
  voice.key=key;voice.state='playing';voice.u=u;
  speechSynthesis.speak(u);refreshVoice();
}
