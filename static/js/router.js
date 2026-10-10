/* Which screen and page is showing. */
import {$, state} from './state.js';
import {stopVoice} from './voice.js';
import {renderCollect} from './views/collect.js';
import {renderAlbums} from './views/albums.js';
import {renderTrip} from './views/trip.js';
import {renderStories} from './views/stories.js';
import {renderSettings} from './views/settings.js';
import {renderLanding} from './views/intro.js';

export function render(){
  if(state.lastView!==state.view){stopVoice();state.lastView=state.view}
  const tab=state.view==='trip'?'albums':state.view;
  document.querySelectorAll('[data-nav]').forEach(b=>b.setAttribute('aria-current',b.dataset.nav===tab));
  ({collect:renderCollect,albums:renderAlbums,trip:renderTrip,stories:renderStories,settings:renderSettings})[state.view]();
}

export function go(v){state.view=v;render();$('#app').scrollTop=0}

export function showScreen(name){
  stopVoice();
  state.screen=name;
  $('#landing').hidden=name!=='landing';
  $('#shell').hidden=name!=='app';
  if(name==='landing'){renderLanding();$('#landing').scrollTop=0}
  if(name==='app')render();
}

export function enterApp(view){state.view=view||'collect';showScreen('app')}
