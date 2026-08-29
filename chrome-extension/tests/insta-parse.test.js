/**
 * 인스타 파싱 순수 함수 테스트 — 인스타 없이 가짜 응답으로 검증.
 * 실행: node chrome-extension/tests/insta-parse.test.js
 */
const assert = require('assert');
const { parseTagAuthors, parseProfile } = require('../content-scripts/insta-parse.js');

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ✓', name); }
  catch (e) { console.error('  ✗', name, '\n   ', e.message); process.exitCode = 1; }
}

// ── parseTagAuthors ─────────────────────────────
test('해시태그 응답에서 작성자 username을 뽑는다', () => {
  const json = { data: { top: { sections: [
    { layout_content: { medias: [
      { media: { user: { username: 'cafe_a' } } },
      { media: { user: { username: 'cafe_b' } } },
    ] } },
  ] } } };
  assert.deepStrictEqual(parseTagAuthors(json, 10), ['cafe_a', 'cafe_b']);
});

test('중복 username은 한 번만', () => {
  const json = { data: { recent: { sections: [
    { layout_content: { medias: [
      { media: { user: { username: 'dup' } } },
      { media: { user: { username: 'dup' } } },
      { media: { user: { username: 'other' } } },
    ] } },
  ] } } };
  assert.deepStrictEqual(parseTagAuthors(json, 10), ['dup', 'other']);
});

test('limit까지만 반환', () => {
  const medias = Array.from({ length: 5 }, (_, i) => ({ media: { user: { username: 'u' + i } } }));
  const json = { data: { top: { sections: [{ layout_content: { medias } }] } } };
  assert.strictEqual(parseTagAuthors(json, 3).length, 3);
});

test('fill_items 형태도 처리', () => {
  const json = { data: { top: { sections: [
    { layout_content: { fill_items: [{ media: { user: { username: 'fi' } } }] } },
  ] } } };
  assert.deepStrictEqual(parseTagAuthors(json, 10), ['fi']);
});

test('빈/이상한 응답은 빈 배열', () => {
  assert.deepStrictEqual(parseTagAuthors({}, 10), []);
  assert.deepStrictEqual(parseTagAuthors(null, 10), []);
  assert.deepStrictEqual(parseTagAuthors({ data: {} }, 10), []);
});

// ── parseProfile ────────────────────────────────
test('business_email 우선', () => {
  const json = { data: { user: {
    full_name: '강남카페', id: '123', biography: '문의 hello@bio.kr',
    business_email: 'biz@corp.kr', business_phone_number: '02-1', external_url: 'https://x.kr',
  } } };
  const p = parseProfile(json, 'gangnam');
  assert.strictEqual(p.email, 'biz@corp.kr');   // business_email이 bio보다 우선
  assert.strictEqual(p.phone, '02-1');
  assert.strictEqual(p.website, 'https://x.kr');
  assert.strictEqual(p.instagram_pk, '123');
  assert.strictEqual(p.name, '강남카페');
});

test('business_email 없으면 소개글에서 이메일 추출', () => {
  const json = { data: { user: { biography: '예약문의: order@shop.com 입니다', id: '9' } } };
  assert.strictEqual(parseProfile(json, 'shop').email, 'order@shop.com');
});

test('이메일 없으면 email은 null (핸들만으로도 유효)', () => {
  const json = { data: { user: { full_name: '노메일', biography: '맛집', id: '1' } } };
  const p = parseProfile(json, 'nomail');
  assert.strictEqual(p.email, null);
  assert.strictEqual(p.instagram, 'nomail');
});

test('bio_links의 링크를 website로', () => {
  const json = { data: { user: { biography: '', bio_links: [{ url: 'https://linktr.ee/x' }], id: '2' } } };
  assert.strictEqual(parseProfile(json, 'x').website, 'https://linktr.ee/x');
});

test('user 없으면 null', () => {
  assert.strictEqual(parseProfile({}, 'x'), null);
  assert.strictEqual(parseProfile(null, 'x'), null);
});

test('full_name 없으면 username을 이름으로', () => {
  assert.strictEqual(parseProfile({ data: { user: { id: '1', biography: '' } } }, 'handle').name, 'handle');
});

console.log(`\n${passed} passed`);
