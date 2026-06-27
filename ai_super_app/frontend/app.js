const API_BASE = 'http://localhost:8000';

const state = {
  token: localStorage.getItem('ai_token') || null,
  username: localStorage.getItem('ai_username') || null,
  currentChatId: null,
  currentPage: 'chat',
};

// ===== DOM =====
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ===== API =====
async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    logout();
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  return res.json();
}

// ===== TOAST =====
function showToast(message, type = 'info') {
  const container = $('#toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ===== AUTH =====
$('#login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = $('#login-btn');
  const username = $('#username').value;
  const password = $('#password').value;
  const errorEl = $('#login-error');

  btn.disabled = true;
  btn.querySelector('.btn-text').classList.add('hidden');
  btn.querySelector('.btn-loader').classList.remove('hidden');
  errorEl.classList.add('hidden');

  try {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }

    const data = await res.json();
    state.token = data.access_token;
    state.username = data.username;
    localStorage.setItem('ai_token', data.access_token);
    localStorage.setItem('ai_username', data.username);

    $('#user-display-name').textContent = data.username;
    $('#user-display-role').textContent = data.is_admin ? 'مدير' : 'مستخدم';

    showScreen('app');
    showToast('تم تسجيل الدخول بنجاح', 'success');
    loadChats();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-text').classList.remove('hidden');
    btn.querySelector('.btn-loader').classList.add('hidden');
  }
});

function logout() {
  state.token = null;
  state.username = null;
  state.currentChatId = null;
  localStorage.removeItem('ai_token');
  localStorage.removeItem('ai_username');
  showScreen('login');
  showToast('تم تسجيل الخروج', 'info');
}

$('#logout-btn').addEventListener('click', logout);

// ===== SCREENS =====
function showScreen(name) {
  $$('.screen').forEach((s) => s.classList.remove('active'));
  if (name === 'login') {
    $('#login-screen').classList.add('active');
    $('#login-screen').style.display = 'flex';
    $('#app-screen').classList.remove('active');
    $('#app-screen').style.display = 'none';
  } else {
    $('#login-screen').classList.remove('active');
    $('#login-screen').style.display = 'none';
    $('#app-screen').classList.add('active');
    $('#app-screen').style.display = 'flex';
  }
}

// ===== NAVIGATION =====
$$('.nav-item').forEach((item) => {
  item.addEventListener('click', () => {
    const page = item.dataset.page;
    switchPage(page);
  });
});

function switchPage(page) {
  state.currentPage = page;
  $$('.nav-item').forEach((n) => n.classList.remove('active'));
  $(`.nav-item[data-page="${page}"]`).classList.add('active');
  $$('.page').forEach((p) => p.classList.remove('active'));
  $(`#page-${page}`).classList.add('active');

  const titles = { chat: 'المحادثة', image: 'توليد الصور', video: 'توليد الفيديو', web: 'تصفح الويب', vpn: 'حالة VPN' };
  $('#page-title').textContent = titles[page] || page;
  $('#new-chat-btn').style.display = page === 'chat' ? '' : 'none';

  if (page === 'vpn') loadVPNStatus();

  if (window.innerWidth < 769) closeSidebar();
}

// ===== SIDEBAR =====
$('#menu-btn').addEventListener('click', () => $('#sidebar').classList.add('open'));
$('#close-sidebar').addEventListener('click', closeSidebar);
function closeSidebar() { $('#sidebar').classList.remove('open'); }

// ===== CHAT =====
$('#new-chat-btn').addEventListener('click', () => {
  state.currentChatId = null;
  const container = $('#chat-messages');
  container.innerHTML = `
    <div class="welcome-message">
      <div class="welcome-icon">🤖</div>
      <h2>مرحبا بك في AI Super App</h2>
      <p>اختر أي شيء تريده وسأساعدك</p>
      <div class="quick-actions">
        <button class="quick-btn" data-prompt="اكتب لي كود Python لحساب الفيبوناتشي">💻 اكتب كود</button>
        <button class="quick-btn" data-prompt="اكتب لي قصة قصيرة عن الفضاء">📝 اكتب قصة</button>
        <button class="quick-btn" data-prompt="حلل لي مميزات وعيوب الذكاء الاصطناعي">🔍 تحليل</button>
        <button class="quick-btn" data-prompt="اشرح لي الحوسبة الكمية بطريقة بسيطة">🧠 اشرح مفهوم</button>
      </div>
    </div>`;
  bindQuickButtons();
  switchPage('chat');
});

function bindQuickButtons() {
  $$('.quick-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      $('#chat-input').value = btn.dataset.prompt;
      $('#chat-form').dispatchEvent(new Event('submit'));
    });
  });
}
bindQuickButtons();

$('#chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('#chat-input');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  input.style.height = 'auto';

  const container = $('#chat-messages');
  const welcome = container.querySelector('.welcome-message');
  if (welcome) welcome.remove();

  appendMessage('user', message);

  const typingEl = appendMessage('assistant', '', true);

  try {
    const result = await api('/chat/send', {
      method: 'POST',
      body: JSON.stringify({
        message,
        chat_id: state.currentChatId,
        prefer_offline: $('#offline-toggle').checked,
      }),
    });

    state.currentChatId = result.chat_id;

    typingEl.remove();
    appendMessage('assistant', result.response, false, result.model_used, result.latency_ms);

    $('#model-badge').textContent = result.model_used;
    loadChats();
  } catch (err) {
    typingEl.remove();
    appendMessage('assistant', `خطأ: ${err.message}`);
    showToast(err.message, 'error');
  }
});

function appendMessage(role, content, isTyping = false, model = '', latency = 0) {
  const container = $('#chat-messages');
  const div = document.createElement('div');
  div.className = `message ${role}${isTyping ? ' typing' : ''}`;

  const avatar = role === 'user' ? '👤' : '🤖';
  let metaHTML = '';
  if (model) {
    metaHTML = `<div class="message-meta">${model} • ${Math.round(latency)}ms</div>`;
  }

  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div>
      <div class="message-bubble">${isTyping ? '' : escapeHtml(content)}</div>
      ${metaHTML}
    </div>`;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// Auto-resize textarea
$('#chat-input').addEventListener('input', function () {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

$('#chat-input').addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    $('#chat-form').dispatchEvent(new Event('submit'));
  }
});

// Load chats list
async function loadChats() {
  try {
    const data = await api('/chat/chats');
    const list = $('#chat-list');
    list.innerHTML = '';
    data.chats.forEach((chat) => {
      const item = document.createElement('div');
      item.className = 'chat-list-item';
      item.innerHTML = `
        <span class="chat-title">${escapeHtml(chat.title)}</span>
        <button class="chat-delete" data-id="${chat.id}" title="حذف">🗑</button>`;
      item.addEventListener('click', (e) => {
        if (e.target.classList.contains('chat-delete')) return;
        loadChatHistory(chat.id);
      });
      item.querySelector('.chat-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteChat(chat.id);
      });
      list.appendChild(item);
    });
  } catch (err) {
    /* ignore */
  }
}

async function loadChatHistory(chatId) {
  try {
    state.currentChatId = chatId;
    const data = await api(`/chat/history/${chatId}`);
    const container = $('#chat-messages');
    container.innerHTML = '';
    data.messages.forEach((msg) => {
      appendMessage(msg.role, msg.content, false, msg.model_used || '');
    });
    switchPage('chat');
  } catch (err) {
    showToast('فشل تحميل المحادثة', 'error');
  }
}

async function deleteChat(chatId) {
  try {
    await api(`/chat/${chatId}`, { method: 'DELETE' });
    if (state.currentChatId === chatId) {
      state.currentChatId = null;
      $('#new-chat-btn').click();
    }
    loadChats();
    showToast('تم حذف المحادثة', 'success');
  } catch (err) {
    showToast('فشل حذف المحادثة', 'error');
  }
}

// ===== IMAGE GENERATION =====
$('#image-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector('.btn');
  btn.disabled = true;
  btn.querySelector('.btn-text').classList.add('hidden');
  btn.querySelector('.btn-loader').classList.remove('hidden');

  try {
    const result = await api('/generate/image', {
      method: 'POST',
      body: JSON.stringify({
        prompt: $('#image-prompt').value,
        size: $('#image-size').value,
        style: $('#image-style').value || null,
      }),
    });

    const resultEl = $('#image-result');
    resultEl.classList.remove('hidden');

    const output = $('#image-output');
    if (result.result_data && result.result_data !== 'placeholder_local_generation') {
      output.innerHTML = `<img src="data:image/png;base64,${result.result_data}" alt="Generated" />`;
    } else {
      output.innerHTML = `<div class="placeholder-img">🎨</div>`;
    }

    $('#image-meta').innerHTML = `
      <span>المزود: ${result.provider}</span>
      <span>الوقت: ${result.generation_time.toFixed(2)}s</span>
      <span>النوع: ${result.type}</span>`;

    showToast('تم توليد الصورة بنجاح', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-text').classList.remove('hidden');
    btn.querySelector('.btn-loader').classList.add('hidden');
  }
});

// ===== VIDEO GENERATION =====
$('#video-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector('.btn');
  btn.disabled = true;
  btn.querySelector('.btn-text').classList.add('hidden');
  btn.querySelector('.btn-loader').classList.remove('hidden');

  try {
    const result = await api('/generate/video', {
      method: 'POST',
      body: JSON.stringify({
        prompt: $('#video-prompt').value,
        duration: parseInt($('#video-duration').value),
        resolution: $('#video-resolution').value,
        style: $('#video-style').value || null,
      }),
    });

    const resultEl = $('#video-result');
    resultEl.classList.remove('hidden');

    const output = $('#video-output');
    if (result.result_url && result.result_url !== 'placeholder_local_video_generation') {
      output.innerHTML = `<video src="${result.result_url}" controls style="width:100%;border-radius:12px;"></video>`;
    } else {
      output.innerHTML = `<div class="placeholder-img">🎬</div>`;
    }

    $('#video-meta').innerHTML = `
      <span>المزود: ${result.provider}</span>
      <span>الوقت: ${result.generation_time.toFixed(2)}s</span>`;

    showToast('تم توليد الفيديو بنجاح', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-text').classList.remove('hidden');
    btn.querySelector('.btn-loader').classList.add('hidden');
  }
});

// ===== WEB SCRAPER =====
$('#web-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector('.btn');
  btn.disabled = true;
  btn.querySelector('.btn-text').classList.add('hidden');
  btn.querySelector('.btn-loader').classList.remove('hidden');

  try {
    const result = await api('/web/scrape', {
      method: 'POST',
      body: JSON.stringify({
        url: $('#web-url').value,
        type: $('#web-type').value,
        extract_images: $('#web-images').checked,
        extract_links: $('#web-links').checked,
      }),
    });

    const resultEl = $('#web-result');
    resultEl.classList.remove('hidden');

    const output = $('#web-output');
    let html = '';

    if (result.title) html += `<div class="web-title">${escapeHtml(result.title)}</div>`;

    html += '<div class="web-meta-info">';
    if (result.proxy_used) html += `<span class="web-meta-tag">بروكسي: ${result.proxy_used}</span>`;
    if (result.latency_ms) html += `<span class="web-meta-tag">الوقت: ${Math.round(result.latency_ms)}ms</span>`;
    if (result.reading_time) html += `<span class="web-meta-tag">وقت القراءة: ${result.reading_time} دقيقة</span>`;
    if (result.author) html += `<span class="web-meta-tag">الكاتب: ${result.author}</span>`;
    html += '</div>';

    if (result.content) html += `<div style="margin-top:12px">${escapeHtml(result.content).substring(0, 3000)}</div>`;
    if (result.markdown) html += `<div style="margin-top:12px">${escapeHtml(result.markdown).substring(0, 3000)}</div>`;
    if (result.description) html += `<div style="margin-top:12px"><strong>الوصف:</strong> ${escapeHtml(result.description)}</div>`;
    if (result.price) html += `<div style="margin-top:8px"><strong>السعر:</strong> ${escapeHtml(result.price)} ${result.currency || ''}</div>`;

    output.innerHTML = html;
    showToast('تم سحب المحتوى بنجاح', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-text').classList.remove('hidden');
    btn.querySelector('.btn-loader').classList.add('hidden');
  }
});

// ===== VPN =====
async function loadVPNStatus() {
  try {
    const data = await api('/vpn/status');
    $('#vpn-total').textContent = data.total_proxies;
    $('#vpn-active').textContent = data.active_proxies;
    $('#vpn-failed').textContent = data.failed_proxies;
    $('#vpn-requests').textContent = data.total_requests;

    const list = $('#vpn-proxies');
    list.innerHTML = '';

    const flags = { US: '🇺🇸', EU: '🇪🇺', JP: '🇯🇵', UK: '🇬🇧', DE: '🇩🇪', FR: '🇫🇷' };

    data.proxies.forEach((proxy) => {
      const card = document.createElement('div');
      card.className = 'proxy-card';
      card.innerHTML = `
        <div class="proxy-info">
          <span class="proxy-flag">${flags[proxy.country] || '🌍'}</span>
          <div>
            <div class="proxy-host">${proxy.host}:${proxy.port}</div>
            <div class="proxy-detail">${proxy.country}</div>
          </div>
        </div>
        <div class="proxy-stats">
          <div class="proxy-stat">
            <span class="proxy-stat-value">${Math.round(proxy.latency_ms)}ms</span>
            <span class="proxy-stat-label">التأخير</span>
          </div>
          <div class="proxy-stat">
            <span class="proxy-stat-value">${(proxy.success_rate * 100).toFixed(0)}%</span>
            <span class="proxy-stat-label">النجاح</span>
          </div>
        </div>
        <span class="proxy-status ${proxy.is_active ? 'active' : 'inactive'}">
          ${proxy.is_active ? 'نشط' : 'متوقف'}
        </span>`;
      list.appendChild(card);
    });
  } catch (err) {
    showToast('فشل تحميل حالة VPN', 'error');
  }
}

$('#vpn-refresh-btn').addEventListener('click', loadVPNStatus);

$('#vpn-rotate-btn').addEventListener('click', async () => {
  try {
    const data = await api('/vpn/rotate', { method: 'POST' });
    if (data.success) {
      showToast(`تم التدوير: ${data.proxy.host} (${data.proxy.country})`, 'success');
      loadVPNStatus();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
});

$('#vpn-test-btn').addEventListener('click', async () => {
  showToast('جاري اختبار الاتصال...', 'info');
  try {
    const data = await api('/vpn/test', { method: 'POST' });
    const resultEl = $('#vpn-test-result');
    resultEl.classList.remove('hidden');
    $('#vpn-test-output').innerHTML = `
      <div style="padding:12px">
        <div><strong>الحالة:</strong> ${data.success ? '✅ ناجح' : '❌ فاشل'}</div>
        <div><strong>البروكسي:</strong> ${data.proxy_used || 'N/A'}</div>
        <div><strong>التأخير:</strong> ${data.latency_ms ? Math.round(data.latency_ms) + 'ms' : 'N/A'}</div>
      </div>`;
    showToast('تم اختبار الاتصال', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// ===== INIT =====
function init() {
  if (state.token) {
    showScreen('app');
    $('#user-display-name').textContent = state.username || 'User';
    loadChats();
  } else {
    showScreen('login');
  }
}

init();
