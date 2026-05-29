// ===== JARVIS WEB CLIENT =====
const WS_URL = `ws://${location.host}/ws`;
let ws = null;
let reconnectTimer = null;
let voiceEnabled = true;
let isRecording = false;
let currentJarvisText = '';
let speaking = false;
let cmdCount = 0;
let animPhase = 0;
let eqEnergy = 0;

// ===== WEBSOCKET =====
function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    try { if (ws) ws.close(); } catch(e) {}

    ws = new WebSocket(WS_URL);
    ws.onopen = () => {
        updateStatus('Online', true);
        if (!document.querySelector('.msg-bubble')) addGreeting();
    };
    ws.onmessage = (e) => {
        try {
            const msg = JSON.parse(e.data);
            handleServerMessage(msg);
        } catch(err) {
            console.error('Bad WS message:', err);
        }
    };
    ws.onclose = () => {
        updateStatus('Reconnecting...', false);
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connect, 2000);
    };
    ws.onerror = () => { try { ws.close(); } catch(e) {} };
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
}

function handleServerMessage(msg) {
    switch(msg.type) {
        case 'token':
            appendToken(msg.content);
            break;
        case 'response':
            finalizeJarvisMessage(msg.content);
            speaking = false;
            break;
        case 'user':
            addMessage('You', msg.content);
            break;
        case 'status':
            // ANY status message from server means we are connected
            updateStatus(msg.content, true);
            break;
        case 'stats':
            updateStats(msg);
            break;
        case 'error':
            addMessage('Jarvis', 'Error: ' + msg.content);
            speaking = false;
            updateStatus('Online', true);
            break;
    }
}

// ===== CHAT =====
function addGreeting() {
    const h = new Date().getHours();
    const sal = h < 14 ? (h < 6 ? 'Buenas noches' : 'Buenos d\u00edas') : (h < 21 ? 'Buenas tardes' : 'Buenas noches');
    addMessage('Jarvis', sal + ', se\u00f1or. \u00bfQu\u00e9 desea hacer hoy?');
}

function addMessage(author, text) {
    const panel = document.getElementById('chatPanel');
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    const isYou = author.toLowerCase() === 'you' || author.toLowerCase() === 'usuario';
    const time = new Date().toLocaleTimeString('es-ES', {hour:'2-digit', minute:'2-digit'});
    bubble.innerHTML = `
        <div class="msg-header">
            <span class="author ${isYou ? 'you' : 'jarvis'}">${isYou ? 'You' : 'JARVIS'}</span>
            <span>${time}</span>
        </div>
        <div class="msg-text ${isYou ? 'you' : 'jarvis'}">${escapeHtml(text)}</div>
    `;
    panel.appendChild(bubble);
    panel.scrollTop = panel.scrollHeight;
    cmdCount++;
    document.getElementById('cmdCount').textContent = cmdCount;
}

function appendToken(token) {
    speaking = true;
    const panel = document.getElementById('chatPanel');
    let jarvisBubble = panel.querySelector('.msg-bubble.streaming');
    if (!jarvisBubble) {
        jarvisBubble = document.createElement('div');
        jarvisBubble.className = 'msg-bubble streaming';
        const time = new Date().toLocaleTimeString('es-ES', {hour:'2-digit', minute:'2-digit'});
        jarvisBubble.innerHTML = `
            <div class="msg-header"><span class="author jarvis">JARVIS</span><span>${time}</span></div>
            <div class="msg-text jarvis"></div>
        `;
        panel.appendChild(jarvisBubble);
    }
    const textEl = jarvisBubble.querySelector('.msg-text');
    textEl.textContent += token;
    currentJarvisText += token;
    panel.scrollTop = panel.scrollHeight;
}

function finalizeJarvisMessage(fullText) {
    const panel = document.getElementById('chatPanel');
    const streaming = panel.querySelector('.msg-bubble.streaming');
    if (streaming) {
        streaming.classList.remove('streaming');
        const textEl = streaming.querySelector('.msg-text');
        if (textEl && fullText) textEl.textContent = fullText;
    } else if (fullText) {
        addMessage('Jarvis', fullText);
    }
    currentJarvisText = '';
    // TTS is handled by the backend (edge-tts), no browser voice needed
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== SEND MESSAGE =====
function sendMessage() {
    const input = document.getElementById('inputBox');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    addMessage('You', text);
    send({type: 'message', content: text});
    updateStatus('Processing...', true);
}

document.getElementById('btnSend').addEventListener('click', sendMessage);
document.getElementById('inputBox').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// ===== CLEAR / EXPORT =====
document.getElementById('btnClear').addEventListener('click', () => {
    document.getElementById('chatPanel').innerHTML = '';
    fetch('/api/clear_memory', {method:'POST'});
});
document.getElementById('btnExport').addEventListener('click', () => {
    const panel = document.getElementById('chatPanel');
    const text = Array.from(panel.querySelectorAll('.msg-text')).map(el => el.textContent).join('\n\n');
    const blob = new Blob([text], {type:'text/plain'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'jarvis_conversation.txt';
    a.click();
});

// ===== STT =====
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
const btnMic = document.getElementById('btnMic');

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        addMessage('You', text);
        send({type: 'voice', content: text});
        updateStatus('Processing...', true);
        isRecording = false;
        btnMic.classList.remove('active');
    };
    recognition.onerror = () => { isRecording = false; btnMic.classList.remove('active'); };
    recognition.onend = () => { isRecording = false; btnMic.classList.remove('active'); };
}

btnMic.addEventListener('click', () => {
    if (!recognition) { alert('Speech recognition not supported'); return; }
    if (isRecording) { recognition.stop(); isRecording = false; btnMic.classList.remove('active'); }
    else { recognition.start(); isRecording = true; btnMic.classList.add('active'); }
});

// ===== STATUS =====
function updateStatus(text, online) {
    const pill = document.getElementById('statusPill');
    const center = document.getElementById('centerStatus');
    pill.textContent = online ? ' Online ' : ' Offline ';
    pill.className = 'status-pill' + (online ? ' online' : '');
    center.textContent = text;
    center.className = 'center-status' + (online ? ' active' : '');
}

// ===== STATS =====
function updateStats(data) {
    if (data.cpu !== undefined) {
        document.getElementById('cpuVal').textContent = data.cpu + '%';
        document.getElementById('cpuBar').style.width = data.cpu + '%';
        document.getElementById('cpuPct').textContent = data.cpu + '%';
    }
    if (data.ram_used !== undefined) {
        document.getElementById('ramVal').textContent = data.ram_used + ' GB';
        const ramPct = Math.min(100, (data.ram_used / Math.max(0.1, data.ram_total)) * 100);
        document.getElementById('ramBar').style.width = ramPct + '%';
        document.getElementById('memVal').textContent = data.ram_used + '/' + data.ram_total + ' GB';
    }
    if (data.disk_free !== undefined) {
        document.getElementById('diskVal').textContent = data.disk_free + '/' + data.disk_total + ' GB';
    }
    if (data.uptime !== undefined) {
        const h = Math.floor(data.uptime / 3600);
        const m = Math.floor((data.uptime % 3600) / 60);
        const s = data.uptime % 60;
        document.getElementById('uptime').textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    }
    if (data.weather_text) document.getElementById('weatherChip').textContent = data.weather_text;
    if (data.weather_details) {
        const d = data.weather_details;
        if (d.temp) document.getElementById('weatherTemp').textContent = d.temp;
        if (d.location) document.getElementById('weatherLoc').textContent = d.location;
        if (d.desc) document.getElementById('weatherDesc').textContent = d.desc;
        if (d.humidity) document.getElementById('weatherHum').textContent = d.humidity;
        if (d.wind) document.getElementById('weatherWind').textContent = d.wind;
        if (d.feelslike) document.getElementById('weatherFeels').textContent = d.feelslike;
    }
}

// ===== CLOCK =====
function updateClock() {
    const now = new Date();
    const opts = {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:true};
    const date = now.toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'});
    document.getElementById('clock').textContent = now.toLocaleTimeString('en-US', opts) + '  |  ' + date;
}
setInterval(updateClock, 500);
updateClock();

// ===== POLL =====
async function pollStats() {
    try { const r = await fetch('/api/stats'); updateStats(await r.json()); } catch(e) {}
}
setInterval(pollStats, 3000);
pollStats();

async function pollWeather() {
    try { const r = await fetch('/api/weather'); const d = await r.json(); updateStats({weather_text: d.text, weather_details: d.details}); } catch(e) {}
}
setTimeout(pollWeather, 1000);
setInterval(pollWeather, 60000);

// ===== CONNECT FIRST (before HUD so UI shows Online immediately) =====
connect();

// ===== HUD REACTOR =====
const canvas = document.getElementById('reactor');
const ctx = canvas ? canvas.getContext('2d') : null;
let lastTime = 0;

function resizeCanvas() {
    if (!canvas) return;
    const container = canvas.parentElement;
    const size = Math.min(container.clientWidth, container.clientHeight) * 0.9;
    if (size < 10) return;
    canvas.width = size;
    canvas.height = size;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
}

function hexToRgb(hex) {
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    return [r, g, b];
}

function blend(fg, bg, t) {
    const [fr, fg2, fb] = hexToRgb(fg);
    const [br, bg2, bb] = hexToRgb(bg);
    return `rgb(${Math.round(br + (fr - br) * t)},${Math.round(bg2 + (fg2 - bg2) * t)},${Math.round(bb + (fb - bb) * t)})`;
}

function drawHUD(timestamp) {
    if (!ctx) return;
    if (!lastTime) lastTime = timestamp;
    const dt = (timestamp - lastTime) / 16.67;
    lastTime = timestamp;
    animPhase = (animPhase + 1 * dt) % 360;

    const target = speaking ? 1.0 : 0.0;
    eqEnergy += (target - eqEnergy) * (target > eqEnergy ? 0.2 : 0.05) * dt;

    const w = canvas.width, h = canvas.height;
    if (w < 10 || h < 10) { requestAnimationFrame(drawHUD); return; }
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2, cy = h * 0.45, base = Math.min(w, h) * 0.22, e = Math.max(0, Math.min(1, eqEnergy));
    const t = (animPhase * Math.PI) / 180;

    function drawDashedRing(r, width, color, dashes, offsetAngle) {
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.setLineDash(dashes);
        ctx.lineDashOffset = offsetAngle || 0;
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // Outer dotted ring
    drawDashedRing(base * 1.8, 1, blend('#35d6ff', '#050a12', 0.8), [4, 8], -t * 10);

    // Outer bar visualizer (120 bars)
    const numBars = 120;
    for (let i = 0; i < numBars; i++) {
        const ang = (i / numBars) * Math.PI * 2 + t * 0.5;
        const wave = 0.5 + 0.5 * Math.sin(t * 3 + i * 0.2) * Math.cos(t * 2 + i * 0.1);
        const length = base * 0.1 + base * 0.3 * wave * e;
        const r1 = base * 1.5;
        const r2 = base * 1.5 + length;

        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(ang) * r1, cy + Math.sin(ang) * r1);
        ctx.lineTo(cx + Math.cos(ang) * r2, cy + Math.sin(ang) * r2);
        ctx.strokeStyle = blend('#11b0ff', '#050a12', 0.3 + 0.7 * e * wave);
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    // Mid rings
    drawDashedRing(base * 1.35, 3, '#11b0ff', [80, 20, 20, 20], t * 30);
    drawDashedRing(base * 1.25, 1, blend('#35d6ff', '#050a12', 0.6), [5, 5], -t * 20);

    // Inner bar visualizer (60 bars)
    const innerBars = 60;
    for (let i = 0; i < innerBars; i++) {
        const ang = (i / innerBars) * Math.PI * 2 - t;
        const wave = 0.5 + 0.5 * Math.sin(t * 5 + i * 0.5);
        const length = base * 0.05 + base * 0.2 * wave * e;
        const r1 = base * 1.0;
        const r2 = base * 1.0 + length;

        ctx.beginPath();
        ctx.moveTo(cx + Math.cos(ang) * r1, cy + Math.sin(ang) * r1);
        ctx.lineTo(cx + Math.cos(ang) * r2, cy + Math.sin(ang) * r2);
        ctx.strokeStyle = '#35d6ff';
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    // Inner core rings
    drawDashedRing(base * 0.8, 2, blend('#11b0ff', '#050a12', 0.2), [10, 5], t * 40);
    drawDashedRing(base * 0.7, 4, '#11b0ff', [40, 10, 5, 10], -t * 50);

    // Center circle
    ctx.beginPath();
    ctx.arc(cx, cy, base * 0.4, 0, Math.PI * 2);
    ctx.strokeStyle = '#35d6ff';
    ctx.lineWidth = 1 + e * 2;
    ctx.stroke();

    // Center fill
    ctx.beginPath();
    ctx.arc(cx, cy, base * 0.35, 0, Math.PI * 2);
    ctx.fillStyle = blend('#11b0ff', '#050a12', Math.max(0.9, 1 - e));
    ctx.fill();

    requestAnimationFrame(drawHUD);
}

if (canvas) {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    requestAnimationFrame(drawHUD);
}
