/**
 * 인스타그램 API 응답 → 우리 데이터로 바꾸는 '순수 함수'들.
 *
 * 네트워크·DOM과 분리해 두어, 인스타 없이도 가짜 응답으로 테스트할 수 있다.
 * (content script와 Node 테스트가 같은 파일을 공유한다.)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.InstaParse = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;

  // 해시태그 web_info 응답 → 작성자 username 목록 (중복 제거, limit까지)
  function parseTagAuthors(tagJson, limit) {
    const sections =
      tagJson?.data?.top?.sections ||
      tagJson?.data?.recent?.sections ||
      [];
    const usernames = [];
    const seen = new Set();
    for (const sec of sections) {
      const medias =
        sec?.layout_content?.medias ||
        sec?.layout_content?.fill_items ||
        [];
      for (const m of medias) {
        const u = m?.media?.user?.username;
        if (u && !seen.has(u)) {
          seen.add(u);
          usernames.push(u);
          if (usernames.length >= limit) return usernames;
        }
      }
    }
    return usernames;
  }

  // web_profile_info 응답 → 업체 레코드 (없으면 null)
  function parseProfile(profileJson, username) {
    const user = profileJson?.data?.user;
    if (!user) return null;
    const bio = user.biography || '';
    const bioEmail =
      user.business_email || (bio.match(EMAIL_RE) || [])[0] || null;
    const link =
      user.external_url ||
      (user.bio_links && user.bio_links[0] && user.bio_links[0].url) ||
      null;
    return {
      name: user.full_name || username,
      instagram: username,
      instagram_pk: user.id ? String(user.id) : null,
      email: bioEmail,
      phone: user.business_phone_number || null,
      website: link,
      bio: bio ? bio.slice(0, 280) : null,
    };
  }

  return { parseTagAuthors, parseProfile, EMAIL_RE };
});
