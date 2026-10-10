import {go, showScreen} from './router.js';
import {$} from './state.js';
import {initCollect} from './views/collect.js';
import {boot} from './views/intro.js';

/* Entry point: wire the navigation, then start the intro. */
document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>go(b.dataset.nav));
$('#about').onclick=()=>showScreen('landing');
initCollect();
boot();
