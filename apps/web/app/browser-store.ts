"use client";
/** Browser-persistent experiment results; never stores MT5 credentials. */
const DB="tradingquant-results-v1";
const STORE="runs";
const VERSION=1;
function openDb():Promise<IDBDatabase>{
 return new Promise((resolve,reject)=>{
  const request=indexedDB.open(DB,VERSION);
  request.onupgradeneeded=()=>{if(!request.result.objectStoreNames.contains(STORE))request.result.createObjectStore(STORE,{keyPath:"id"})};
  request.onsuccess=()=>resolve(request.result);
  request.onerror=()=>reject(request.error);
 });
}
export async function readExperiments<T extends {id:string}>():Promise<T[]>{
 if(typeof indexedDB==="undefined")return [];
 const db=await openDb();
 try{return await new Promise<T[]>((resolve,reject)=>{
  const tx=db.transaction(STORE,"readonly");
  const request=tx.objectStore(STORE).getAll();
  request.onsuccess=()=>resolve(request.result as T[]);
  request.onerror=()=>reject(request.error);
 });}finally{db.close()}
}
export async function writeExperiments<T extends {id:string}>(runs:T[]):Promise<void>{
 if(typeof indexedDB==="undefined")return;
 const db=await openDb();
 try{await new Promise<void>((resolve,reject)=>{
  const tx=db.transaction(STORE,"readwrite");
  const store=tx.objectStore(STORE);
  store.clear();
  for(const run of runs)store.put(run);
  tx.oncomplete=()=>resolve();
  tx.onerror=()=>reject(tx.error);
  tx.onabort=()=>reject(tx.error);
 });}finally{db.close()}
}
