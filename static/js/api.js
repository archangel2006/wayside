import {SAMPLES} from './art.js';
import {cap1} from './state.js';

/*
  Everything that talks to "the AI" goes through this file.

  Per-function mock flags allow incremental backend wiring:
  MOCK_CUTOUT = true/false : rembg background removal
  MOCK_LABEL  = true/false : vision model find naming
  MOCK_STORY  = true/false : language model story generation
*/
export const MOCK_CUTOUT = false;
export const MOCK_LABEL = false;
export const MOCK_STORY = false;
export const MOCK_COVER = false;

const TIMEOUT_MS = 90000; // free CPU can be slow, and a sleeping Space needs time to wake

const sleep = ms => new Promise(r => setTimeout(r, ms));
let mockCount = 0;

async function request(path, options){
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try{
    const res = await fetch(path, {...options, signal: ctrl.signal});
    if(res.status === 503) throw new Error('The server is busy. Try again in a moment.');
    if(res.status === 429) throw new Error('Slow down a little, then try again.');
    if(!res.ok) throw new Error('Something went wrong on the server.');
    return res;
  }catch(err){
    if(err.name === 'AbortError') throw new Error('That took too long. The server may be waking up, so try again.');
    if(err instanceof TypeError) throw new Error('Could not reach the server.');
    throw err;
  }finally{
    clearTimeout(timer);
  }
}

function postFile(path, file){
  const body = new FormData();
  body.append('file', file);
  return request(path, {method: 'POST', body});
}

function postJson(path, data){
  return request(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
}

const blobToDataUrl = blob => new Promise((ok, fail) => {
  const r = new FileReader();
  r.onload = () => ok(r.result);
  r.onerror = () => fail(r.error);
  r.readAsDataURL(blob);
});

/* One photo in, one find out: { img | art, label, desc }.
   input is { file } from the camera, or { sample } from the "add a sample" link. */
export async function snap(input, onStatus=()=>{}){
  if(input.sample) return mockSnap(input, onStatus);
  if(!input.file) throw new Error('Pick a photo first.');

  if(MOCK_CUTOUT && MOCK_LABEL) return mockSnap(input, onStatus);

  onStatus('Cutting out the background and naming your find…');

  const cutPromise = MOCK_CUTOUT
    ? Promise.resolve(input.file)
    : postFile('/api/cutout', input.file).then(r => r.blob());

  const labPromise = MOCK_LABEL
    ? (async () => {
        const s = SAMPLES[mockCount++ % SAMPLES.length];
        return {label: s.label, description: s.desc};
      })()
    : postFile('/api/label', input.file).then(r => r.json());

  const [blob, info] = await Promise.all([cutPromise, labPromise]);
  return {img: URL.createObjectURL(blob), label: info.label, desc: info.description};
}

async function mockSnap(input, onStatus){
  onStatus('Cutting out the background…'); await sleep(900);
  onStatus('Naming your find…'); await sleep(900);
  const s = input.sample || SAMPLES[mockCount++ % SAMPLES.length];
  return input.file
    ? {img: URL.createObjectURL(input.file), label: s.label, desc: s.desc}
    : {art: s.art, label: s.label, desc: s.desc};
}

/* Picked finds + theme + place in, a story out: { title, theme, place, labels, text, items }. */
export async function writeStory({items, theme, place}){
  if(MOCK_STORY){
    await sleep(1600);
    return fakeStory(items, theme, place);
  }
  const res = await postJson('/api/story', {
    items: items.map(i => ({label: i.label, description: i.desc, note: i.note})),
    theme,
    place
  });
  const out = await res.json();
  return {
    title: out.title,
    text: out.text,
    theme: (theme||'quiet').toLowerCase(),
    place,
    labels: items.map(i => i.label),
    items: items
  };
}

/* A story in, a cover image out: { cover: "data:image/png;base64,...", prompt: scene }.
   Calls POST /api/cover — Step A: story model writes a visual scene sentence;
   Step B: SD-Turbo paints it. Falls back to canvas collage on any server error. */
export async function coverImage(story, items = []){
  if(MOCK_COVER){
    // Lightweight canvas fallback used while mock mode is on
    const {drawCover, hash, coverPrompt} = await import('./cover.js');
    const seed = ((story.seed||0) + 1) * 7919 + hash(story.title);
    story.seed = (story.seed||0) + 1;
    const cover = await drawCover(story, seed, items.length ? items : (story.items||[]));
    return {cover, prompt: coverPrompt(story)};
  }

  const labels = (story.labels || items.map(i => i.label) || []).slice(0, 4);
  const body = {
    title: story.title || '',
    text: story.text || '',
    theme: story.theme || 'quiet',
    place: story.place || '',
    labels
  };

  const res = await postJson('/api/cover', body);
  const out = await res.json();
  if(!out.image) throw new Error('Cover generation returned no image.');
  const cover = 'data:image/png;base64,' + out.image;
  return {cover, prompt: out.scene || ''};
}

/* Mock story writer. Used while MOCK_STORY is true. */
function fakeStory(items, theme, place){
  const th = (theme || 'quiet').toLowerCase();
  const open = `${place ? 'Near ' + place + ', t' : 'T'}he evening had a ${th} feeling, and the ground was offering clues.`;
  const bits = items.map((it, k) => {
    const l = it.label.toLowerCase(), note = it.note.trim().replace(/\.$/, '');
    const lead = ['', 'Beside it, ', 'Not far off, ', 'Then, '][Math.min(k, 3)];
    const a = note ? `${lead}${l} turned up, ${it.desc}. ${note}.` : `${lead}${l} turned up, ${it.desc}.`;
    return lead ? a : cap1(a);
  });
  const end = `You carried it all home in your pocket and your head, a little more ${th} than before.`;
  return {
    title: items.length ? `The ${cap1(th)} Tale of the ${items[0].label.split(',')[0]}` : 'A short walk',
    theme: th,
    place,
    labels: items.map(i => i.label),
    items: items,
    text: [open, bits.join(' '), end].join('\n')
  };
}

