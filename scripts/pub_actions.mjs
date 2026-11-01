import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash,randomUUID} from 'node:crypto';
const R=createRequire(import.meta.url)('./pubrender.cjs');
const ID=/^[a-z0-9]{10}$/;
const json=x=>JSON.stringify(x,null,2)+'\n';
const hash=r=>createHash('sha256').update(r.m+'\n'+r.png).digest('hex');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
function safe(file){
  // Check every existing ancestor, including junctions and dangling links.
  let p=path.resolve(file);
  for(;;){
    try{assert(!fs.lstatSync(p).isSymbolicLink(),'Symbolic link: '+p);}
    catch(e){if(e.code!=='ENOENT')throw e;}
    const next=path.dirname(p);if(next===p)break;p=next;
  }
}
function read(file,fallback){
  safe(file);
  try{return JSON.parse(fs.readFileSync(file,'utf8'));}
  catch(e){if(e.code==='ENOENT'&&fallback!==undefined)return fallback;throw e;}
}
function model(m){
  assert(typeof m==='string'&&m.length<=4000000,'Model size/type');
  const M=JSON.parse(m),result=R.check(M);assert(result.ok,'Model: '+result.error);return M;
}
function record(r){
  assert(r&&r.v===1,'Record version');
  const M=model(r.m);
  assert(typeof r.png==='string'&&r.png.length<=2666668&&/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(r.png),'PNG base64');
  const png=Buffer.from(r.png,'base64');
  assert(png.length>=33&&png.length<=2000000&&png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])),'PNG size/signature');
  assert(png.readUInt32BE(8)===13&&png.toString('ascii',12,16)==='IHDR','PNG IHDR');
  assert(Number.isSafeInteger(r.w)&&r.w>0&&Number.isSafeInteger(r.h)&&r.h>0&&png.readUInt32BE(16)===r.w&&png.readUInt32BE(20)===r.h,'PNG dimensions');
  return {M,png};
}
async function remote(id){
  const base=(process.env.FIREBASE_URL||'https://cypanliketrpg-default-rtdb.firebaseio.com').replace(/\/$/,'');
  const res=await fetch(base+'/pubpages/'+id+'.json',{signal:AbortSignal.timeout(10000)});
  assert(res.ok,'Firebase HTTP '+res.status);return res.json();
}
function manifest(x){
  assert(x&&typeof x==='object'&&!Array.isArray(x),'Manifest');
  for(const [id,v] of Object.entries(x)){
    assert(ID.test(id)&&v&&typeof v==='object'&&/^[a-f0-9]{64}$/.test(v.hash)&&Number.isInteger(v.rv)&&Number.isSafeInteger(v.w)&&v.w>0&&Number.isSafeInteger(v.h)&&v.h>0,'Manifest entry');
  }
  return x;
}
// Stage all files first, then rename. Roll back all targets if a commit fails.
function commit(changes){
  changes=changes.filter(([file,value])=>{
    safe(file);
    if(value===null)return fs.existsSync(file);
    if(!fs.existsSync(file))return true;
    return !fs.readFileSync(file).equals(Buffer.from(value));
  });
  const stages=[],backups=[],created=[];
  try{
    for(const [file,value] of changes){
      safe(file);
      let dir=path.dirname(file),missing=[];
      while(!fs.existsSync(dir)){missing.push(dir);dir=path.dirname(dir);}
      for(const d of missing.reverse()){fs.mkdirSync(d);created.push(d);}
      backups.push([file,fs.existsSync(file)?fs.readFileSync(file):null]);
      if(value!==null){
        const temp=file+'.tmp-'+randomUUID();fs.writeFileSync(temp,value,{flag:'wx'});stages.push([file,temp]);
      }
    }
    for(const [file,value] of changes){
      safe(file);
      if(value===null)fs.unlinkSync(file);
      else fs.renameSync(stages.find(x=>x[0]===file)[1],file);
    }
  }catch(e){
    for(const [file,value] of backups){
      if(value===null){if(fs.existsSync(file))fs.unlinkSync(file);}
      else{const temp=file+'.rollback-'+randomUUID();fs.writeFileSync(temp,value,{flag:'wx'});fs.renameSync(temp,file);}
    }
    throw e;
  }finally{
    for(const [,temp] of stages)if(fs.existsSync(temp))fs.unlinkSync(temp);
    for(const d of created.reverse())if(fs.existsSync(d)&&fs.readdirSync(d).length===0)fs.rmdirSync(d);
  }
}
export async function main(args){
  const op=args.shift();assert(['approve','revoke','sync'].includes(op),'Operation');
  let id=op==='sync'?null:args.shift(),repo=fileURLToPath(new URL('../',import.meta.url)),local;
  let prefix;
  if(op!=='sync'){
    assert(typeof id==='string'&&/^[a-z0-9]{10}(:[0-9a-f]{12})?$/.test(id)&&!/[\r\n]/.test(id),'Invalid id');
    [id,prefix]=id.split(':');
    assert(op!=='revoke'||!prefix,'revoke accepts id only');
  }
  while(args.length){
    const flag=args.shift(),value=args.shift();assert(value&&!value.startsWith('--'),'Option value');
    if(flag==='--repo')repo=value;else if(flag==='--record'&&op==='approve')local=value;else throw Error('Unknown option');
  }
  repo=path.resolve(repo);safe(repo);
  const file=rel=>path.join(repo,rel),approved=manifest(read(file('c/approved.json'),{})),changes=[];
  const put=(rel,value)=>changes.push([file(rel),value]);
  if(op==='approve'){
    const rec=local?read(path.resolve(local)):await remote(id),{M,png}=record(rec);
    const digest=hash(rec);
    assert(!prefix||digest.startsWith(prefix),'確認した版と中身が違います。一覧を読み込み直してください');
    const html=R.webHTML(M,id,rec.w,rec.h);
    put('data/'+id+'.json',json(M));put('c/'+id+'.png',png);put('c/'+id+'.html',html);
    approved[id]={hash:digest,at:new Date().toISOString(),rv:R.VERSION,w:rec.w,h:rec.h};
    put('c/approved.json',json(approved));
  }else if(op==='revoke'){
    if(!Object.hasOwn(approved,id))return;
    for(const rel of ['c/'+id+'.html','c/'+id+'.png','data/'+id+'.json'])put(rel,null);
    delete approved[id];put('c/approved.json',json(approved));
  }else{
    const status={};
    for(const [key,entry] of Object.entries(approved)){
      if(entry.rv!==R.VERSION){
        const M=read(file('data/'+key+'.json')),result=R.check(M);assert(result.ok,'Stored model: '+result.error);
        put('c/'+key+'.html',R.webHTML(M,key,entry.w,entry.h));entry.rv=R.VERSION;
      }
      try{const rec=await remote(key);if(rec===null)status[key]='missing';else{record(rec);status[key]=hash(rec)===entry.hash?'same':'changed';}}
      catch(e){status[key]='unknown';}
    }
    put('c/approved.json',json(approved));put('data/status.json',json(status));
  }
  // Preflight all targets before staging anything.
  changes.forEach(([f])=>{safe(f);if(fs.existsSync(f))assert(fs.statSync(f).isFile(),'Not a file: '+f);});
  commit(changes);
  console.log(op+' OK'+(id?' '+id:''));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main(process.argv.slice(2)).catch(e=>{console.error(e.message);process.exitCode=1;});
}
