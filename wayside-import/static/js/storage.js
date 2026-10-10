/*
  Browser storage for albums (IndexedDB). NOT WIRED IN YET.

  Plan: on boot, loadTrips() replaces the demo data. After every change, saveTrip(trip).
  Store real Blobs for cutouts (item.cutout), not blob: URLs, because URLs die when the page closes.
  Wrap calls in try/catch and render fine when storage is empty or blocked.
*/
const DB_NAME='wayside',STORE='trips',VERSION=1;

function openDb(){
  return new Promise((ok,fail)=>{
    const r=indexedDB.open(DB_NAME,VERSION);
    r.onupgradeneeded=()=>{r.result.createObjectStore(STORE,{keyPath:'id'})};
    r.onsuccess=()=>ok(r.result);
    r.onerror=()=>fail(r.error);
  });
}
function run(mode,fn){
  return openDb().then(db=>new Promise((ok,fail)=>{
    const tx=db.transaction(STORE,mode);
    const req=fn(tx.objectStore(STORE));
    tx.oncomplete=()=>{db.close();ok(req&&req.result)};
    tx.onerror=tx.onabort=()=>{db.close();fail(tx.error)};
  }));
}

export const loadTrips=()=>run('readonly',s=>s.getAll()).catch(()=>[]);
export const saveTrip=trip=>run('readwrite',s=>s.put(trip));
export const deleteTrip=id=>run('readwrite',s=>s.delete(id));
