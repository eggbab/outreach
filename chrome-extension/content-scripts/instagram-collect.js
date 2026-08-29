/**
 * Instagram 콜드 수집 콘텐츠 스크립트
 *
 * 서버 큐에서 '해시태그 검색어'를 받아, 사용자 본인 브라우저의 로그인 세션으로
 * 인스타 공개 API를 호출해 해당 해시태그 게시물의 작성자 계정을 모으고,
 * 각 계정의 프로필(소개글의 이메일·링크)을 읽어 서버로 돌려준다.
 *
 * DM 스크립트와 같은 안전 원칙:
 *  - 서버는 자격증명을 갖지 않는다 (credentials: include, 본인 세션 사용)
 *  - 사람 속도로 천천히, 요청 사이에 랜덤 지연
 *  - 차단 신호(429/checkpoint) 감지 시 즉시 중단
 *  - 서버가 크레딧을 차감하므로 과수집 방지는 서버가 관리
 *
 * ⚠️ 콜드 수집도 비공식 경로다. DM보다 읽기 위주라 부담은 낮지만
 *    리스크가 0은 아니다 — 소량·저빈도 권장.
 */

(() => {
  const IG_APP_ID = '936619743392459';
  const TAG_API = 'https://www.instagram.com/api/v1/tags/web_info/?tag_name=';
  const PROFILE_API = 'https://www.instagram.com/api/v1/users/web_profile_info/?username=';
  const DELAY_MIN = 4000;   // 프로필 조회 간 최소 지연(ms)
  const DELAY_MAX = 9000;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const jitter = () => DELAY_MIN + Math.random() * (DELAY_MAX - DELAY_MIN);

  let running = false;

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'START_INSTA_COLLECT' && !running) runCollect(msg.projectId, msg.apiBase, msg.token);
    if (msg.type === 'STOP_INSTA_COLLECT') running = false;
  });

  function headers() {
    return {
      'x-ig-app-id': IG_APP_ID,
      'x-requested-with': 'XMLHttpRequest',
    };
  }

  function isBlocked(status) {
    return status === 429 || status === 403 || status === 401;
  }

  // 해시태그 게시물에서 작성자 username 목록 수집
  async function fetchTagAuthors(tag, limit) {
    const resp = await fetch(TAG_API + encodeURIComponent(tag), {
      headers: headers(), credentials: 'include',
    });
    if (isBlocked(resp.status)) throw new Error('BLOCKED');
    if (!resp.ok) return [];
    const data = await resp.json().catch(() => ({}));
    return InstaParse.parseTagAuthors(data, limit);
  }

  // 프로필에서 연락처 추출
  async function fetchProfile(username) {
    const resp = await fetch(PROFILE_API + encodeURIComponent(username), {
      headers: headers(), credentials: 'include',
    });
    if (isBlocked(resp.status)) throw new Error('BLOCKED');
    if (!resp.ok) return null;
    const data = await resp.json().catch(() => ({}));
    return InstaParse.parseProfile(data, username);
  }

  async function post(apiBase, token, path, body) {
    return fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    });
  }

  async function runCollect(projectId, apiBase, token) {
    running = true;
    try {
      // 1) 큐에서 작업 받기
      const qResp = await fetch(`${apiBase}/api/chrome/insta-collect-queue?project_id=${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const { job } = await qResp.json();
      if (!job) { running = false; return; }

      const tag = job.keyword.replace(/\s+/g, '');
      let authors;
      try {
        authors = await fetchTagAuthors(tag, job.target_count);
      } catch (e) {
        await post(apiBase, token, '/api/chrome/insta-collect-result', {
          job_id: job.job_id, status: 'failed',
          message: e.message === 'BLOCKED'
            ? '인스타그램이 요청을 차단했습니다. 잠시 후 다시 시도하세요.'
            : '해시태그 검색에 실패했습니다.',
        });
        running = false; return;
      }

      // 2) 프로필 순회 (사람 속도), 5건마다 서버로 중간 저장
      const batch = [];
      let sent = 0;
      for (const username of authors) {
        if (!running) break;
        try {
          const prof = await fetchProfile(username);
          if (prof) batch.push(prof);
        } catch (e) {
          if (e.message === 'BLOCKED') {
            await post(apiBase, token, '/api/chrome/insta-collect-result', {
              job_id: job.job_id, status: 'failed', prospects: batch,
              message: '수집 중 차단 감지 — 중단했습니다.',
            });
            running = false; return;
          }
        }
        if (batch.length >= 5) {
          await post(apiBase, token, '/api/chrome/insta-collect-result', {
            job_id: job.job_id, status: 'running', prospects: batch.splice(0),
            message: `${(sent += 5)}명 확인 중...`,
          });
        }
        await sleep(jitter());
      }

      // 3) 마무리
      await post(apiBase, token, '/api/chrome/insta-collect-result', {
        job_id: job.job_id, status: 'completed', prospects: batch,
        message: '수집 완료',
      });
    } catch (e) {
      // 네트워크 등 예기치 못한 오류는 조용히 종료 (서버 job은 running으로 남아 재개 가능)
    } finally {
      running = false;
    }
  }
})();
