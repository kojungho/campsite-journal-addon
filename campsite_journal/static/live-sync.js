'use strict';
(()=>{
 let pending=false,refreshing=false,timer,stream,currentRevision=null,currentVersion='';
 const busy=()=>['editor','prefs','stayPicker','addressSearch','positionPicker','campsiteFinder'].some(id=>document.getElementById(id)?.open)||!!window.journalUploading;
 async function apply(){if(!pending||refreshing||busy())return;refreshing=true;pending=false;try{await reload()}catch{pending=true}finally{refreshing=false;if(pending&&!busy())timer=setTimeout(apply,1500)}}
 function schedule(){pending=true;clearTimeout(timer);timer=setTimeout(apply,150)}
 function connect(){if(stream)return;stream=new EventSource('api/live');const changed=e=>{const revision=Number(e.data);if(e.type==='ready'||revision!==currentRevision){currentRevision=revision;schedule()}};stream.addEventListener('ready',changed);stream.addEventListener('change',changed);stream.onerror=()=>{/* EventSource reconnects automatically. */}}
 document.addEventListener('close',()=>{if(pending)timer=setTimeout(apply,0)},true);document.addEventListener('visibilitychange',()=>{if(!document.hidden)schedule()});window.addEventListener('online',schedule);window.addEventListener('journal-idle',apply);connect();
 // Recover from proxies or browsers that do not deliver the event stream reliably.
 setInterval(async()=>{if(document.hidden)return;try{const response=await fetch('api/live/status');if(!response.ok)return;const status=await response.json();if(status.revision!==currentRevision||(currentVersion&&status.version!==currentVersion)){currentRevision=status.revision;schedule()}currentVersion=status.version}catch{}},15000);
})();
