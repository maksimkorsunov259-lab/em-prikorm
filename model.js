'use strict';
const PrikormModel=(()=>{
 const localDate=(d=new Date())=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
 const localTime=(d=new Date())=>`${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
 const riskKeys=['severeEczema','eggAllergy','peanutReaction','complex'],readyKeys=['head','sit','coordinate','swallow'];
 const codes=['local','eczema','hives','swelling','vomit','repeatVomit','pallor','lethargy','diarrhea','breathing','voice','collapse','severeLethargy','rapid','throat','severePain','other'];
 const knownFoods=new Set((typeof FOOD_CATALOG!=='undefined'?FOOD_CATALOG:[]).map(f=>f.id));
 function patient(name='Новый пациент',dob=''){return {id:crypto.randomUUID(),name,dob,createdAt:new Date().toISOString(),risks:Object.fromEntries(riskKeys.map(k=>[k,'unknown'])),ready:Object.fromEntries(readyKeys.map(k=>[k,false])),meals:[],symptoms:[],plan:'',doctorFoods:[],observationMode:false,questions:''};}
 function fresh(){const p=patient();return {app:'em-prikorm',schemaVersion:1,activePatientId:p.id,patients:[p]};}
 const fail=()=>{throw new Error('Данные не соответствуют формату резервной копии ЕмПрикорм версии 1. Текущие дневники не заменены.');};
 const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
 const str=(x,max=3000)=>{if(typeof x!=='string'||x.length>max)fail();};
 const bool=x=>{if(typeof x!=='boolean')fail();};
 const id=x=>{str(x,100);if(!/^[a-zA-Z0-9_-]+$/.test(x))fail();};
 const one=(x,allowed)=>{if(!allowed.includes(x))fail();};
 function date(x,empty=false){if(empty&&x==='')return;str(x,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(x)||!Number.isFinite(Date.parse(x+'T12:00:00Z'))||new Date(x+'T12:00:00Z').toISOString().slice(0,10)!==x||x<'1900-01-01'||x>localDate())fail();}
 function time(x){str(x,5);if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(x))fail();}
 function iso(x){str(x,40);if(!/^\d{4}-\d\d-\d\dT/.test(x)||!Number.isFinite(Date.parse(x))||Date.parse(x)>Date.now()+60000)fail();}
 function occurrence(d,t,dob=''){date(d);time(t);if(dob&&d<dob||Date.parse(d+'T'+t)>Date.now()+60000)fail();}
 function safeTree(x,depth=0){if(depth>12)fail();if(typeof x==='string'){str(x,12*1024*1024);return;}if(x===null||typeof x==='boolean')return;if(typeof x==='number'){if(!Number.isFinite(x))fail();return;}if(Array.isArray(x)){if(x.length>40000)fail();x.forEach(v=>safeTree(v,depth+1));return;}if(!obj(x))fail();for(const [k,v]of Object.entries(x)){if(['__proto__','prototype','constructor'].includes(k))fail();safeTree(v,depth+1);}}
 const array=(x,max)=>{if(!Array.isArray(x)||x.length>max)fail();};
 function unique(items,key='id'){const seen=new Set();for(const item of items){id(item[key]);if(seen.has(item[key]))fail();seen.add(item[key]);}}
 function food(id){if(!knownFoods.has(id))fail();}
 function photo(s){if(s===null)return;str(s,12*1024*1024);if(!/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(s))fail();const payload=s.split(',')[1];if(payload.length%4!==0)fail();let bytes;try{bytes=atob(payload.slice(0,32));}catch{fail();}if(s.startsWith('data:image/png')&&!bytes.startsWith('\x89PNG\r\n\x1a\n')||s.startsWith('data:image/jpeg')&&!bytes.startsWith('\xff\xd8\xff')||s.startsWith('data:image/webp')&&!(bytes.startsWith('RIFF')&&bytes.slice(8,12)==='WEBP'))fail();}
 function validate(v){safeTree(v);if(!obj(v)||v.app!=='em-prikorm'||v.schemaVersion!==1)fail();array(v.patients,100);if(!v.patients.length)fail();unique(v.patients);id(v.activePatientId);if(!v.patients.some(p=>p.id===v.activePatientId))fail();
  for(const p of v.patients){str(p.name,80);if(!p.name.trim())fail();date(p.dob,true);iso(p.createdAt);if(!obj(p.risks)||!obj(p.ready))fail();riskKeys.forEach(k=>one(p.risks[k],['unknown','no','yes']));readyKeys.forEach(k=>bool(p.ready[k]));bool(p.observationMode);str(p.plan,3000);str(p.questions,2000);array(p.meals,20000);array(p.symptoms,20000);array(p.doctorFoods,knownFoods.size);unique(p.meals);unique(p.symptoms);unique(p.doctorFoods,'foodId');
   for(const m of p.meals){occurrence(m.date,m.time,p.dob);iso(m.createdAt);iso(m.updatedAt);if(m.updatedAt<m.createdAt)fail();one(m.kind,['eaten','offered','refused','skipped']);bool(m.unknown);array(m.foodIds,knownFoods.size);if(new Set(m.foodIds).size!==m.foodIds.length)fail();m.foodIds.forEach(food);if(m.kind!=='skipped'&&!m.foodIds.length&&!m.unknown)fail();one(m.result,['none','pending','unknown']);if(m.kind!=='eaten'&&m.result!=='unknown')fail();for(const k of ['dish','amount','texture'])str(m[k],300);str(m.note,1500);}
   for(const s of p.symptoms){occurrence(s.date,s.time,p.dob);iso(s.createdAt);iso(s.updatedAt);if(s.updatedAt<s.createdAt)fail();array(s.codes,codes.length);if(!s.codes.length||new Set(s.codes).size!==s.codes.length)fail();s.codes.forEach(c=>one(c,codes));one(s.onset,['unknown','soon','hours','later','unrelated']);if(s.mealId!==null){id(s.mealId);if(!p.meals.some(m=>m.id===s.mealId&&m.kind==='eaten'))fail();}str(s.note,2000);photo(s.photo);}
   for(const d of p.doctorFoods){food(d.foodId);one(d.status,['individual','avoid']);str(d.note,300);if(!d.note.trim())fail();}
  }
  return structuredClone(v);
 }
 return {localDate,localTime,patient,fresh,validate,date,occurrence,riskKeys,photo};
})();
if(typeof module!=='undefined')module.exports=PrikormModel;
