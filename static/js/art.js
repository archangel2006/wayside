/* Sample specimen drawings and the logo. Stand-ins for real cutouts. */

export const ART = {
  leaf:`<svg viewBox="0 0 100 100"><path d="M50 7C82 24 90 56 50 93 10 56 18 24 50 7Z" fill="#B8503A"/><path d="M50 14V90M50 40L34 28M50 56L68 42M50 70L33 58" stroke="#7E2F20" stroke-width="2" fill="none" stroke-linecap="round"/><circle cx="40" cy="48" r="3" fill="#7E2F20"/><circle cx="62" cy="62" r="2.5" fill="#7E2F20"/></svg>`,
  acorn:`<svg viewBox="0 0 100 100"><path d="M30 46C30 78 44 92 50 92S70 78 70 46Z" fill="#C79A5B"/><path d="M24 48C24 28 38 20 50 20S76 28 76 48Z" fill="#6E4B2A"/><path d="M50 20V10" stroke="#6E4B2A" stroke-width="5" stroke-linecap="round"/><path d="M34 34l8 8M48 30l10 10M62 34l6 8" stroke="#4E331B" stroke-width="2"/></svg>`,
  candy:`<svg viewBox="0 0 100 100"><path d="M8 34L30 50 8 66Z M92 34L70 50 92 66Z" fill="#F29BB4"/><rect x="28" y="30" width="44" height="40" rx="14" fill="#E8628A"/><path d="M38 38C44 34 56 34 62 38" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" opacity=".7"/></svg>`,
  feather:`<svg viewBox="0 0 100 100"><path d="M78 10C40 14 22 44 24 70L22 92" stroke="#8D8579" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M78 10C52 8 28 28 25 66 54 62 76 44 78 10Z" fill="#D9D2C6"/><path d="M60 30L30 62M66 24L40 56" stroke="#B7AE9F" stroke-width="1.6"/></svg>`,
  pebble:`<svg viewBox="0 0 100 100"><path d="M16 58C14 36 34 22 56 24 80 26 90 44 84 62 78 78 50 84 32 78 22 74 17 68 16 58Z" fill="#8F9A9B"/><path d="M30 40C36 32 48 30 56 32" stroke="#C2CBCB" stroke-width="4" fill="none" stroke-linecap="round"/><circle cx="62" cy="58" r="2" fill="#6F7A7B"/><circle cx="48" cy="64" r="1.6" fill="#6F7A7B"/></svg>`
};

export const LEAF_LOGO=`<svg width="26" height="26" viewBox="0 0 100 100" aria-hidden="true"><path d="M50 7C82 24 90 56 50 93 10 56 18 24 50 7Z" fill="var(--accent)"/><path d="M50 22V86" stroke="var(--paper)" stroke-width="5" stroke-linecap="round"/></svg>`;

export const SAMPLES=[
  {art:'leaf',label:'Crumpled red leaf',desc:'spotted, slightly menacing'},
  {art:'acorn',label:'Acorn, cap askew',desc:'small and very smug'},
  {art:'candy',label:'Candy wrapper',desc:'sweet evidence of a bad decision'},
  {art:'feather',label:'Grey feather',desc:'dropped by someone in a hurry'},
  {art:'pebble',label:'Pocket pebble',desc:'quietly pleased to be chosen'}
];
