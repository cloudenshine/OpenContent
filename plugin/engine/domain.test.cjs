/**
 * Pure JS Unit Tests for Domain Engine (Claim/Evidence/Gate)
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const domain = require('./domain.js');

test('domain.validate: project requires goal, audience and valid state', () => {
  assert.throws(() => domain.validate({ type: 'Project', title: 'P1' }, {}), /goal cannot be empty/);
  assert.throws(() => domain.validate({ type: 'Project', title: 'P1', goal: 'G' }, {}), /audience cannot be empty/);
  assert.throws(() => domain.validate({ type: 'Project', title: 'P1', goal: 'G', audience: 'A', state: 'INVALID' }, {}), /Invalid project state/);
  
  const validP = { type: 'Project', title: 'P1', goal: 'G', audience: 'A', state: 'CAPTURED', oc_id: 'p1' };
  assert.doesNotThrow(() => domain.validate(validP, { p1: validP }));
});

test('domain.validate: material must cite source and non-empty body', () => {
  const p = { type: 'Project', title: 'P1', goal: 'G', audience: 'A', state: 'CAPTURED', oc_id: 'p1' };
  const objects = { p1: p };

  assert.throws(() => domain.validate({ type: 'Material', title: 'M1', project: 'p1', body: '' }, objects), /must record a source/);
  assert.throws(() => domain.validate({ type: 'Material', title: 'M1', project: 'p1', source: 'file.md', body: ' ' }, objects), /excerpt cannot be empty/);
  
  const m = { type: 'Material', title: 'M1', project: 'p1', source: 'file.md', body: 'Fact 1', oc_id: 'm1' };
  assert.doesNotThrow(() => domain.validate(m, { ...objects, m1: m }));
});

test('domain.gate: fails on missing thesis, missing claims, short draft', () => {
  const p = { type: 'Project', title: 'P1', goal: 'G', audience: 'A', state: 'DRAFTING', oc_id: 'p1', thesis: '' };
  const a = { type: 'Artifact', title: 'A1', project: 'p1', body: 'Short text', oc_id: 'a1' };
  const objects = { p1: p, a1: a };

  const result = domain.gate(objects, a);
  assert.equal(result.status, 'FAIL');
  assert.ok(result.issues.some(i => i.includes('Project thesis is missing')));
  assert.ok(result.issues.some(i => i.includes('Project has no Claims')));
  assert.ok(result.issues.some(i => i.includes('Draft is shorter than 80 characters')));
});

test('domain.gate: verifies claim link matching and quote verbatim check', () => {
  const p = { type: 'Project', title: 'P1', goal: 'G', audience: 'A', state: 'DRAFTING', oc_id: 'p1', thesis: 'T1' };
  const m = { type: 'Material', title: 'M1', project: 'p1', source: 'f.md', body: 'All apples are round and red.', oc_id: 'm1' };
  const k = { type: 'Knowledge', title: 'K1', project: 'p1', derived_from: ['m1'], oc_id: 'k1' };
  const claimId = '11112222333344445555666677778888';
  const c = { type: 'Claim', title: 'C1', project: 'p1', derived_from: ['k1'], body: 'Apples are round.', oc_id: claimId };
  const e = { type: 'Evidence', title: 'E1', project: 'p1', claim: claimId, material: 'm1', stance: 'supports', quote: 'round and red', oc_id: 'e1' };
  
  const body = 'This is a long enough draft text that exceeds eighty characters easily.\nApples are round. [[' + claimId + ']] And more content here to ensure length.';
  const a = { type: 'Artifact', title: 'A1', project: 'p1', derived_from: [claimId], body: body, oc_id: 'a1', author: 'AuthorA' };

  const objects = { p1: p, m1: m, k1: k, [claimId]: c, e1: e, a1: a };
  const hash = domain.contextHash(objects, a);

  // Review passing all axes
  const r = {
    type: 'Review',
    title: 'R1',
    project: 'p1',
    artifact: 'a1',
    mode: 'critique',
    created: '2026-09-11T10:00:00Z',
    context_hash: hash,
    reviewer: 'ReviewerB',
    claims_complete: true,
    axes: {
      Evidence: { status: 'PASS', reason: 'Verified' },
      Logic: { status: 'PASS', reason: 'Sound' },
      Originality: { status: 'PASS', reason: 'Fresh' },
      Voice: { status: 'PASS', reason: 'Clear' },
      Utility: { status: 'PASS', reason: 'Useful' }
    },
    oc_id: 'r1'
  };
  objects.r1 = r;

  const result = domain.gate(objects, a);
  assert.equal(result.status, 'PASS');
  assert.equal(result.issues.length, 0);
  assert.equal(result.axes.Evidence.status, 'PASS');
});
