/* Canned data: challenge prompts, story themes, demo walks. */

export const PROMPTS=['Find something smaller than your thumbnail.','Find something that has been here longer than you.','Find a texture you would want to touch.','Find something that someone left behind.','Find the oldest-looking thing on this street.','Find something that is not green.','Find something that makes a sound when you move it.','Find something that looks almost like a face.'];

export const STORY_THEMES=['Mystery','Cozy','Cheeky','Spooky','Adventure'];

export const seedTrips=()=>[{
  id:1,name:'Walk home from college',date:'Tue 6 Oct',place:'the old bridge',
  items:[
    {id:1,art:'leaf',label:'Crumpled red leaf',desc:'spotted, slightly menacing',note:'Fell right in front of me outside the library.',tilt:-6},
    {id:2,art:'acorn',label:'Acorn, cap askew',desc:'small and very smug',note:'',tilt:5},
    {id:3,art:'candy',label:'Candy wrapper',desc:'sweet evidence of a bad decision',note:'Smelled like strawberries.',tilt:-3},
    {id:4,art:'feather',label:'Grey feather',desc:'dropped by someone in a hurry',note:'',tilt:7}],
  stories:[{id:1,title:'The Case of the Smug Acorn',theme:'mystery',
    text:'Near the old bridge, the evening had a mysterious feeling, and the ground was offering clues. A crumpled red leaf lay where it fell outside the library, spotted and slightly menacing. Beside it, an acorn with its cap askew looked small and very smug, as if it knew exactly who had dropped the strawberry-scented wrapper nearby.\nNobody ever solved the case, but you walked home a little more suspicious of the trees.'}]
},{
  id:2,name:'Sunday market loop',date:'Sun 4 Oct',place:'',
  items:[
    {id:5,art:'pebble',label:'Pocket pebble',desc:'quietly pleased to be chosen',note:'Warm from the sun.',tilt:4},
    {id:6,art:'feather',label:'Grey feather',desc:'dropped by someone in a hurry',note:'',tilt:-8}],
  stories:[]
}];
