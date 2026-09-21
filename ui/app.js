// Badge for alerts — shows when you have active district subscriptions
(function initAlertBadge(){
  const badge=document.getElementById("alertBadge");
  const badgeIcon=document.getElementById("alertBadgeIcon");
  async function update(){
    try{
      const r=await fetch("/api/alerts/stats");
      const j=await r.json();
      const has = j.total>0;
      if(badge) badge.classList.toggle("show", has);
      if(badgeIcon) badgeIcon.style.display = has ? "block" : "none";
      if(badgeIcon) badgeIcon.classList.toggle("show", has);
    }catch{}
  }
  update();
  setInterval(update, 30000);
})();

// Phase 2: Landing ↔ Chat, weather card, processing, voice modal + premium sidebar/theme
const landingView = document.getElementById("landingView");
const chatView = document.getElementById("chatView");
const backBtn = document.getElementById("backBtn");
const newChatBtn = document.getElementById("newChatBtn");
const aboutLink = document.getElementById("aboutLink");
const aboutModal = document.getElementById("aboutModal");
const aboutClose = document.getElementById("aboutClose");
const sidebar = document.getElementById("sidebar");
const sidebarOpen = document.getElementById("sidebarOpen");
const sidebarClose = document.getElementById("sidebarClose");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const themeToggle = document.getElementById("themeToggle");

const landingInput = document.getElementById("landingInput");
const askBtn = document.getElementById("askBtn");
const landingMic = document.getElementById("landingMic");

const chatHistory = document.getElementById("chatHistory");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");
const chatMic = document.getElementById("chatMic");
const clearBtn = document.getElementById("clearBtn");
const chatStatus = document.getElementById("chatStatus");
const chatError = document.getElementById("chatError");
const processing = document.getElementById("processing");

const voiceModal = document.getElementById("voiceModal");
const voiceTranscript = document.getElementById("voiceTranscript");
const voiceCancel = document.getElementById("voiceCancel");

let listening = false, recorder = null;

function cleanText(t){ return t.replace(/\*\*/g,"").replace(/\*/g,"").replace(/#{1,6}\s?/g,"").trim(); }

function showLanding(){
  landingView.classList.remove("hidden");
  chatView.classList.add("hidden");
  backBtn.classList.add("hidden");
  chatHistory.innerHTML = "";
  chatError.classList.add("hidden");
  chatStatus.textContent = "";
  landingInput.value = "";
  chatInput.value = "";
}
function showChat(){
  landingView.classList.add("hidden");
  chatView.classList.remove("hidden");
  backBtn.classList.remove("hidden");
  chatInput.focus();
}
backBtn.addEventListener("click", showLanding);
newChatBtn.addEventListener("click", showLanding);
// Sidebar ChatGPT-like: desktop rail (64px icons) vs 260px, mobile overlay
function setSidebar(open){
  if(!sidebar) return;
  const isMobile = window.innerWidth < 860;
  if(isMobile){
    sidebar.classList.toggle("collapsed", !open);
    sidebarOverlay.classList.toggle("hidden", !open);
  } else {
    sidebar.classList.toggle("collapsed", !open);
    localStorage.setItem("sidebarOpen", open ? "1":"0");
  }
}
if(sidebarOpen) sidebarOpen.addEventListener("click", ()=> setSidebar(true));
if(sidebarClose) sidebarClose.addEventListener("click", ()=> {
  const isCollapsed = sidebar.classList.contains("collapsed");
  setSidebar(isCollapsed);
});
if(sidebarOverlay) sidebarOverlay.addEventListener("click", ()=> setSidebar(false));
(function initSidebar(){
  const saved = localStorage.getItem("sidebarOpen");
  const isDesktop = window.innerWidth >= 860;
  if(isDesktop){
    if(saved === "0") sidebar?.classList.add("collapsed");
    else sidebar?.classList.remove("collapsed");
  } else {
    sidebar?.classList.add("collapsed");
    sidebarOverlay?.classList.add("hidden");
  }
})();
// Theme day/night (premium) + persist — topbar only (sidebar toggle removed per design)
function applyTheme(t){
  document.documentElement.setAttribute("data-theme", t);
  localStorage.setItem("theme", t);
  if(themeToggle) themeToggle.textContent = t==="dark" ? "☀" : "◐";
}
function toggleTheme(){
  const cur = document.documentElement.getAttribute("data-theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark":"light");
  applyTheme(cur==="dark" ? "light":"dark");
}
if(themeToggle) themeToggle.addEventListener("click", toggleTheme);
(function initTheme(){
  const saved = localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark":"light");
  applyTheme(saved);
})();
function openAbout(){ aboutModal.classList.remove("hidden"); }
function closeAbout(){ aboutModal.classList.add("hidden"); }
aboutLink.addEventListener("click", (e)=>{ e.preventDefault(); openAbout(); });
aboutClose.addEventListener("click", closeAbout);
aboutModal.addEventListener("click", (e)=>{ if(e.target===aboutModal) closeAbout(); });
document.addEventListener("keydown", (e)=>{ if(e.key==="Escape"){ aboutModal.classList.add("hidden"); voiceModal.classList.add("hidden"); const am=document.getElementById("alertsModal"); if(am) am.classList.add("hidden"); } });

function parseWeather(text){
  const temp=(text.match(/(\d+\.?\d*)\s*°C/)||[])[1];
  const hum=(text.match(/(\d+)\s*%\s*humidity/i)||text.match(/humidity[^\d]*(\d+)/i)||[])[1];
  const wind=(text.match(/wind[^\d]*(\d+\.?\d*)/i)||[])[1];
  return {temp,hum,wind};
}

function addUserBubble(text){
  const div=document.createElement("div");
  div.className="bubble user";
  div.textContent=text;
  chatHistory.appendChild(div);
  chatHistory.scrollTop=chatHistory.scrollHeight;
}
function addAssistantCard(query, reply, lang){
  const wrap=document.createElement("div");
  wrap.className="bubble assistant";
  const p=parseWeather(reply);
  const tVal=p.temp? p.temp+"°C":"--";
  const timeStr=new Date().toLocaleString("en-IN",{timeZone:"Asia/Kolkata", weekday:"short", day:"numeric", month:"short", hour:"numeric", minute:"2-digit"})+" IST";
  // derive label: tomorrow/today/now hint
  let when="Forecast";
  if(/tomorrow/i.test(query)) when="Tomorrow";
  else if(/today/i.test(query)) when="Today";
  else if(/now/i.test(query)) when="Now";
  const loc = query.length>36? query.slice(0,36)+"…": query;
  const hum=p.hum? p.hum+" %":"--";
  const wind=p.wind? p.wind+" km/h":"--";
  const cond = p.temp? (parseFloat(p.temp)>=32?"Hot": parseFloat(p.temp)>=26?"Warm":"Pleasant"):"--";
  wrap.innerHTML=`
    <div class="weatherCard">
      <div class="weatherCardTop">
        <div><div class="loc">${when}</div><div class="date">${timeStr}</div><div style="margin-top:6px;font-size:12px;color:#64748b">${cleanText(loc)}</div></div>
        <div class="temp">${tVal}<sup>°C</sup></div>
      </div>
      <div class="grid3">
        <div class="gItem"><div class="gLabel">Humidity</div><div class="gVal">${hum}</div></div>
        <div class="gItem"><div class="gLabel">Wind</div><div class="gVal">${wind}</div></div>
        <div class="gItem"><div class="gLabel">Feels like</div><div class="gVal">${cond}</div></div>
      </div>
      <div class="replyPlain">${cleanText(reply)}</div>
      <div class="voicePlayRow">
        <button class="playBtn" data-text="${cleanText(reply).replace(/"/g,'&quot;')}" data-lang="${lang}">Play response</button>
        <audio controls class="audioEl hidden"></audio>
      </div>
    </div>`;
  chatHistory.appendChild(wrap);
  chatHistory.scrollTop=chatHistory.scrollHeight;
  // attach play
  const btn=wrap.querySelector(".playBtn");
  const audio=wrap.querySelector("audio");
  btn.addEventListener("click", async()=>{
    btn.textContent="Loading...";
    try{
      const r=await fetch("/api/tts",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text: btn.dataset.text, lang: btn.dataset.lang})});
      const b=await r.blob(); const url=URL.createObjectURL(b);
      audio.src=url; audio.classList.remove("hidden"); await audio.play(); btn.textContent="Play again";
    }catch(e){ btn.textContent="Error"; }
  });
  // auto play if enabled (default)
  if(document.getElementById("autoPlayCheck")?.checked !== false){
    // try autoplay silently — click programmatically
    btn.click();
  }
}

let isProcessing=false;
function setProcessing(on){
  isProcessing=on;
  chatSend.disabled=on;
  if(chatMic) chatMic.disabled=on;
  if(landingMic) landingMic.disabled=on;
  if(askBtn) askBtn.disabled=on;
  if(landingInput) landingInput.disabled=on;
  if(chatInput) chatInput.disabled=on;
  document.querySelector(".composerInner")?.classList.toggle("loading",on);
  document.getElementById("landingSearchCard")?.classList.toggle("loading",on);
  // dim quick chips
  document.querySelectorAll(".quickChips button").forEach(b=>b.disabled=on);
}
async function doChat(query){
  if(isProcessing) return;
  const text=(query||"").trim();
  if(!text) return;
  // move to chat if on landing
  if(!landingView.classList.contains("hidden")) showChat();
  addUserBubble(text);
  chatInput.value=""; clearBtn.classList.add("hidden");
  chatError.classList.add("hidden");
  chatStatus.textContent="Checking the latest weather data...";
  processing.classList.remove("hidden");
  setProcessing(true);
  try{
    const res=await fetch("/chat",{method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({query:text})});
    const data=await res.json();
    if(!res.ok) throw new Error(data.error||"Failed");
    addAssistantCard(text, data.reply, data.lang||"en");
    chatStatus.textContent="";
  }catch(e){
    chatError.textContent=e.message||String(e);
    chatError.classList.remove("hidden");
    chatStatus.textContent="";
  }finally{
    processing.classList.add("hidden");
    setProcessing(false);
    chatStatus.textContent="";
  }
}

// Landing handlers
function landingQuery(){ const v=landingInput.value.trim()|| landingInput.placeholder.replace('Try: ','').replace(/"/g,''); return v; }
askBtn.addEventListener("click",()=>{ const q=landingInput.value.trim(); if(!q){ landingInput.focus(); return; } doChat(q); });
landingInput.addEventListener("keydown",e=>{ if(e.key==="Enter") { const q=landingInput.value.trim(); if(q) doChat(q); } });
document.querySelectorAll(".quickChips button").forEach(b=>b.addEventListener("click",()=> doChat(b.dataset.q)));
document.querySelectorAll(".suggestions button").forEach(b=>b.addEventListener("click",()=> doChat(b.dataset.q)));

// Alerts now on dedicated /alerts.html — old inline modal removed. Keep nav link.
const openAlertsBtn=document.getElementById("openAlerts");
if(openAlertsBtn) openAlertsBtn.addEventListener("click", ()=>{ window.location.href="/alerts.html"; });

// Chat handlers
chatSend.addEventListener("click",()=> doChat(chatInput.value));
chatInput.addEventListener("keydown",e=>{ if(e.key==="Enter") doChat(chatInput.value); });
chatInput.addEventListener("input",()=> clearBtn.classList.toggle("hidden", !chatInput.value.trim()));
clearBtn.addEventListener("click",()=>{ chatInput.value=""; clearBtn.classList.add("hidden"); chatInput.focus(); });

// Voice — blocked while processing
async function startVoice(targetInput){
  if(isProcessing) return;
  voiceModal.classList.remove("hidden");
  voiceTranscript.textContent="Listening...";
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});
    const mr=new MediaRecorder(stream,{mimeType:"audio/webm"});
    const chunks=[];
    mr.ondataavailable=e=> e.data.size && chunks.push(e.data);
    mr.onstop=async()=>{
      voiceModal.classList.add("hidden");
      stream.getTracks().forEach(t=>t.stop());
      const blob=new Blob(chunks,{type:"audio/webm"});
      if(!blob.size) return;
      // show transcript placeholder
      voiceTranscript.textContent="Transcribing...";
      try{
        const fd=new FormData(); fd.append("file", blob, "audio.webm");
        const r=await fetch("/api/stt",{method:"POST", body:fd});
        const d=await r.json();
        if(!r.ok) throw new Error(d.error||"STT failed");
        voiceTranscript.textContent='"'+d.text+'"';
        if(targetInput) targetInput.value=d.text;
        await doChat(d.text);
      }catch(e){
        chatError.textContent=e.message||String(e); chatError.classList.remove("hidden");
      }
    };
    recorder=mr; mr.start(); listening=true;
    // allow cancel to stop
    voiceCancel.onclick=()=>{
      try{ mr.state!=="inactive"&&mr.stop(); }catch{}
      voiceModal.classList.add("hidden");
      stream.getTracks().forEach(t=>t.stop());
    };
  }catch(e){
    voiceModal.classList.add("hidden");
    chatError.textContent="Microphone blocked";
    chatError.classList.remove("hidden");
  }
}
landingMic.addEventListener("click",()=> startVoice(landingInput));
document.getElementById("chatMic").addEventListener("click",()=> startVoice(chatInput));
voiceCancel.addEventListener("click",()=>{
  try{ recorder&&recorder.state!=="inactive"&&recorder.stop(); }catch{}
  voiceModal.classList.add("hidden");
});
