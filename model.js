'use strict';
const PrikormModel=(()=>{
 const localDate=(d=new Date())=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
 const localTime=(d=new Date())=>`${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
 const riskKeys=['severeEczema','eggAllergy','milkAllergy','peanutAllergy','peanutReaction','complex'],readyKeys=['head','sit','coordinate','swallow'];
 const codes=['local','eczema','hives','swelling','vomit','repeatVomit','pallor','lethargy','diarrhea','breathing','voice','collapse','severeLethargy','rapid','throat','severePain','other'];
 const onsetChoices=Object.freeze({"m0_15": "Во время еды или в первые 15 минут", "m15_60": "Через 15–60 минут", "h1_2": "Через 1–2 часа", "h2_4": "Через 2–4 часа", "h4_8": "Через 4–8 часов", "h8_24": "Через 8–24 часа", "d1_3": "Через 1–3 дня", "after3d": "Позже чем через 3 дня", "unknown": "Не могу определить время", "unrelated": "Не связываю симптом с приёмом пищи"});
 const legacyOnset=Object.freeze({"gradual": "Симптомы развивались постепенно при регулярном употреблении продукта", "soon": "Во время еды или вскоре после неё", "hours": "Через несколько часов", "later": "Позже / на следующий день"});
 const knownFoods=new Set((typeof FOOD_CATALOG!=='undefined'?FOOD_CATALOG:[]).map(f=>f.id));
 function patient(name='Новый пациент',dob=''){return {id:crypto.randomUUID(),name,dob,createdAt:new Date().toISOString(),risks:Object.fromEntries(riskKeys.map(k=>[k,'unknown'])),ready:Object.fromEntries(readyKeys.map(k=>[k,false])),meals:[],symptoms:[],plan:'',doctorFoods:[],foodReviews:[],observationMode:false,questions:''};}
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

 // A clinician clarification applies only to the recorded versions of these events,
 // for this food and this patient. New or edited events require a fresh assessment.
 function relatedSymptoms(p,foodId){const ids=new Set(p.meals.filter(m=>m.kind==='eaten'&&m.foodIds.includes(foodId)).map(m=>m.id));return p.symptoms.filter(s=>ids.has(s.mealId));}
 function reviewSnapshot(p,s){const m=p.meals.find(m=>m.id===s.mealId);return {id:s.id,updatedAt:s.updatedAt,mealId:m.id,mealUpdatedAt:m.updatedAt};}
 function unresolvedFoodSymptoms(p,foodId){const review=p.foodReviews?.find(r=>r.foodId===foodId);return relatedSymptoms(p,foodId).filter(s=>{const stamp=reviewSnapshot(p,s);return !review?.symptoms.some(v=>Object.keys(stamp).every(k=>stamp[k]===v[k]));});}
 function foodStatus(p,f){
  const rows=p.meals.filter(m=>m.kind==='eaten'&&m.foodIds.includes(f.id));
  if(p.doctorFoods.some(d=>d.foodId===f.id&&d.status==='avoid'))return {label:'Ограничение из плана врача',tone:'red',symbol:'!'};
  if(unresolvedFoodSymptoms(p,f.id).length)return {label:'Есть связанные симптомы · причину уточняют',tone:'red',symbol:'!'};
  if(f.allergens.includes('egg')&&p.risks.eggAllergy==='yes'||f.allergens.includes('milk')&&p.risks.milkAllergy==='yes'||f.allergens.includes('peanut')&&p.risks.peanutAllergy==='yes')return {label:'В профиле указана аллергия · нужен план врача',tone:'red',symbol:'!'};
  if(!rows.length)return {label:p.meals.some(m=>m.foodIds.includes(f.id))?'Предлагали · употребление не отмечено':'Употребление не записано',tone:'neutral',symbol:'·'};
  if(rows.some(m=>m.result!=='none'))return {label:'Наблюдение / результат не уточнён',tone:'orange',symbol:'◌'};
  if(relatedSymptoms(p,f.id).length)return {label:'Ел · связь прежних симптомов с продуктом исключена врачом',tone:'green',symbol:'✓'};
  return {label:'Ел · по записям без симптомов',tone:'green',symbol:'✓'};
 }
 function validate(v){safeTree(v);if(!obj(v)||v.app!=='em-prikorm'||v.schemaVersion!==1)fail();array(v.patients,100);if(!v.patients.length)fail();unique(v.patients);id(v.activePatientId);if(!v.patients.some(p=>p.id===v.activePatientId))fail();
  for(const p of v.patients){str(p.name,80);if(!p.name.trim())fail();date(p.dob,true);iso(p.createdAt);if(!obj(p.risks)||!obj(p.ready))fail();riskKeys.forEach(k=>{if(['milkAllergy','peanutAllergy'].includes(k)&&!Object.hasOwn(p.risks,k))return;one(p.risks[k],['unknown','no','yes']);});readyKeys.forEach(k=>bool(p.ready[k]));bool(p.observationMode);str(p.plan,3000);str(p.questions,2000);array(p.meals,20000);array(p.symptoms,20000);array(p.doctorFoods,knownFoods.size);unique(p.meals);unique(p.symptoms);unique(p.doctorFoods,'foodId');
   for(const m of p.meals){occurrence(m.date,m.time,p.dob);iso(m.createdAt);iso(m.updatedAt);if(m.updatedAt<m.createdAt)fail();one(m.kind,['eaten','offered','refused','skipped']);bool(m.unknown);array(m.foodIds,knownFoods.size);if(new Set(m.foodIds).size!==m.foodIds.length)fail();m.foodIds.forEach(food);if(m.kind!=='skipped'&&!m.foodIds.length&&!m.unknown)fail();one(m.result,['none','pending','unknown']);if(m.kind!=='eaten'&&m.result!=='unknown')fail();for(const k of ['dish','amount','texture'])str(m[k],300);str(m.note,1500);}
   for(const s of p.symptoms){occurrence(s.date,s.time,p.dob);iso(s.createdAt);iso(s.updatedAt);if(s.updatedAt<s.createdAt)fail();array(s.codes,codes.length);if(!s.codes.length||new Set(s.codes).size!==s.codes.length)fail();s.codes.forEach(c=>one(c,codes));one(s.onset,[...Object.keys(onsetChoices),...Object.keys(legacyOnset)]);if(s.mealId!==null){id(s.mealId);if(!p.meals.some(m=>m.id===s.mealId&&m.kind==='eaten'))fail();}str(s.note,2000);photo(s.photo);}
   if(Object.hasOwn(p,'foodReviews')){array(p.foodReviews,knownFoods.size);unique(p.foodReviews,'foodId');for(const r of p.foodReviews){food(r.foodId);date(r.date);if(p.dob&&r.date<p.dob)fail();str(r.note,1000);if(!r.note.trim())fail();array(r.symptoms,20000);if(!r.symptoms.length)fail();unique(r.symptoms);for(const v of r.symptoms){id(v.mealId);iso(v.updatedAt);iso(v.mealUpdatedAt);}}}
   for(const d of p.doctorFoods){food(d.foodId);one(d.status,['individual','avoid']);str(d.note,300);if(!d.note.trim())fail();}
  }
  const copy=structuredClone(v);for(const p of copy.patients){for(const key of ['milkAllergy','peanutAllergy'])if(!Object.hasOwn(p.risks,key))p.risks[key]='unknown';if(!Object.hasOwn(p,'foodReviews'))p.foodReviews=[];}return copy;
 }
 return {onsetChoices,legacyOnset,localDate,localTime,patient,fresh,validate,date,occurrence,riskKeys,photo,relatedSymptoms,reviewSnapshot,unresolvedFoodSymptoms,foodStatus};
})();
if(typeof module!=='undefined')module.exports=PrikormModel;
