/**
 * Comprehensive Red-Teaming (Adversarial) Suite for OpenContent
 * Evaluates failure boundaries, security invariants, provenance tampering, and edge cases:
 * 1. Missing / Fake Evidence injection into Claims
 * 2. Stale context hash tampering (bypassing Quality Gate)
 * 3. Self-review / Creator conflict of interest
 * 4. Forbidden patterns bypass attempts
 * 5. Auto-feeding pipeline token injection & edge cases
 * 6. Typography rendering XSS / script injection attacks
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const domain = require('../plugin/engine/domain.js');
const pipeline = require('../plugin/engine/pipeline.js');
const typography = require('../plugin/engine/typography.js');

test('Red-Team 1: Fake or non-existent claim ID cannot pass gate', () => {
  const p = { type: 'Project', title: 'Sec Project', goal: 'Security', audience: 'Aud', state: 'DRAFTING', oc_id: 'p_sec', thesis: 'Sec Thesis' };
  const fakeClaimId = '99999999999999999999999999999999';
  const body = `This text is long enough to satisfy the eighty character limit for draft articles. [[${fakeClaimId}]] Fake claim attached.`;
  const a = { type: 'Artifact', title: 'Sec Artifact', project: 'p_sec', derived_from: [fakeClaimId], body, oc_id: 'a_sec', author: 'Alice' };

  const objects = { p_sec: p, a_sec: a };
  const result = domain.gate(objects, a);
  
  assert.equal(result.status, 'FAIL', 'Unregistered claim must fail gate');
  assert.ok(result.issues.some(i => i.includes('unknown Claim') || i.includes('absent from draft') || i.includes('Project has no Claims')));
});

test('Red-Team 2: Content tampering invalidates approval and context hash', () => {
  const p = { type: 'Project', title: 'Tamper Project', goal: 'Goal', audience: 'Aud', state: 'DRAFTING', oc_id: 'p_t', thesis: 'Thesis' };
  const m = { type: 'Material', title: 'Mat', project: 'p_t', source: 's.md', body: 'Evidence text here.', oc_id: 'm_t' };
  const k = { type: 'Knowledge', title: 'Kn', project: 'p_t', derived_from: ['m_t'], oc_id: 'k_t' };
  const cid = '12345678123456781234567812345678';
  const c = { type: 'Claim', title: 'Cl', project: 'p_t', derived_from: ['k_t'], body: 'Evidence text.', oc_id: cid };
  const e = { type: 'Evidence', title: 'Ev', project: 'p_t', claim: cid, material: 'm_t', stance: 'supports', quote: 'Evidence text', oc_id: 'e_t' };

  const originalBody = `This is the original vetted article body that comfortably exceeds eighty characters length limit. [[${cid}]] Evidence text.`;
  const a = { type: 'Artifact', title: 'Art', project: 'p_t', derived_from: [cid], body: originalBody, oc_id: 'a_t', author: 'Alice' };

  const objects = { p_t: p, m_t: m, k_t: k, [cid]: c, e_t: e, a_t: a };
  const validHash = domain.contextHash(objects, a);

  // Review created with valid hash
  const r = {
    type: 'Review',
    title: 'Rev',
    project: 'p_t',
    artifact: 'a_t',
    mode: 'critique',
    created: '2026-09-11T12:00:00Z',
    context_hash: validHash,
    reviewer: 'Bob',
    claims_complete: true,
    axes: {
      Evidence: { status: 'PASS', reason: 'Ok' },
      Logic: { status: 'PASS', reason: 'Ok' },
      Originality: { status: 'PASS', reason: 'Ok' },
      Voice: { status: 'PASS', reason: 'Ok' },
      Utility: { status: 'PASS', reason: 'Ok' }
    },
    oc_id: 'r_t'
  };
  objects.r_t = r;

  // Initial check passes
  const initialResult = domain.gate(objects, a);
  assert.equal(initialResult.status, 'PASS');

  // Attacker covertly modifies draft body after review
  a.body = originalBody + ' [TAMPERED CONTENT INSERTED POST-REVIEW]';
  const tamperedResult = domain.gate(objects, a);
  assert.equal(tamperedResult.status, 'FAIL', 'Hash mismatch must invalidate gate immediately');
  assert.ok(tamperedResult.issues.some(i => i.includes('Missing or stale Critic Review')));
});

test('Red-Team 3: Conflict of interest (Author cannot be Critic Reviewer)', () => {
  const p = { type: 'Project', title: 'P', goal: 'G', audience: 'A', state: 'DRAFTING', oc_id: 'p', thesis: 'T' };
  const m = { type: 'Material', title: 'M', project: 'p', source: 's.md', body: 'Verbatim fact.', oc_id: 'm' };
  const k = { type: 'Knowledge', title: 'K', project: 'p', derived_from: ['m'], oc_id: 'k' };
  const cid = 'abcdefabcdefabcdefabcdefabcdefab';
  const c = { type: 'Claim', title: 'C', project: 'p', derived_from: ['k'], body: 'Verbatim fact.', oc_id: cid };
  const e = { type: 'Evidence', title: 'E', project: 'p', claim: cid, material: 'm', stance: 'supports', quote: 'Verbatim fact', oc_id: 'e' };

  const body = `Sufficiently long draft body text exceeding the minimum 80 chars required by gate. [[${cid}]] Verbatim fact.`;
  const a = { type: 'Artifact', title: 'Art', project: 'p', derived_from: [cid], body, oc_id: 'a', author: 'AttackerAuthor' };
  const objects = { p, m, k, [cid]: c, e, a };
  const hash = domain.contextHash(objects, a);

  // Self-review attempt: reviewer equals author
  const r = {
    type: 'Review',
    title: 'Self Rev',
    project: 'p',
    artifact: 'a',
    mode: 'critique',
    created: '2026-09-11T12:00:00Z',
    context_hash: hash,
    reviewer: 'AttackerAuthor', // Same!
    claims_complete: true,
    axes: {
      Evidence: { status: 'PASS', reason: 'Self pass' },
      Logic: { status: 'PASS', reason: 'Self pass' },
      Originality: { status: 'PASS', reason: 'Self pass' },
      Voice: { status: 'PASS', reason: 'Self pass' },
      Utility: { status: 'PASS', reason: 'Self pass' }
    },
    oc_id: 'r_self'
  };
  objects.r_self = r;

  const result = domain.gate(objects, a);
  assert.equal(result.status, 'FAIL');
  assert.ok(result.issues.some(i => i.includes('Creator cannot review their own draft')));
});

test('Red-Team 4: Forbidden pattern detection from CONTENT.md policies', () => {
  const p = { type: 'Project', title: 'P', goal: 'G', audience: 'A', state: 'DRAFTING', oc_id: 'p', thesis: 'T' };
  const m = { type: 'Material', title: 'M', project: 'p', source: 's.md', body: 'Valid fact.', oc_id: 'm' };
  const k = { type: 'Knowledge', title: 'K', project: 'p', derived_from: ['m'], oc_id: 'k' };
  const cid = '11223344556677889900aabbccddeeff';
  const c = { type: 'Claim', title: 'C', project: 'p', derived_from: ['k'], body: 'Valid fact.', oc_id: cid };
  const e = { type: 'Evidence', title: 'E', project: 'p', claim: cid, material: 'm', stance: 'supports', quote: 'Valid fact', oc_id: 'e' };

  // Injects forbidden word "TODO"
  const body = `Sufficiently long draft body text exceeding the minimum 80 chars required by gate. [[${cid}]] Valid fact. TODO: finish this later.`;
  const a = { type: 'Artifact', title: 'Art', project: 'p', derived_from: [cid], body, oc_id: 'a', author: 'Author' };
  const objects = { p, m, k, [cid]: c, e, a };

  const policy = `
## Audience
Any
## Voice
Clear
## Editorial Principles
Strict
## Evidence Policy
Bound
## Citation Policy
Strict
## Originality Standard
High
## Forbidden Patterns
- TODO
- 待补充
## Quality Gates
Strict
`;
  const result = domain.gate(objects, a, { 'CONTENT.md': policy });
  assert.equal(result.status, 'FAIL');
  assert.ok(result.issues.some(i => i.includes('Forbidden pattern: TODO')));
});

test('Red-Team 5: Typography Engine sanitizes XSS and script injections', () => {
  const maliciousMd = `# Attack Title <script>alert("xss")</script>
<img src=x onerror=alert(1)>
[Evil](javascript:alert(2))
`;
  const renderedHtml = typography.renderArticleHtml(maliciousMd, 'serif');
  assert.ok(!renderedHtml.includes('<script>'), 'Script tag must be escaped');
  assert.ok(renderedHtml.includes('&lt;script&gt;'));
  assert.ok(renderedHtml.includes('&lt;img src=x onerror=alert(1)&gt;'));
});
