/**
 * Instagram DM 자동 발송 콘텐츠 스크립트
 *
 * 서버가 준 대기열(각 대상별 개인화·변형 완료된 message)을 받아,
 * username → 내부 PK를 인스타 공개 API로 해석한 뒤 DM을 순차 발송한다.
 * 본인 브라우저의 로그인 세션(credentials: include)을 사용 — 서버는 자격증명을 갖지 않는다.
 */

(() => {
  // 서버 안전 정책으로 덮어씌워짐 (큐 응답). 아래는 폴백 기본값.
  let DELAY_MIN = 180;  // 최소 대기(초)
  let DELAY_MAX = 480;  // 최대 대기(초)
  const IG_APP_ID = '936619743392459';
  const DM_API_URL = 'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/';
  const PROFILE_API = 'https://www.instagram.com/api/v1/users/web_profile_info/?username=';
  const NIGHT_START = 21;  // 21시 이후 발송 금지 (정보통신망법 §50③)
  const NIGHT_END = 8;     // 08시 이전 발송 금지

  let isRunning = false;
  let targets = [];
  let dailyLimit = 15;
  let hourlyLimit = 5;
  let nightBlock = true;
  let maxConsecutiveFailures = 3;
  let consecutiveFailures = 0;
  let todaySent = 0;
  let sentHistory = new Set();
  let hourlyTimestamps = [];  // 최근 1시간 발송 시각(ms) — 시간당 한도 계산용

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'START_DM_SENDING' && !isRunning) startSending();
    if (msg.type === 'STOP_DM_SENDING') stopSending('사용자 중지', /*isError=*/false);
  });

  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];
    for (const script of document.querySelectorAll('script')) {
      const m = (script.textContent || '').match(/"csrf_token":"([^"]+)"/);
      if (m) return m[1];
    }
    return null;
  }

  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function randomDelay() {
    return (DELAY_MIN + Math.random() * (DELAY_MAX - DELAY_MIN)) * 1000;
  }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // username → 내부 PK 해석 (인스타 공개 프로필 API)
  async function resolvePk(username) {
    const resp = await fetch(PROFILE_API + encodeURIComponent(username), {
      headers: { 'X-IG-App-ID': IG_APP_ID, 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'include',
    });
    if (resp.status === 404) throw new Error('ACCOUNT_NOT_FOUND');
    if (resp.status === 429) throw new Error('RATE_LIMITED');
    if (resp.status === 401 || resp.status === 403) throw new Error('LOGIN_REQUIRED');
    if (!resp.ok) throw new Error(`profile_lookup_${resp.status}`);
    const data = await resp.json().catch(() => null);
    const pk = data?.data?.user?.id;
    if (!pk) throw new Error('ACCOUNT_NOT_FOUND');
    return String(pk);
  }

  // 인스타 응답에서 계정 차단/체크포인트 등 '전체 중단' 신호 판별
  function detectHardStop(status, result) {
    if (status === 429) return 'rate_limited';
    if (status === 403 || status === 401) return 'login_or_block';
    const r = result || {};
    if (r.spam === true) return 'spam_flag';
    if (r.message === 'feedback_required' || r.feedback_required) return 'feedback_required';
    if (r.require_login || r.checkpoint_url || r.challenge) return 'checkpoint';
    if (typeof r.message === 'string' && /checkpoint|challenge|block/i.test(r.message)) return 'checkpoint';
    return null;
  }

  async function sendDm(userPk, messageText) {
    const csrfToken = getCsrfToken();
    if (!csrfToken) throw new Error('LOGIN_REQUIRED');

    const formData = new URLSearchParams();
    formData.append('recipient_users', JSON.stringify([[Number(userPk)]]));
    formData.append('message', messageText);
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

    let result = null;
    try { result = await response.json(); } catch { /* HTML 에러 페이지 등 */ }

    const hardStop = detectHardStop(response.status, result);
    if (hardStop) { const e = new Error('HARD_STOP'); e.reason = hardStop; throw e; }

    if (!response.ok || !result || result.status !== 'ok') {
      throw new Error((result && result.message) || `send_failed_${response.status}`);
    }
    return result;
  }

  async function startSending() {
    isRunning = true;
    const today = new Date().toISOString().slice(0, 10);
    const stored = await chrome.storage.local.get(['dmSentHistory', 'dmTodaySent', 'dmTodayDate', 'dmCooldownUntil']);

    // 차단 쿨다운 중이면 발송 금지
    if (stored.dmCooldownUntil && Date.now() < stored.dmCooldownUntil) {
      const mins = Math.ceil((stored.dmCooldownUntil - Date.now()) / 60000);
      stopSending(`인스타 제한 감지로 대기 중입니다. 약 ${mins}분 후 다시 시도하세요.`, true);
      return;
    }

    todaySent = stored.dmTodayDate === today ? (stored.dmTodaySent || 0) : 0;
    if (stored.dmTodayDate !== today) await chrome.storage.local.set({ dmTodayDate: today, dmTodaySent: 0 });
    // 오래된 이력은 자름 (최근 2000건 유지 — 무한 증가 방지)
    sentHistory = new Set((stored.dmSentHistory || []).slice(-2000));

    try {
      const resp = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'GET_DM_QUEUE' }, (r) => {
          if (r?.error) reject(new Error(r.error)); else resolve(r);
        });
      });
      targets = resp.targets || [];
      dailyLimit = resp.daily_limit || 15;
      todaySent = resp.sent_today != null ? resp.sent_today : todaySent;
      // 서버 안전 정책 적용
      hourlyLimit = resp.hourly_limit || hourlyLimit;
      if (resp.min_delay_seconds) DELAY_MIN = resp.min_delay_seconds;
      if (resp.max_delay_seconds) DELAY_MAX = resp.max_delay_seconds;
      if (resp.night_block != null) nightBlock = resp.night_block;
      if (resp.max_consecutive_failures) maxConsecutiveFailures = resp.max_consecutive_failures;
    } catch (err) {
      stopSending(`대기열 로드 실패: ${err.message}`, true);
      return;
    }

    // 야간 발송 차단 (정보통신망법 §50③ — 21~08시 광고성 정보 별도 동의 필요)
    if (nightBlock && isNightTime()) {
      stopSending('야간(밤 9시~오전 8시)에는 광고성 DM 발송이 제한됩니다. 낮에 다시 시작하세요.', true);
      return;
    }

    targets = targets.filter((t) => !sentHistory.has(String(t.prospect_id)));
    if (targets.length === 0) { notifyComplete('발송할 새 대상이 없습니다.'); isRunning = false; return; }

    consecutiveFailures = 0;
    let idx = 0;
    for (const target of targets) {
      if (!isRunning) break;
      if (todaySent >= dailyLimit) { notifyComplete(`오늘 안전 한도(${dailyLimit}건) 도달`); break; }
      // 야간 진입 시 중단 (발송 중 자정을 넘긴 경우)
      if (nightBlock && isNightTime()) { stopSending('야간 시간대 진입 — 계정 보호를 위해 발송을 멈춥니다.', true); return; }
      // 시간당 한도 — 도달 시 가장 오래된 발송 + 1시간까지 대기
      await enforceHourlyLimit(idx, targets.length);
      if (!isRunning) break;
      idx++;
      notifyProgress(idx, targets.length, `@${target.username} 처리 중`);

      try {
        let pk = target.instagram_pk;
        if (!pk) {
          pk = await resolvePk(target.username);
          await sleep(2000 + Math.random() * 3000);
        }

        await sendDm(pk, target.message);
        todaySent++;
        consecutiveFailures = 0;
        hourlyTimestamps.push(Date.now());
        sentHistory.add(String(target.prospect_id));
        await saveState(today);

        reportResult({
          prospect_id: target.prospect_id,
          status: 'success',
          message_body: target.message,
          instagram_pk: pk,
        });
        notifyProgress(idx, targets.length, `@${target.username} 발송 완료`);

        if (idx < targets.length && isRunning) {
          const d = randomDelay();
          notifyProgress(idx, targets.length, `다음까지 ${Math.round(d / 1000)}초 대기`);
          await sleep(d);
        }
      } catch (err) {
        if (err.message === 'HARD_STOP' || err.message === 'RATE_LIMITED' || err.message === 'LOGIN_REQUIRED') {
          // 계정 보호를 위해 전체 중단 + 쿨다운 (기본 6시간)
          const cooldown = Date.now() + 6 * 60 * 60 * 1000;
          await chrome.storage.local.set({ dmCooldownUntil: cooldown });
          reportResult({
            prospect_id: target.prospect_id, status: 'failed',
            error_message: err.reason || err.message, stop_reason: err.reason || err.message,
          });
          stopSending('인스타 제한 신호 감지 — 계정 보호를 위해 자동 중단(6시간 대기)', true);
          return;
        }
        // 개별 실패 (계정 없음/일시 오류) — 기록하고 계속
        consecutiveFailures++;
        reportResult({
          prospect_id: target.prospect_id, status: 'failed', error_message: err.message,
        });
        notifyProgress(idx, targets.length, `@${target.username} 실패: ${err.message}`);
        // 연속 실패가 임계 초과 → 계정/세션 이상 가능성 → 중단
        if (consecutiveFailures >= maxConsecutiveFailures) {
          stopSending(`연속 ${consecutiveFailures}회 실패 — 계정/세션 문제일 수 있어 발송을 멈춥니다. 인스타 로그인 상태를 확인하세요.`, true);
          return;
        }
        // 실패 후에도 짧게 쉬어 기계적 재시도 패턴 회피
        if (isRunning) await sleep(randomDelay());
      }
    }

    if (isRunning) notifyComplete('발송 완료');
    isRunning = false;
    await chrome.storage.local.set({ dmSending: false });
  }

  // 로컬 시각 기준 야간(21~08시) 여부
  function isNightTime() {
    const h = new Date().getHours();
    return h >= NIGHT_START || h < NIGHT_END;
  }

  // 시간당 한도 강제 — 최근 1시간 발송 수가 한도에 닿으면 가장 오래된 발송 +1시간까지 대기
  async function enforceHourlyLimit(idx, total) {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    hourlyTimestamps = hourlyTimestamps.filter((t) => t > oneHourAgo);
    if (hourlyTimestamps.length >= hourlyLimit) {
      const waitMs = hourlyTimestamps[0] + 60 * 60 * 1000 - Date.now();
      if (waitMs > 0) {
        const mins = Math.ceil(waitMs / 60000);
        notifyProgress(idx, total, `시간당 안전 한도(${hourlyLimit}건) 도달 — ${mins}분 대기`);
        // 야간 진입 방지를 위해 최대 대기는 15분 단위로 쪼개 확인
        const step = Math.min(waitMs, 15 * 60 * 1000);
        await sleep(step);
        if (isRunning) await enforceHourlyLimit(idx, total);
      }
    }
  }

  function stopSending(reason, isError) {
    isRunning = false;
    chrome.storage.local.set({ dmSending: false });
    if (isError) notifyError(reason); else notifyComplete(reason);
  }

  async function saveState(today) {
    await chrome.storage.local.set({
      dmSentHistory: Array.from(sentHistory).slice(-2000),
      dmTodaySent: todaySent,
      dmTodayDate: today,
    });
  }

  function reportResult(data) { chrome.runtime.sendMessage({ type: 'DM_RESULT', data }); }
  function notifyProgress(current, total, detail) {
    chrome.runtime.sendMessage({ type: 'DM_PROGRESS', current, total, todaySent, detail });
  }
  function notifyComplete(message) { chrome.runtime.sendMessage({ type: 'DM_COMPLETE', message, todaySent }); }
  function notifyError(message) { chrome.runtime.sendMessage({ type: 'DM_ERROR', message }); }

  console.log('[Outreach] Instagram DM 콘텐츠 스크립트 로드됨');
})();
