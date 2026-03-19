/**
 * Instagram DM 자동 발송 콘텐츠 스크립트
 * Instagram Private API를 통해 DM을 직접 전송
 */

(() => {
  // 설정
  const DELAY_MIN = 90;  // 최소 대기 시간 (초)
  const DELAY_MAX = 180; // 최대 대기 시간 (초)
  const IG_APP_ID = '936619743392459';
  const DM_API_URL = 'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/';

  // 상태
  let isRunning = false;
  let targets = [];
  let currentIndex = 0;
  let todaySent = 0;
  let dailyLimit = 15;
  let sentHistory = new Set(); // 중복 발송 방지

  // --- 메시지 리스너 ---
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'START_DM_SENDING') {
      if (!isRunning) {
        startSending();
      }
    }
    if (msg.type === 'STOP_DM_SENDING') {
      stopSending('사용자 중지');
    }
  });

  // --- CSRF 토큰 추출 ---
  function getCsrfToken() {
    // 쿠키에서 추출
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];

    // meta 태그에서 추출
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    // 페이지 소스에서 추출
    const scripts = document.querySelectorAll('script');
    for (const script of scripts) {
      const text = script.textContent;
      const csrfMatch = text.match(/"csrf_token":"([^"]+)"/);
      if (csrfMatch) return csrfMatch[1];
    }

    return null;
  }

  // --- UUID 생성 ---
  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  // --- 랜덤 딜레이 ---
  function randomDelay() {
    const seconds = DELAY_MIN + Math.random() * (DELAY_MAX - DELAY_MIN);
    return seconds * 1000;
  }

  // --- 딜레이 Promise ---
  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // --- 메시지 템플릿 치환 ---
  function renderMessage(template, target) {
    let message = template;
    message = message.replace(/\{company\}/g, target.company_name || target.username || '');
    message = message.replace(/\{name\}/g, target.name || target.company_name || '');
    message = message.replace(/\{username\}/g, target.username || '');
    return message;
  }

  // --- DM 전송 ---
  async function sendDm(target, messageText) {
    const csrfToken = getCsrfToken();
    if (!csrfToken) {
      throw new Error('CSRF 토큰을 찾을 수 없습니다. Instagram에 로그인되어 있는지 확인하세요.');
    }

    const userPk = target.instagram_pk || target.user_pk || target.pk;
    if (!userPk) {
      throw new Error(`사용자 PK가 없습니다: ${target.username}`);
    }

    const body = new URLSearchParams({
      recipient_users: JSON.stringify([userPk]),
      message: { text: messageText },
      client_context: generateUUID(),
      action: 'send_item',
    });

    // message 필드를 올바르게 설정 (URLSearchParams는 자동으로 toString하므로 직접 설정)
    const formData = new URLSearchParams();
    formData.append('recipient_users', JSON.stringify([userPk]));
    formData.append('message', JSON.stringify({ text: messageText }));
    formData.append('client_context', generateUUID());
    formData.append('action', 'send_item');

    const response = await fetch(DM_API_URL, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-IG-App-ID': IG_APP_ID,
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
      credentials: 'include',
    });

    const result = await response.json();

    // 스팸 감지
    if (result.spam || JSON.stringify(result).toLowerCase().includes('spam') ||
        JSON.stringify(result).toLowerCase().includes('feedback')) {
      throw new Error('SPAM_DETECTED');
    }

    if (result.status !== 'ok') {
      throw new Error(result.message || `전송 실패: ${JSON.stringify(result)}`);
    }

    return result;
  }

  // --- 발송 시작 ---
  async function startSending() {
    isRunning = true;

    // 발송 이력 복원
    const stored = await chrome.storage.local.get(['dmSentHistory', 'dmTodaySent', 'dmTodayDate']);
    const today = new Date().toISOString().slice(0, 10);

    if (stored.dmTodayDate === today) {
      todaySent = stored.dmTodaySent || 0;
    } else {
      todaySent = 0;
      await chrome.storage.local.set({ dmTodayDate: today, dmTodaySent: 0 });
    }

    sentHistory = new Set(stored.dmSentHistory || []);

    // 서버에서 대기열 가져오기
    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'GET_DM_QUEUE' }, (resp) => {
          if (resp?.error) reject(new Error(resp.error));
          else resolve(resp);
        });
      });

      targets = response.targets || [];
      dailyLimit = response.daily_limit || 15;

      if (targets.length === 0) {
        notifyComplete('대기열이 비어있습니다.');
        return;
      }
    } catch (err) {
      notifyError(`대기열 로드 실패: ${err.message}`);
      return;
    }

    // 이미 발송한 대상 필터링
    targets = targets.filter((t) => {
      const key = t.instagram_pk || t.user_pk || t.pk || t.username;
      return !sentHistory.has(String(key));
    });

    if (targets.length === 0) {
      notifyComplete('모든 대상에게 이미 발송 완료.');
      return;
    }

    console.log(`[Outreach] DM 발송 시작: ${targets.length}건, 오늘 발송: ${todaySent}/${dailyLimit}`);

    // 순차 발송
    currentIndex = 0;
    for (const target of targets) {
      if (!isRunning) break;
      if (todaySent >= dailyLimit) {
        notifyComplete('일일 발송 한도에 도달했습니다.');
        break;
      }

      currentIndex++;
      const messageTemplate = target.message_template || target.message || getDefaultTemplate();
      const messageText = renderMessage(messageTemplate, target);

      notifyProgress(currentIndex, targets.length);

      try {
        await sendDm(target, messageText);
        todaySent++;

        // 성공 기록
        const key = String(target.instagram_pk || target.user_pk || target.pk || target.username);
        sentHistory.add(key);
        await saveSentHistory();

        // 결과 보고
        reportResult({
          target_id: target.id,
          username: target.username,
          success: true,
        });

        console.log(`[Outreach] DM 발송 성공: @${target.username} (${currentIndex}/${targets.length})`);

        // 마지막이 아니면 딜레이
        if (currentIndex < targets.length && isRunning) {
          const delay = randomDelay();
          console.log(`[Outreach] 다음 발송까지 ${Math.round(delay / 1000)}초 대기`);
          notifyProgress(currentIndex, targets.length, `다음 발송까지 ${Math.round(delay / 1000)}초 대기`);
          await sleep(delay);
        }
      } catch (err) {
        if (err.message === 'SPAM_DETECTED') {
          console.error('[Outreach] 스팸 감지됨! 발송 중단.');
          reportResult({
            target_id: target.id,
            username: target.username,
            success: false,
            error: 'spam_detected',
          });
          stopSending('스팸 감지로 자동 중단');
          return;
        }

        console.error(`[Outreach] DM 발송 실패: @${target.username}`, err.message);
        reportResult({
          target_id: target.id,
          username: target.username,
          success: false,
          error: err.message,
        });
      }
    }

    if (isRunning) {
      notifyComplete('발송 완료');
    }
    isRunning = false;
    await chrome.storage.local.set({ dmSending: false });
  }

  // --- 발송 중지 ---
  function stopSending(reason) {
    isRunning = false;
    chrome.storage.local.set({ dmSending: false });
    console.log(`[Outreach] 발송 중지: ${reason}`);
    notifyError(reason);
  }

  // --- 발송 이력 저장 ---
  async function saveSentHistory() {
    const today = new Date().toISOString().slice(0, 10);
    await chrome.storage.local.set({
      dmSentHistory: Array.from(sentHistory),
      dmTodaySent: todaySent,
      dmTodayDate: today,
    });
  }

  // --- 결과 보고 ---
  function reportResult(result) {
    chrome.runtime.sendMessage({
      type: 'DM_RESULT',
      data: result,
    });
  }

  // --- 상태 알림 ---
  function notifyProgress(current, total, detail) {
    chrome.runtime.sendMessage({
      type: 'DM_PROGRESS',
      current,
      total,
      todaySent,
      detail: detail || `${current}/${total} 발송 중`,
    });
  }

  function notifyComplete(message) {
    chrome.runtime.sendMessage({
      type: 'DM_COMPLETE',
      message,
      todaySent,
    });
  }

  function notifyError(message) {
    chrome.runtime.sendMessage({
      type: 'DM_ERROR',
      message,
    });
  }

  // --- 기본 메시지 템플릿 ---
  function getDefaultTemplate() {
    return `안녕하세요, {company} 담당자님!

마트/슈퍼 업계 최대 커뮤니티 '마트마트'에서 연락드립니다.
22,000명 이상의 마트/슈퍼 사장님들이 활동하는 네이버 카페에 광고 파트너십을 제안드리고 싶습니다.

자세한 내용은 회신 부탁드립니다. 감사합니다!`;
  }

  console.log('[Outreach] Instagram DM 콘텐츠 스크립트 로드 완료');
})();
