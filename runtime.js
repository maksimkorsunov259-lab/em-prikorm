'use strict';
let collection,loading=true,storageFailed=false,canExport=false,rawRecovery=null,lastQueued='',saveQueue=Promise.resolve(),pendingWrites=0,pendingImport=null,installPrompt=null,registration=null,offlineReady=false,offlineError='',photoLoadId=0,photoReading=false;
let importSequence=0;
let installBusy=false,installStatus='';
const isStandalone=()=>window.matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
let updateChecking=false,updateCheckStatus='';
let updateRequested=false,updatePreparing=false,reloadReady=false,reloading=false;
const patientMeta=q=>q.dob?new Date(q.dob+'T12:00:00').toLocaleDateString('ru-RU')+' · '+ageMonths(q.dob)+' полных мес.':'Дата рождения не указана';
function validOccurrence(date,time){try{PrikormModel.occurrence(date,time,p.dob);return true;}catch{return false;}}
function currentCollection(){collection.patients=profiles;collection.activePatientId=p.id;return collection;}
function lockEditing(){document.body.classList.add('storage-readonly');$('#screen').querySelectorAll('input,select,textarea,button[type=submit]').forEach(el=>el.disabled=true);}
function showStorageError(error){storageFailed=true;$('#patient-select').disabled=true;$('#storage-status').textContent='Изменения не сохранены';$('#storage-error').hidden=false;$('#storage-error').innerHTML=`<strong>Не удалось сохранить или прочитать дневник.</strong><p>${esc(error.message||error)}</p><p>${canExport?'Скачайте текущую копию перед перезагрузкой. Редактирование остановлено, чтобы не перезаписать данные.':'Существующие данные не перезаписаны. Не очищайте данные сайта. Восстановите доступ к хранилищу и перезагрузите страницу.'}</p>${canExport?'<button class="wide" data-runtime="export">Скачать текущую копию</button>':''}<button class="wide" data-runtime="reload">Перезагрузить</button><button class="wide" data-go="help">План помощи при реакции</button>`;lockEditing();refreshUpdateUI();}
function persist(){if(loading||storageFailed)return saveQueue;let snapshot,key;try{snapshot=PrikormModel.validate(currentCollection());key=JSON.stringify(snapshot);}catch(e){showStorageError(e);return saveQueue;}if(key===lastQueued)return saveQueue;lastQueued=key;pendingWrites++;$('#storage-status').textContent='Сохраняем на устройстве…';saveQueue=saveQueue.then(async()=>{try{if(!storageFailed)await DiaryStore.write(snapshot);}catch(e){showStorageError(e);}finally{pendingWrites--;if(!storageFailed&&!pendingWrites)$('#storage-status').textContent='Сохранено на этом устройстве';}});return saveQueue;}
const baseToast=toast;
toast=async t=>{await saveQueue;if(!storageFailed)baseToast(t);};
const baseRender=render;
render=function(next=view){if(next==='help'){helpOverlay.open();return;}if(next==='about'){aboutOverlay.open();return;}if(!p)return;aboutOverlay.close(false);if(next!==view)helpOverlay.close(false);TODAY=PrikormModel.localDate();photoLoadId++;photoReading=false;baseRender(next);bindRuntime();if(storageFailed)lockEditing();else persist();refreshUpdateUI();};
let patientSwitchBusy=false;
function renderPatientSelect(){const select=$('#patient-select');select.replaceChildren(...profiles.map(q=>new Option(q.name+(q.dob?' · '+new Date(q.dob+'T12:00:00').toLocaleDateString('ru-RU',{day:'numeric',month:'long',year:'numeric'}):''),q.id)));select.value=p.id;select.disabled=loading||storageFailed||patientSwitchBusy;}
async function selectPatient(id){if(loading||storageFailed||patientSwitchBusy||id===p.id)return;patientSwitchBusy=true;$('#screen').inert=true;renderPatientSelect();try{await saveQueue;if(storageFailed||!profiles.some(q=>q.id===id))return;collection.activePatientId=id;resetSelection();render('today');}finally{patientSwitchBusy=false;$('#screen').inert=false;renderPatientSelect();}}
$('#patient-select').addEventListener('change',async e=>{const id=e.target.value;e.target.value=p.id;if(loading||storageFailed||patientSwitchBusy||id===p.id)return;if((dirty||photoReading)&&!confirm('Форма ещё не сохранена. Перейти без сохранения?'))return;await selectPatient(id);});
function resetSelection(){active=profiles.findIndex(x=>x.id===collection.activePatientId);p=profiles[active];editing=null;photoDraft=null;photoInclude=false;photoReading=false;photoLoadId++;preselectedFood=null;selectedDay=TODAY;catalogFilter='all';catalogGroup='all';search='';foodOrigin='foods';pendingImport=null;}
function profileForm(create=false){const q=create?PrikormModel.patient('', ''):p;return back(create?'patients':'today','Назад')+header('Профиль ребёнка',create?'Добавить пациента':'Чтобы помнить<br>важный контекст.','У каждого пациента — отдельные записи, наблюдения и план врача.')+`<form id="patient-form" data-create="${create}">${input('Имя или удобное обращение','name',q.name,'text','required maxlength="80"')}${input('Дата рождения (необязательно)','dob',q.dob,'date','min="1900-01-01" max="'+TODAY+'"')}${Object.entries({severeEczema:'Тяжёлый атопический дерматит по оценке врача',eggAllergy:'Установленная аллергия на яйцо',milkAllergy:'Установленная аллергия на белки коровьего молока',peanutAllergy:'Установленная аллергия на арахис',peanutReaction:'Предыдущая реакция на арахис (независимо от установленного диагноза)',complex:'Недоношенность, трудности с глотанием/ростом, лечебное или энтеральное питание'}).map(([k,t])=>select(t,k,[['unknown','Не уточнено'],['no','Не отмечено'],['yes','Да']],q.risks[k])).join('')}<p class="small">Анкета не диагностирует аллергию и не выдаёт допуск к пробам.</p><p class="error" id="patient-error" role="alert"></p><button class="primary wide" type="submit">${create?'Создать отдельный дневник':'Сохранить профиль'}</button></form>`;}
screens.profile=()=>profileForm();screens.newPatient=()=>profileForm(true);
screens.patients=()=>back('today','Сегодня')+header('Пациенты','Чей дневник<br>открываем?')+profiles.map((q,i)=>`<section class="card patient-card"><h3>${esc(q.name)}</h3><p class="small">${esc(patientMeta(q))} · записей о еде: ${q.meals.length}</p><button class="wide" data-patient="${i}" ${i===active?'disabled':''}>${i===active?'Выбран сейчас':'Выбрать пациента'}</button></section>`).join('')+`<button class="primary wide" data-go="newPatient" ${profiles.length>=100?'disabled':''}>Добавить пациента</button><button class="link wide" data-go="settings">Копия всех дневников</button>`;
screens.settings=()=>back('more','Памятка')+header('На вашем устройстве','Данные и установка')+`<div class="family-data" data-app-name="ЕмПрикорм">
<section class="family-data-card" data-family-section="device"><h3>Ваш дневник на этом устройстве</h3><p>Ваши записи хранятся только на вашем устройстве — в браузере или установленном приложении. Мы не отправляем их на серверы и не передаём автору приложения. Регистрация не нужна, облачной синхронизации нет. Чтобы перенести дневники на другое устройство, сохраните резервную копию.</p><p data-family-count></p><p data-family-save role="status">Проверяем сохранение…</p><div class="family-data-patient"><label>Пациент, чей дневник нужно удалить<select data-family-delete-patient aria-label="Пациент, чей дневник нужно удалить"></select></label><p class="family-data-note">Удалятся профиль и записи только выбранного пациента. Дневники остальных останутся. Перед удалением рекомендуем скачать резервную копию.</p><button type="button" data-runtime="delete-patient" class="family-data-button">Удалить дневник пациента</button></div></section>
<section class="family-data-card" data-family-section="install"><h3>Установка приложения</h3><p data-family-install-help></p><p class="family-data-note" data-family-install-android><strong>Android:</strong> откройте приложение в Chrome → меню ⋮ → «Установить приложение» или «Добавить на главный экран».</p><p class="family-data-note" data-family-install-ios><strong>iPhone и iPad:</strong> откройте приложение в Safari → «Поделиться» → «На экран Домой» → «Добавить».</p><button type="button" data-runtime="install" class="family-data-button family-data-primary" hidden>Установить приложение</button><p id="install-status" class="family-data-note" role="status"></p></section>
<section class="family-data-card" data-family-section="update"><h3>Обновление и работа без интернета</h3><p>ЕмПрикорм · версия <span id="version">1.0.32</span></p><p id="offline-status" role="status">Подготовка работы без интернета…</p><p class="family-data-note">Для первого открытия нужен интернет. После подготовки дневник доступен без сети; внешние ссылки требуют подключения.</p><button type="button" data-runtime="check-update" class="family-data-button">Проверить обновления</button><button type="button" data-runtime="update" class="family-data-button family-data-primary" hidden>Обновить приложение</button><p id="update-check-status" role="status"></p><p data-family-update-recovery hidden><a href="./update.html">Помощь с обновлением</a></p></section>
<section class="family-data-card" data-family-section="backup"><h3>Резервная копия и перенос данных</h3><p>Копия содержит дневники всех пациентов. Сохраните её перед сменой устройства, переустановкой приложения или очисткой данных браузера.</p><button type="button" data-runtime="export" class="family-data-button family-data-primary">Скачать резервную копию</button><label class="family-data-file">Восстановить из файла<input type="file" id="import-file" accept=".json,application/json"></label><div id="import-preview" class="family-data-preview"></div><p id="import-error" role="status"></p><p class="family-data-note">Файл содержит медицинские сведения без шифрования. Храните его в доступном только вам месте. Подходит только копия приложения «ЕмПрикорм».</p></section>

</div>`;
function offlineStatus(){return offlineReady?'Приложение подготовлено для работы без сети.':offlineError||'Подготовка работы без сети…';}
const originalMealCard=mealCard;
mealCard=(m,edit=true)=>originalMealCard(m,edit).replace('</article>',`${edit?'<button class="link danger-link record-remove" data-remove-meal="'+m.id+'">Удалить</button>':''}</article>`);
const originalSymptomCard=symptomCard;
symptomCard=(s,edit=true)=>originalSymptomCard(s,edit).replace('</article>',`${edit?'<button class="link danger-link record-remove" data-remove-symptom="'+s.id+'">Удалить</button>':''}</article>`);
async function exportBackup(){if(!canExport)return;await saveQueue;const data=rawRecovery||currentCollection();download('em-prikorm-'+(storageFailed?'recovery-':'backup-')+PrikormModel.localDate()+'.json',JSON.stringify(data,null,2),'application/json');baseToast(storageFailed?'Копия текущих данных подготовлена. Ошибка хранилища не устранена.':'Резервная копия всех пациентов подготовлена.');}
function bindRuntime(){FamilyData.refresh(profiles.length,p.name,profiles.map(p=>({id:p.id,label:p.name+(p.dob?' · '+new Date(p.dob+'T12:00:00').toLocaleDateString('ru-RU'):'')})),collection.activePatientId);FamilyData.syncStorage?.();refreshInstallUI();if($('#offline-status'))$('#offline-status').textContent=offlineStatus();
 $('#patient-form [name=name]')?.setAttribute('maxlength','80');
 $('#patient-form')?.addEventListener('submit',e=>{e.preventDefault();if(storageFailed)return;const f=new FormData(e.target),name=String(f.get('name')).trim(),dob=String(f.get('dob')),create=e.target.dataset.create==='true';if(!name){$('#patient-error').textContent='Укажите имя или удобное обращение.';return;}try{PrikormModel.date(dob,true);}catch{$('#patient-error').textContent='Проверьте дату рождения.';return;}if(!create&&dob&&[...p.meals,...p.symptoms].some(r=>r.date<dob)){$('#patient-error').textContent='Дата рождения позже уже сохранённых записей. Проверьте пациента и дату.';return;}if(!create&&(p.meals.length||p.symptoms.length)&&(name!==p.name||dob!==p.dob)&&!confirm('Изменить сведения выбранного пациента? Его записи останутся в этом профиле. Для другого ребёнка добавьте отдельного пациента.'))return;if(create){if(profiles.length>=100)return;p=PrikormModel.patient(name,dob);profiles.push(p);active=profiles.length-1;}else{p.name=name;p.dob=dob;}PrikormModel.riskKeys.forEach(k=>p.risks[k]=f.get(k));collection.activePatientId=p.id;render('today');toast('Профиль сохранён.');});
 $('#import-file')?.addEventListener('change',async e=>{const file=e.target.files[0];pendingImport=null;$('#import-preview').replaceChildren();$('#import-error').textContent='';if(!file)return;const formElement=e.target,sequence=++importSequence;try{if(file.size>64*1024*1024)throw new Error('Файл превышает 64 МБ.');const validated=PrikormModel.validate(JSON.parse(await file.text()));if(!formElement.isConnected||sequence!==importSequence)return;pendingImport=validated;$('#import-preview').innerHTML=`<p>ЕмПрикорм. Пациентов: ${validated.patients.length}; записей о еде — ${validated.patients.reduce((n,x)=>n+x.meals.length,0)}.</p><button class="family-data-button family-data-primary" data-runtime="import-add">Добавить пациентов из копии</button><button class="family-data-button" data-runtime="import-replace">Заменить все данные</button><button type="button" class="family-data-button" data-runtime="import-cancel">Отмена</button>`;}catch(error){if(formElement.isConnected&&sequence===importSequence)$('#import-error').textContent=error.message||'Не удалось прочитать копию.';}});
}
// Capture only blocks mutations; emergency help, backup export and reload remain reachable.
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(loading&&!['help'].includes(b.dataset.go)&&!['choking-help','close-triage'].includes(b.dataset.action)){e.stopImmediatePropagation();e.preventDefault();return;}if(storageFailed){const safe=b.dataset.go==='help'||b.dataset.go==='settings'||['export','reload'].includes(b.dataset.runtime)||['choking-help','close-triage'].includes(b.dataset.action);if(!safe){e.stopImmediatePropagation();e.preventDefault();}}},true);
document.addEventListener('submit',e=>{if(storageFailed){e.preventDefault();e.stopImmediatePropagation();}},true);
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b||b.disabled)return;const action=b.dataset.runtime;
 if(action==='reload'){if((dirty||pendingWrites||storageFailed)&&!confirm('Перезагрузить страницу? Несохранённые изменения останутся только в скачанной копии.'))return;location.reload();return;}
 if(action==='export'){await exportBackup();return;}if(action==='import-cancel'){importSequence++;pendingImport=null;$('#import-preview').replaceChildren();$('#import-file').value='';$('#import-error').textContent='Восстановление отменено.';return;}
 if(storageFailed)return;
 if(action==='install'){await startInstallation();return;}
 if(action==='persistent'){try{const ok=await navigator.storage?.persist?.();$('#persistence-result').textContent=ok?'Браузер предоставил постоянное хранилище. Резервные копии всё равно нужны.':'Браузер не предоставил защиту. Регулярно сохраняйте копии.';}catch{$('#persistence-result').textContent='Функция недоступна. Используйте резервные копии.';}}
 if(action==='check-update'){await checkAppUpdate();return;}
 if(action==='update'){await activateUpdate();return;}
 if(action==='delete-patient'){const patientId=FamilyData.selectedPatient(),patient=profiles.find(q=>q.id===patientId);if(!patient)return;if(!confirm('Удалить все записи пациента «'+patient.name+'» с этого устройства? Отменить нельзя. Сначала сохраните резервную копию.'))return;await saveQueue;if(storageFailed||!profiles.some(q=>q.id===patientId))return;profiles=profiles.filter(q=>q.id!==patientId);if(!profiles.length)profiles.push(PrikormModel.patient());collection.patients=profiles;if(!profiles.some(q=>q.id===collection.activePatientId))collection.activePatientId=profiles[0].id;resetSelection();render('settings');toast('Дневник выбранного пациента удалён.');}
 if((action==='import-add'||action==='import-replace')&&pendingImport){if(action==='import-add'&&profiles.length+pendingImport.patients.length>100){$('#import-error').textContent='Можно хранить до 100 пациентов.';return;}if(!confirm(action==='import-replace'?'Заменить все данные копией? Сначала скачайте текущую копию.':'Добавить пациентов из файла как отдельные профили?'))return;const source=pendingImport,sequence=importSequence;await saveQueue;if(storageFailed||source!==pendingImport||sequence!==importSequence)return;const imported=structuredClone(source);if(action==='import-replace'){collection=imported;profiles=collection.patients;}else{imported.patients.forEach(q=>q.id=crypto.randomUUID());profiles.push(...imported.patients);collection.activePatientId=imported.patients[0].id;}resetSelection();render('today');toast('Резервная копия восстановлена.');}
 if(b.dataset.removeMeal){if(!confirm('Удалить запись о еде? Связанные наблюдения о симптомах останутся без привязки к этому приёму.'))return;const id=b.dataset.removeMeal;p.meals=p.meals.filter(m=>m.id!==id);p.symptoms.forEach(s=>{if(s.mealId===id){s.mealId=null;s.updatedAt=new Date().toISOString();}});render('diary');toast('Запись удалена. Наблюдения сохранены.');}
 if(b.dataset.removeSymptom){if(!confirm('Удалить выбранную запись симптомов?'))return;p.symptoms=p.symptoms.filter(s=>s.id!==b.dataset.removeSymptom);render('diary');toast('Запись симптомов удалена.');}
});
window.addEventListener('beforeunload',e=>{if(dirty||pendingWrites||storageFailed||photoReading){e.preventDefault();e.returnValue='';}});
function refreshInstallUI(){FamilyData.refresh();const b=$('[data-runtime=install]');if(b){b.hidden=!installPrompt||isStandalone();b.disabled=installBusy;}if($('#install-status'))$('#install-status').textContent=isStandalone()?'ЕмПрикорм открыто как установленное приложение.':installStatus;}
async function startInstallation(){
 if(!installPrompt||installBusy||isStandalone())return;
 const prompt=installPrompt;installPrompt=null;installBusy=true;installStatus='Подтвердите установку в окне Chrome.';refreshInstallUI();
 try{await prompt.prompt();const choice=await prompt.userChoice;installStatus=choice.outcome==='accepted'?'Запрос передан Chrome. Дождитесь установки, затем проверьте запуск с главного экрана. Если Chrome сообщает об ошибке, откройте сайт ЕмПрикорм в отдельной вкладке Chrome и попробуйте меню «Добавить на главный экран» → «Создать ярлык».':'Установка отменена. Дневник доступен в браузере; повторить установку можно через меню Chrome.';}
 catch{installStatus='Chrome не смог запустить установку. Откройте сайт ЕмПрикорм в отдельной вкладке Chrome и используйте меню «Добавить на главный экран». Можно продолжать вести дневник в браузере. Не удаляйте данные сайта: в них хранятся записи.';}
 finally{installBusy=false;refreshInstallUI();}
}
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;refreshInstallUI();});
window.addEventListener('appinstalled',()=>{installPrompt=null;installStatus='Chrome сообщил об установке. Откройте ЕмПрикорм с главного экрана.';refreshInstallUI();});
function refreshUpdateCheckUI(){const recovery=$('[data-family-update-recovery]');if(recovery)recovery.hidden=!/не удалось|ошибк|недоступ/i.test(updateCheckStatus);const button=$('[data-runtime=check-update]');if(button){button.disabled=updateChecking;button.textContent=updateChecking?'Проверяем…':'Проверить обновления';}if($('#update-check-status'))$('#update-check-status').textContent=updateCheckStatus;}
async function checkAppUpdate(){
 if(updateChecking)return;updateChecking=true;updateCheckStatus='Проверяем обновления…';refreshUpdateCheckUI();
 try{
  if(!navigator.onLine)throw new Error('Нет подключения к интернету. Подключитесь и повторите проверку.');
  if(!registration)await setupOffline();
  if(!registration)throw new Error(offlineError||'Не удалось подключить обновления. Откройте ссылку «Если обновление не появляется».');
  const waiting=await AppUpdates.check(registration);
  updateCheckStatus=waiting||reloadReady?'Обновление готово. Нажмите «Обновить приложение».':'Проверка завершена. Готового обновления нет. На устройстве версия '+VERSION+'.';
 }catch(error){updateCheckStatus=error.message||'Не удалось проверить обновление. Повторите попытку с интернетом.';}
 finally{updateChecking=false;refreshUpdateUI();}
}
function refreshUpdateUI(){
 refreshUpdateCheckUI();
 const ready=!!registration?.waiting||reloadReady;
 $('#update-banner').hidden=!ready;
 $$('[data-runtime=update]').forEach(b=>{b.hidden=!ready;b.disabled=loading||storageFailed||updateRequested||updatePreparing;});
}
function updateMessage(text){$('#update-message').textContent=text;}
function reloadUpdatedApp(){if(!reloading){reloading=true;location.reload();}}
async function activateUpdate(){
 if(loading||storageFailed||updateRequested||updatePreparing||(!registration?.waiting&&!reloadReady))return;
 if(dirty||photoReading){updateMessage(photoReading?'Дождитесь загрузки фото и сохраните запись перед обновлением.':'Сначала сохраните запись или настройки, затем нажмите «Обновить приложение».');return;}
 if(!confirm('Обновить приложение? Сохранённый дневник останется на устройстве.'))return;
 updatePreparing=true;refreshUpdateUI();
 try{
  await saveQueue;
  if(storageFailed||pendingWrites){updateMessage('Не удалось подтвердить сохранение. Проверьте сообщение об ошибке и сохраните резервную копию перед обновлением.');return;}
  if(dirty||photoReading){updateMessage('Сначала завершите и сохраните запись, затем повторите обновление.');return;}
  if(!registration?.waiting&&!reloadReady)return;
  updateRequested=true;updateMessage('Обновляем приложение…');
  if(reloadReady)reloadUpdatedApp();else registration.waiting.postMessage({type:'ACTIVATE'});
 }catch{updateRequested=false;updateMessage('Не удалось выполнить обновление. Повторите попытку.');}
 finally{updatePreparing=false;refreshUpdateUI();}
}
function refreshOfflineUI(){if($('#offline-status'))$('#offline-status').textContent=offlineStatus();refreshUpdateUI();}
async function setupOffline(){
 if(!('serviceWorker'in navigator)){offlineError='Этот браузер не поддерживает автономную подготовку приложения.';refreshOfflineUI();return;}
 try{
  let previousController=navigator.serviceWorker.controller,checking=false,lastCheck=0;
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
   const next=navigator.serviceWorker.controller;
   if(updateRequested){reloadUpdatedApp();return;}
   if(previousController&&next!==previousController)reloadReady=true;
   previousController=next;offlineReady=!!next;refreshOfflineUI();
  });
  registration=await navigator.serviceWorker.register('./sw.js',{scope:'./',updateViaCache:'none'});
  const watch=()=>{const worker=registration.installing;if(worker)worker.addEventListener('statechange',()=>{offlineReady=!!registration.active;refreshOfflineUI();});refreshOfflineUI();};
  registration.addEventListener('updatefound',watch);watch();
  await AppUpdates.waitForInstall(registration);
  if(registration.scope!==new URL('./',location.href).href)throw new Error('Область установки не совпала с адресом ЕмПрикорм.');
  offlineReady=!!registration.active;refreshOfflineUI();
  const check=async()=>{if(checking||document.hidden||!navigator.onLine||Date.now()-lastCheck<300000)return;checking=true;lastCheck=Date.now();try{await AppUpdates.check(registration);}catch(error){updateCheckStatus=error.message||'Не удалось проверить обновление. Повторите проверку в разделе «Данные и установка».';}finally{checking=false;refreshOfflineUI();}};
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});window.addEventListener('online',check);check();
 }catch{offlineError='Не удалось подготовить работу без сети. Повторите открытие с интернетом.';refreshOfflineUI();}
}
async function init(){let first=false;try{const saved=await DiaryStore.read();canExport=true;rawRecovery=saved;first=!saved;collection=saved?PrikormModel.validate(saved):PrikormModel.fresh();rawRecovery=null;profiles=collection.patients;resetSelection();lastQueued=saved?JSON.stringify(collection):'';loading=false;$('#storage-status').textContent='Сохранено на этом устройстве';render(first?'profile':'today');await saveQueue;setupOffline();}catch(e){loading=false;if(!collection){collection=PrikormModel.fresh();profiles=collection.patients;resetSelection();}storageFailed=true;render('help');showStorageError(new Error('Существующие данные не перезаписаны. '+e.message));}}
function refreshDate(){const date=PrikormModel.localDate();if(TODAY===date||loading||storageFailed)return;TODAY=date;selectedDay=date;if(!dirty&&!photoReading)render(view);else $$('#screen input[type=date]').forEach(el=>el.max=date);}
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshDate();});setInterval(refreshDate,30000);
$$('[data-nav-icon]').forEach(el=>el.innerHTML=icon(el.dataset.navIcon));
FamilyData.watchStorage('#storage-status');
init();
