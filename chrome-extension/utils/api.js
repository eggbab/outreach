/**
 * Outreach API 유틸리티
 * chrome.storage.local에 저장된 서버 URL과 인증 토큰을 사용하여 API 호출
 */

const OutreachAPI = (() => {
  async function getServerUrl() {
    const data = await chrome.storage.local.get('serverUrl');
    return (data.serverUrl || 'http://localhost:8000').replace(/\/+$/, '');
  }

  async function getAuthToken() {
    const data = await chrome.storage.local.get('authToken');
    return data.authToken || null;
  }

  async function setAuth(serverUrl, token) {
    await chrome.storage.local.set({ serverUrl, authToken: token });
  }

  async function clearAuth() {
    await chrome.storage.local.remove(['authToken']);
  }

  async function apiRequest(method, path, body = null) {
    const serverUrl = await getServerUrl();
    const token = await getAuthToken();
    const url = `${serverUrl}${path}`;

    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const options = { method, headers };
    if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    if (response.status === 401) {
      await clearAuth();
      throw new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
    }
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || errData.message || `요청 실패 (${response.status})`);
    }
    return response.json();
  }

  async function apiGet(path) {
    return apiRequest('GET', path);
  }

  async function apiPost(path, data) {
    return apiRequest('POST', path, data);
  }

  // --- 구체적 API 함수들 ---

  async function login(serverUrl, email, password) {
    const url = `${serverUrl.replace(/\/+$/, '')}/api/auth/login`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || err.message || '로그인 실패');
    }
    const data = await response.json();
    await setAuth(serverUrl, data.token || data.access_token);
    return data;
  }

  async function getDmQueue() {
    return apiGet('/api/chrome/dm-queue');
  }

  async function reportDmResult(result) {
    return apiPost('/api/chrome/dm-result', result);
  }

  return {
    getServerUrl,
    getAuthToken,
    setAuth,
    clearAuth,
    apiGet,
    apiPost,
    login,
    getDmQueue,
    reportDmResult,
  };
})();
