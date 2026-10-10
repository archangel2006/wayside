/* Story cover pieces: prompt text, HTML, and the canvas stand-in painter. */
import {esc} from './state.js';
import {ICON} from './icons.js';

export const hash=str=>[...String(str)].reduce((a,c)=>(Math.imul(a,31)+c.charCodeAt(0))>>>0,7);

const COVER_PAL={
  mystery:['#2B2D5B','#6A55B5','#E8C27A'],
  cozy:['#F6D9B8','#D9825F','#7A4B3A'],
  cheeky:['#FFD3E2','#C0446E','#FFE29A'],
  spooky:['#171229','#4B3A7A','#C9B8FF'],
  adventure:['#BFE3D0','#3F7A66','#F2D58A'],
  quiet:['#D5E4EA','#5F8FA0','#F4E3B3']
};

export function coverPrompt(s){
  const l=(s.labels||[]).map(x=>x.toLowerCase());
  return `A soft illustrated cover for a short ${s.theme||'quiet'} story${s.place?', set near '+s.place:''}${l.length?'. Hints of: '+l.join(', '):''}. Gentle colors, simple shapes, no text.`;
}

export function coverHTML(s){
  if(s._busy)return '<div class="cover ph" role="status">Painting your cover. The real server may take up to a minute.</div>';
  if(!s.cover)return '';
  return `<img class="cover" src="${s.cover}" alt="Cover for ${esc(s.title)}"><div class="cover-note">Prototype stand-in image. The real one comes from an open image model, prompted with: ${esc(s.coverPrompt||'')}</div>`;
}

export function coverBtn(s){
  return `<button class="btn ghost sm" data-cover ${s._busy?'disabled':''}><span class="ico">${ICON.image}</span><span class="lbl">${s._busy?'Painting…':s.cover?'New cover':'Make cover'}</span></button>`;
}

export function drawCover(s,seed){
  const W=800,H=600,c=document.createElement('canvas');c.width=W;c.height=H;
  const x=c.getContext('2d');
  let a=seed>>>0;const rnd=()=>{a=(Math.imul(a,1664525)+1013904223)>>>0;return a/4294967296};
  const keys=Object.keys(COVER_PAL);
  const pal=COVER_PAL[s.theme]||COVER_PAL[keys[hash(s.theme||'')%keys.length]];
  const sky=x.createLinearGradient(0,0,0,H);sky.addColorStop(0,pal[0]);sky.addColorStop(1,pal[2]);
  x.fillStyle=sky;x.fillRect(0,0,W,H);
  const sx=150+rnd()*500,sy=110+rnd()*100;
  [110,70,40].forEach((r,i)=>{x.beginPath();x.arc(sx,sy,r,0,7);x.fillStyle='rgba(255,255,255,'+(0.18+i*0.2)+')';x.fill()});
  for(let l=0;l<3;l++){
    const base=320+l*80,amp=30+rnd()*40,steps=4;
    x.beginPath();x.moveTo(0,H);x.lineTo(0,base);
    let px=0;
    for(let i=1;i<=steps;i++){const nx=W*i/steps;x.quadraticCurveTo(px+W/steps/2,base+(rnd()-.5)*amp*2,nx,base+(rnd()-.5)*amp);px=nx}
    x.lineTo(W,H);x.closePath();
    x.fillStyle=pal[1];x.globalAlpha=0.45+l*0.25;x.fill();x.globalAlpha=1;
  }
  const sc=x.createLinearGradient(0,H*0.5,0,H);sc.addColorStop(0,'rgba(0,0,0,0)');sc.addColorStop(1,'rgba(0,0,0,.55)');
  x.fillStyle=sc;x.fillRect(0,H*0.5,W,H*0.5);
  x.fillStyle='#fff';x.font='700 44px Figtree, system-ui, sans-serif';
  const lines=[];let cur='';
  s.title.split(' ').forEach(w=>{const t=cur?cur+' '+w:w;if(x.measureText(t).width>W-100&&cur){lines.push(cur);cur=w}else cur=t});
  lines.push(cur);
  const show=lines.slice(-3);
  show.forEach((ln,i)=>x.fillText(ln,50,H-50-(show.length-1-i)*54));
  return c.toDataURL('image/png');
}
