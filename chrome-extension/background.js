/**
 * Outreach 백그라운드 서비스 워커
 * 팝업 <-> 콘텐츠 스크립트 간 메시지 중계 및 API 호출
 */

// --- 메시지 리스너 ---
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  switch (msg.type) {
    case 'START_DM_SENDING':
      forwardToInstagramTab(msg);
      break;

    case 'STOP_DM_SENDING':
      forwardToInstagramTab(msg);
      break;

    case 'DM_RESULT':
      handleDmResult(msg.data);
      break;

    case 'DM_PROGRESS':
    case 'DM_COMPLETE':
    case 'DM_ERROR':
    case 'DM_LOG_UPDATE':
      // 팝업으로 전달
      chrome.runtime.sendMessage(msg).catch(() => {});
      break;

    case 'GET_DM_QUEUE':
      fetchDmQueue().then(sendResponse).catch((err) => sendResponse({ error: err.message }));
      return true; // async response

    case 'API_GET':
      apiWithAuth('GET', msg.path).then(sendResponse).catch((err) => sendResponse({ error: err.message }));
      return true;

    case 'API_POST':
      apiWithAuth('POST', msg.path, msg.data).then(sendResponse).catch((err) => sendResponse({ error: err.message }));
      return true;
  }
});

// --- Instagram 탭에 메시지 전달 ---
async function forwardToInstagramTab(msg) {
  try {
    const tabs = await chrome.tabs.query({ url: 'https://www.instagram.com/*' });
    if (tabs.length === 0) {
      // 인스타그램 탭이 없으면 열기
      const tab = await chrome.tabs.create({ url: 'https://www.instagram.com/direct/inbox/' });
      // 탭 로딩 완료 후 메시지 전송
      chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
        if (tabId === tab.id && info.status === 'complete') {
          chrome.tabs.onUpdated.removeListener(listener);
          chrome.tabs.sendMessage(tab.id, msg).catch(() => {});
        }
      });
    } else {
      chrome.tabs.sendMessage(tabs[0].id, msg).catch(() => {});
    }
  } catch (err) {
    console.error('Failed to forward message to Instagram tab:', err);
  }
}

// --- DM 결과 처리 ---
async function handleDmResult(result) {
  // 서버에 결과 보고
  try {
    await apiWithAuth('POST', '/api/chrome/dm-result', result);
  } catch (err) {
    console.error('Failed to report DM result:', err);
  }

  // 로컬 로그 업데이트
  const data = await chrome.storage.local.get('dmLog');
  const logs = data.dmLog || [];
  logs.push({
    target: result.target_id,
    username: result.username,
    success: result.success,
    timestamp: new Date().toISOString(),
    error: result.error || null,
  });
  // 최근 100건만 유지
  if (logs.length > 100) logs.splice(0, logs.length - 100);
  await chrome.storage.local.set({ dmLog: logs });

  // 팝업에 로그 업데이트 알림
  chrome.runtime.sendMessage({ type: 'DM_LOG_UPDATE' }).catch(() => {});

  // 배지 업데이트
  updateBadge();
}

// --- 배지 업데이트 ---
async function updateBadge() {
  try {
    const queue = await fetchDmQueue();
    const count = queue.queue_size ?? queue.targets?.length ?? 0;
    const text = count > 0 ? String(count) : '';
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color: '#2563eb' });
  } catch {
    chrome.action.setBadgeText({ text: '' });
  }
}

// --- API 호출 헬퍼 ---
async function apiWithAuth(method, path, body = null) {
  const data = await chrome.storage.local.get(['serverUrl', 'authToken']);
  const serverUrl = (data.serverUrl || 'http://localhost:8000').replace(/\/+$/, '');
  const token = data.authToken;
  const url = `${serverUrl}${path}`;

  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (body && method !== 'GET') {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  if (response.status === 401) {
    await chrome.storage.local.remove(['authToken']);
    throw new Error('인증 만료');
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `HTTP ${response.status}`);
  }
  return response.json();
}

async function fetchDmQueue() {
  return apiWithAuth('GET', '/api/chrome/dm-queue');
}

// --- 확장 설치 시 ---
chrome.runtime.onInstalled.addListener(() => {
  console.log('Outreach DM 확장 프로그램이 설치되었습니다.');
  updateBadge();
});

// --- 주기적 배지 업데이트 (5분마다) ---
chrome.alarms.create('updateBadge', { periodInMinutes: 5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'updateBadge') {
    updateBadge();
  }
});
