/**
 * Outreach 팝업 UI 로직
 */

const $ = (sel) => document.querySelector(sel);

// DOM 요소
const loginSection = $('#login-section');
const mainSection = $('#main-section');
const loginBtn = $('#login-btn');
const logoutBtn = $('#logout-btn');
const loginError = $('#login-error');
const serverUrlInput = $('#server-url');
const emailInput = $('#email');
const passwordInput = $('#password');
const startBtn = $('#start-btn');
const stopBtn = $('#stop-btn');
const dmCountEl = $('#dm-count');
const dmLimitEl = $('#dm-limit');
const queueSizeEl = $('#queue-size');
const connectionStatus = $('#connection-status');
const connectionText = $('#connection-text');
const sendingStatus = $('#sending-status');
const sendingText = $('#sending-text');
const progressFill = $('#progress-fill');
const logList = $('#log-list');

// 상태
let isSending = false;

// --- 초기화 ---
document.addEventListener('DOMContentLoaded', async () => {
  // 저장된 서버 URL 복원
  const stored = await chrome.storage.local.get(['serverUrl', 'authToken']);
  if (stored.serverUrl) {
    serverUrlInput.value = stored.serverUrl;
  }

  if (stored.authToken) {
    showMain();
    await refreshDashboard();
  } else {
    showLogin();
  }

  // 발송 상태 확인
  const state = await chrome.storage.local.get('dmSending');
  if (state.dmSending) {
    isSending = true;
    showSendingUI();
  }
});

// --- 로그인 ---
loginBtn.addEventListener('click', async () => {
  const serverUrl = serverUrlInput.value.trim();
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!serverUrl || !email || !password) {
    showError('모든 필드를 입력해주세요.');
    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = '로그인 중...';
  hideError();

  try {
    await OutreachAPI.login(serverUrl, email, password);
    showMain();
    await refreshDashboard();
  } catch (err) {
    showError(err.message);
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = '로그인';
  }
});

// 엔터 키로 로그인
passwordInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') loginBtn.click();
});

// --- 로그아웃 ---
logoutBtn.addEventListener('click', async () => {
  await OutreachAPI.clearAuth();
  showLogin();
});

// --- 발송 시작 ---
startBtn.addEventListener('click', async () => {
  isSending = true;
  await chrome.storage.local.set({ dmSending: true });
  showSendingUI();

  // content script에 시작 메시지 전송
  chrome.runtime.sendMessage({ type: 'START_DM_SENDING' });
});

// --- 발송 중지 ---
stopBtn.addEventListener('click', async () => {
  isSending = false;
  await chrome.storage.local.set({ dmSending: false });
  hideSendingUI();

  // content script에 중지 메시지 전송
  chrome.runtime.sendMessage({ type: 'STOP_DM_SENDING' });
});

// --- 대시보드 새로고침 ---
async function refreshDashboard() {
  try {
    const queue = await OutreachAPI.getDmQueue();
    queueSizeEl.textContent = queue.queue_size ?? queue.targets?.length ?? 0;
    dmCountEl.textContent = queue.today_sent ?? 0;
    dmLimitEl.textContent = queue.daily_limit ?? 15;

    connectionStatus.className = 'status-dot status-connected';
    connectionText.textContent = '서버 연결됨';

    // 발송 가능 여부 체크
    const todaySent = queue.today_sent ?? 0;
    const dailyLimit = queue.daily_limit ?? 15;
    if (todaySent >= dailyLimit) {
      startBtn.disabled = true;
      startBtn.textContent = '일일 한도 도달';
    }
  } catch (err) {
    connectionStatus.className = 'status-dot status-disconnected';
    connectionText.textContent = '서버 연결 실패';
    console.error('Dashboard refresh failed:', err);
  }

  // 최근 로그 불러오기
  await refreshLog();
}

// --- 최근 발송 로그 ---
async function refreshLog() {
  const data = await chrome.storage.local.get('dmLog');
  const logs = (data.dmLog || []).slice(-5).reverse();

  if (logs.length === 0) {
    logList.innerHTML = '<p class="log-empty">발송 내역이 없습니다.</p>';
    return;
  }

  logList.innerHTML = logs.map((log) => {
    const statusClass = log.success ? 'log-status-success' : 'log-status-fail';
    const statusText = log.success ? '성공' : '실패';
    const time = new Date(log.timestamp).toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
    return `
      <div class="log-item">
        <span class="log-name">${escapeHtml(log.username || log.target)}</span>
        <span class="${statusClass}">${statusText}</span>
        <span class="log-time">${time}</span>
      </div>
    `;
  }).join('');
}

// --- UI 헬퍼 ---
function showLogin() {
  loginSection.classList.remove('hidden');
  mainSection.classList.add('hidden');
}

function showMain() {
  loginSection.classList.add('hidden');
  mainSection.classList.remove('hidden');
}

function showSendingUI() {
  startBtn.classList.add('hidden');
  stopBtn.classList.remove('hidden');
  sendingStatus.classList.remove('hidden');
  sendingText.textContent = '발송 중...';
}

function hideSendingUI() {
  startBtn.classList.remove('hidden');
  stopBtn.classList.add('hidden');
  sendingStatus.classList.add('hidden');
}

function showError(msg) {
  loginError.textContent = msg;
  loginError.classList.remove('hidden');
}

function hideError() {
  loginError.classList.add('hidden');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// --- 메시지 리스너 (background/content에서 오는 상태 업데이트) ---
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'DM_PROGRESS') {
    sendingText.textContent = `발송 중... (${msg.current}/${msg.total})`;
    const pct = msg.total > 0 ? (msg.current / msg.total) * 100 : 0;
    progressFill.style.width = `${pct}%`;
    dmCountEl.textContent = msg.todaySent ?? dmCountEl.textContent;
  }

  if (msg.type === 'DM_COMPLETE') {
    isSending = false;
    hideSendingUI();
    refreshDashboard();
  }

  if (msg.type === 'DM_ERROR') {
    isSending = false;
    hideSendingUI();
    sendingText.textContent = `오류: ${msg.message}`;
    sendingStatus.classList.remove('hidden');
  }

  if (msg.type === 'DM_LOG_UPDATE') {
    refreshLog();
  }
});
