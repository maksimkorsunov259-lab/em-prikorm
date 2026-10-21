'use strict';
(()=>{
 const status=document.getElementById('status'),checkButton=document.getElementById('check'),activateButton=document.getElementById('activate'),saved=document.getElementById('saved');
 let registration=null,busy=false;
 function refresh(){checkButton.disabled=busy;activateButton.hidden=!registration?.waiting;activateButton.disabled=busy||!saved.checked;}
 async function check(){
  if(busy)return;busy=true;status.textContent='Проверяем обновление…';refresh();
  try{
   if(!('serviceWorker'in navigator))throw new Error('Этот браузер не поддерживает обновление автономного приложения. Откройте ЕмПрикорм в Chrome или Safari.');
   if(!navigator.onLine)throw new Error('Нет подключения к интернету. Подключитесь и повторите проверку.');
   const scope=new URL('./',location.href).href;
   try{registration=await navigator.serviceWorker.register('./sw.js',{scope:'./',updateViaCache:'none'});}catch{throw new Error('Не удалось подключиться к обновлениям ЕмПрикорм. Проверьте подключение к интернету и повторите попытку.');}
   if(registration.scope!==scope)throw new Error('Адрес установки не совпадает с адресом ЕмПрикорм.');
   await AppUpdates.waitForInstall(registration);
   const waiting=await AppUpdates.check(registration);
   status.textContent=waiting?'Обновление загружено. Подтвердите сохранение записей и нажмите «Установить обновление и открыть дневник».':'Проверка завершена. Готового обновления нет. Можно вернуться в ЕмПрикорм. Если там остаётся старый интерфейс, сообщите автору номер версии из раздела «Данные и установка».';
  }catch(error){status.textContent=error.message||'Проверить обновление не удалось. Повторите попытку с интернетом.';}
  finally{busy=false;refresh();}
 }
 async function activate(){
  const worker=registration?.waiting;if(busy||!worker||!saved.checked)return;
  busy=true;status.textContent='Применяем обновление…';refresh();
  try{
   await new Promise((resolve,reject)=>{
    let timer;
    const finish=error=>{clearTimeout(timer);worker.removeEventListener('statechange',changed);error?reject(error):resolve();};
    const changed=()=>{if(worker.state==='activated')finish();else if(worker.state==='redundant')finish(new Error('Не удалось применить обновление. Повторите проверку.'));};
    worker.addEventListener('statechange',changed);timer=setTimeout(()=>finish(new Error('Обновление ещё не завершилось. Закройте другие окна ЕмПрикорм и повторите проверку.')),20000);
    worker.postMessage({type:'ACTIVATE'});changed();
   });
   location.replace(new URL('./',location.href).href);
  }catch(error){status.textContent=error.message;busy=false;refresh();}
 }
 saved.addEventListener('change',refresh);checkButton.addEventListener('click',check);activateButton.addEventListener('click',activate);check();
})();
