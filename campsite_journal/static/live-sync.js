'use strict';
(()=>{
 let pending=false,refreshing=false,timer,stream;
 const busy=()=>['editor','prefs','stayPicker','addressSearch','positionPicker','campsiteFinder'].some(id=>document.getElementById(id)?.open)||!!window.journalUploading;
 async function apply(){if(!pending||refreshing||busy())return;refreshing=true;pending=false;try{await reload()}catch{pending=true}finally{refreshing=false;if(pending&&!busy())timer=setTimeout(apply,1500)}}
 function schedule(){pending=true;clearTimeout(timer);timer=setTimeout(apply,150)}
 function connect(){if(stream)return;stream=new EventSource('api/live');stream.addEventListener('ready',schedule);stream.addEventListener('change',schedule);stream.onerror=()=>{/* EventSource reconnects automatically. */}}
 document.addEventListener('close',()=>{if(pending)timer=setTimeout(apply,0)},true);document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule()});window.addEventListener('online',schedule);window.addEventListener('journal-idle',apply);connect();
 // Recover from proxies or browsers that do not deliver the event stream reliably.
 setInterval(()=>{if(!document.hidden)schedule()},15000);
})();
