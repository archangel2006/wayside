/* Story cover pieces: prompt text, HTML, and the scrapbook collage canvas painter. */
import {esc} from './state.js';
import {ICON} from './icons.js';
import {ART} from './art.js';

export const hash=str=>[...String(str)].reduce((a,c)=>(Math.imul(a,31)+c.charCodeAt(0))>>>0,7);

const COVER_PAL={
  mystery:['#1B1936','#3C306E','#D8B066'],
  cozy:['#2D1D18','#8C4730','#F7D6B5'],
  cheeky:['#381628','#8F2E54','#FED285'],
  spooky:['#120F1D','#3E2D68','#B49FF7'],
  adventure:['#132B22','#2E604F','#F4D58D'],
  quiet:['#192832','#416474','#EADAB2']
};

function roundBox(ctx, x, y, w, h, r){
  if(ctx.roundRect){
    ctx.beginPath();
    ctx.roundRect(x,y,w,h,r);
  }else{
    ctx.beginPath();
    ctx.moveTo(x+r,y);
    ctx.lineTo(x+w-r,y);
    ctx.quadraticCurveTo(x+w,y,x+w,y+r);
    ctx.lineTo(x+w,y+h-r);
    ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    ctx.lineTo(x+r,y+h);
    ctx.quadraticCurveTo(x,y+h,x,y+h-r);
    ctx.lineTo(x,y+r);
    ctx.quadraticCurveTo(x,y,x+r,y);
    ctx.closePath();
  }
}

async function loadItemImage(item){
  if(!item)return null;
  let src=item.img;
  if(!src && item.art && ART[item.art]){
    let svgStr=ART[item.art];
    if(!svgStr.includes('xmlns=')){
      svgStr=svgStr.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ');
    }
    if(!svgStr.includes('width=')){
      svgStr=svgStr.replace('<svg ', '<svg width="200" height="200" ');
    }
    src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svgStr);
  }
  if(!src)return null;

  return new Promise(res=>{
    const img=new Image();
    img.crossOrigin='anonymous';
    img.onload=()=>res(img);
    img.onerror=()=>res(null);
    img.src=src;
  });
}

export function coverPrompt(s){
  const l=(s.labels||[]).map(x=>x.toLowerCase());
  return `A soft illustrated cover for a short ${s.theme||'quiet'} story${s.place?', set near '+s.place:''}${l.length?'. Hints of: '+l.join(', '):''}. Gentle colors, simple shapes, no text.`;
}

export function coverHTML(s){
  if(s._busy)return '<div class="cover ph" role="status">Painting your cover…</div>';
  if(!s.cover)return '';
  const note = s.coverPrompt
    ? `<div class="cover-note">Painted from this scene: <em>${esc(s.coverPrompt)}</em></div>`
    : `<div class="cover-note">Cover painted by SD-Turbo from your story's finds.</div>`;
  return `<img class="cover" src="${s.cover}" alt="Cover for ${esc(s.title)}">${note}`;
}

export function coverBtn(s){
  return `<button class="btn ghost sm" data-cover ${s._busy?'disabled':''}><span class="ico">${ICON.image}</span><span class="lbl">${s._busy?'Painting…':s.cover?'New cover':'Make cover'}</span></button>`;
}

export async function drawCover(s,seed,items=[]){
  const W=800,H=600,c=document.createElement('canvas');c.width=W;c.height=H;
  const x=c.getContext('2d');
  let a=seed>>>0;const rnd=()=>{a=(Math.imul(a,1664525)+1013904223)>>>0;return a/4294967296};
  const keys=Object.keys(COVER_PAL);
  const pal=COVER_PAL[s.theme]||COVER_PAL[keys[hash(s.theme||'')%keys.length]];

  // 1. Naturalist journal background
  const bg=x.createLinearGradient(0,0,W,H);
  bg.addColorStop(0,pal[0]);
  bg.addColorStop(1,pal[1]);
  x.fillStyle=bg;x.fillRect(0,0,W,H);

  // Field notebook dotted grid
  x.fillStyle='rgba(255,255,255,0.06)';
  for(let gx=36;gx<W-36;gx+=28){
    for(let gy=36;gy<H-140;gy+=28){
      x.fillRect(gx,gy,1.5,1.5);
    }
  }

  // Double vintage border
  x.strokeStyle='rgba(255,255,255,0.16)';x.lineWidth=1.5;
  roundBox(x,22,22,W-44,H-44,12);x.stroke();
  x.strokeStyle='rgba(255,255,255,0.07)';x.lineWidth=1;
  roundBox(x,28,28,W-56,H-56,8);x.stroke();

  // Top header inscription
  x.fillStyle='rgba(255,255,255,0.5)';
  x.font='600 11px system-ui, -apple-system, sans-serif';
  x.textAlign='left';
  x.fillText('WAYSIDE BOTANICAL & SPECIMEN ARCHIVE',42,46);
  x.textAlign='right';
  x.fillText((s.theme||'FIELD LOG').toUpperCase()+' • EDITION',W-42,46);

  // 2. Load specimen sticker images
  const pool=(items&&items.length?items:(s.items||[])).slice(0,4);
  const loaded=await Promise.all(pool.map(async it=>({it,img:await loadItemImage(it)})));
  const valid=loaded.filter(obj=>obj.img!==null);

  if(valid.length>0){
    // Layout positions according to number of items
    let configs=[];
    if(valid.length===1){
      configs=[{cx:400,cy:230,maxW:340,maxH:260,tilt:(-2+rnd()*4)}];
    }else if(valid.length===2){
      configs=[
        {cx:270,cy:225,maxW:250,maxH:230,tilt:(-7+rnd()*3)},
        {cx:530,cy:220,maxW:250,maxH:230,tilt:(6+rnd()*3)}
      ];
    }else if(valid.length===3){
      configs=[
        {cx:220,cy:210,maxW:210,maxH:200,tilt:(-8+rnd()*3)},
        {cx:580,cy:205,maxW:210,maxH:200,tilt:(7+rnd()*3)},
        {cx:400,cy:245,maxW:230,maxH:220,tilt:(-1+rnd()*2)}
      ];
    }else{
      configs=[
        {cx:190,cy:205,maxW:180,maxH:180,tilt:(-8+rnd()*3)},
        {cx:330,cy:235,maxW:185,maxH:185,tilt:(3+rnd()*2)},
        {cx:470,cy:200,maxW:180,maxH:180,tilt:(-4+rnd()*2)},
        {cx:610,cy:230,maxW:180,maxH:180,tilt:(7+rnd()*3)}
      ];
    }

    // Paint each cutout sticker
    valid.forEach((spec,i)=>{
      const cfg=configs[i];
      const img=spec.img;
      const rad=cfg.tilt*Math.PI/180;
      x.save();
      x.translate(cfg.cx,cfg.cy);
      x.rotate(rad);

      // Realistic 3D sticker drop shadow
      x.shadowColor='rgba(0,0,0,0.38)';
      x.shadowBlur=16;
      x.shadowOffsetY=9;
      x.shadowOffsetX=2;

      const iw=img.naturalWidth||img.width||200;
      const ih=img.naturalHeight||img.height||200;
      const scale=Math.min(cfg.maxW/iw, cfg.maxH/ih);
      const dw=iw*scale;
      const dh=ih*scale;
      x.drawImage(img,-dw/2,-dh/2,dw,dh);

      // Clear shadow for crisp label tag
      x.shadowColor='transparent';

      // Specimen tag below sticker
      const labelText=(spec.it.label||'Specimen').slice(0,24);
      x.font='600 12px Figtree, system-ui, sans-serif';
      const textW=x.measureText(labelText).width;
      const tagW=Math.max(textW+26,76);
      const tagH=22;
      const tagY=dh/2+6;

      // Tag background
      x.save();
      x.shadowColor='rgba(0,0,0,0.22)';
      x.shadowBlur=5;
      x.shadowOffsetY=2;
      x.fillStyle='#FFFDF5';
      roundBox(x,-tagW/2,tagY,tagW,tagH,5);
      x.fill();
      x.strokeStyle='#D8CCA8';
      x.lineWidth=1;
      x.stroke();
      x.restore();

      // Pin pip
      x.fillStyle='#9C8A69';
      x.beginPath();
      x.arc(-tagW/2+7,tagY+tagH/2,2.2,0,Math.PI*2);
      x.fill();

      // Tag text
      x.fillStyle='#363024';
      x.textAlign='center';
      x.textBaseline='middle';
      x.fillText(labelText,4,tagY+tagH/2);

      x.restore();
    });
  }else{
    // Graceful decorative fallback if no cutout images are present
    const sx=150+rnd()*500,sy=110+rnd()*100;
    [110,70,40].forEach((r,i)=>{x.beginPath();x.arc(sx,sy,r,0,7);x.fillStyle='rgba(255,255,255,'+(0.16+i*0.18)+')';x.fill()});
    for(let l=0;l<3;l++){
      const base=290+l*60,amp=24+rnd()*30,steps=4;
      x.beginPath();x.moveTo(0,H-130);x.lineTo(0,base);
      let px=0;
      for(let i=1;i<=steps;i++){const nx=W*i/steps;x.quadraticCurveTo(px+W/steps/2,base+(rnd()-.5)*amp*2,nx,base+(rnd()-.5)*amp);px=nx}
      x.lineTo(W,H-130);x.closePath();
      x.fillStyle=pal[1];x.globalAlpha=0.45+l*0.25;x.fill();x.globalAlpha=1;
    }
  }

  // 3. Frosted title plaque at bottom
  const bx=36,by=430,bw=W-72,bh=135;
  x.save();
  x.shadowColor='rgba(0,0,0,0.35)';
  x.shadowBlur=20;
  x.shadowOffsetY=8;
  x.fillStyle='rgba(16,14,24,0.88)';
  roundBox(x,bx,by,bw,bh,14);
  x.fill();
  x.shadowColor='transparent';

  x.strokeStyle='rgba(255,255,255,0.18)';
  x.lineWidth=1.2;
  x.stroke();

  // Theme tag
  const themeTag=(s.theme||'FIELD NOTE').toUpperCase();
  const placeTag=s.place?(' • '+s.place.toUpperCase()):'';
  x.fillStyle=pal[2]||'#E8C27A';
  x.font='700 11px system-ui, -apple-system, sans-serif';
  x.textAlign='left';
  x.textBaseline='top';
  x.fillText(`✦ ${themeTag}${placeTag}`,bx+24,by+18);

  // Title text with clean wrapping
  x.fillStyle='#FFFFFF';
  x.font='700 26px Figtree, system-ui, sans-serif';
  const words=(s.title||'A Wayside Tale').split(' ');
  const lines=[];
  let cur='';
  words.forEach(w=>{
    const t=cur?cur+' '+w:w;
    if(x.measureText(t).width>bw-48&&cur){lines.push(cur);cur=w;}
    else cur=t;
  });
  if(cur)lines.push(cur);
  const showLines=lines.slice(0,2);
  showLines.forEach((ln,idx)=>{
    x.fillText(ln,bx+24,by+42+idx*32);
  });

  // Stamp footnote
  x.fillStyle='rgba(255,255,255,0.45)';
  x.font='500 12px Figtree, system-ui, sans-serif';
  const noteText=valid.length?`${valid.length} walk specimen${valid.length>1?'s':''} preserved • Field Album`:'Field observation • Wayside Album';
  x.fillText(noteText,bx+24,by+bh-24);
  x.restore();

  return c.toDataURL('image/png');
}
