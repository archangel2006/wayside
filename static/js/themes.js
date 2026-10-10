/* The six color themes (CSS lives in css/themes.css) and how to apply one. */
import {$, state} from './state.js';
import {LEAF_LOGO} from './art.js';

export const THEMES=[
  {id:'moss',name:'Moss',c:['#3F7A66','#EEF3F0','#1E2B2C']},
  {id:'tide',name:'Tide',c:['#2F6FA8','#EAF2F7','#18283A']},
  {id:'dusk',name:'Dusk',c:['#6A55B5','#F0EEF7','#251F3A']},
  {id:'blossom',name:'Blossom',c:['#C0446E','#F9EEF1','#3A1F2A']},
  {id:'honey',name:'Honey',c:['#9C620F','#F8F3E4','#33290F']},
  {id:'night',name:'Night',c:['#5DB894','#12181B','#E6EEEC']}
];

export function applyTheme(id){
  state.theme=id;document.documentElement.dataset.theme=id;
  try{localStorage.setItem('wayside-theme',id)}catch(e){}
  $('#brand').innerHTML=LEAF_LOGO+'Wayside';
}
