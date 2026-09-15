/**
 * Pure JavaScript Domain Engine for OpenContent
 * Ported from opencontent/domain.py
 * Zero Python dependencies for core validation, Quality Gates, evidence graph & transitions.
 */

const crypto = require('crypto');

const TYPES = ['Project', 'Material', 'Knowledge', 'Idea', 'Claim', 'Evidence', 'Artifact', 'Review', 'Publication'];
const STATES = ['CAPTURED', 'DISTILLED', 'IDEA', 'RESEARCHING', 'ARGUMENT_READY', 'DRAFTING', 'REVIEWING', 'APPROVED', 'PUBLISHED', 'LEARNING'];
const AXES = ['Evidence', 'Logic', 'Originality', 'Voice', 'Utility'];

function digest(data) {
  return crypto.createHash('sha256').update(typeof data === 'string' ? data : Buffer.from(data)).digest('hex');
}

class Problem extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = 'Problem';
    this.status = status;
  }
}

function linked(objects, project, kind) {
  return Object.values(objects).filter(o => o.project === project && o.type === kind);
}

function requireObject(objects, uid, kind = null) {
  const obj = objects[uid];
  if (!obj) throw new Problem(`Object not found: ${uid}`, 404);
  if (kind && obj.type !== kind) throw new Problem(`Object ${uid} is ${obj.type}, expected ${kind}`);
  return obj;
}

function validate(obj, objects) {
  const kind = obj.type;
  if (!TYPES.includes(kind)) throw new Problem(`Unknown type: ${kind}`);
  if (!obj.title || !String(obj.title).trim()) throw new Problem(`${kind} title cannot be empty`);

  const pid = obj.project;
  if (kind === 'Project') {
    if (!obj.goal || !String(obj.goal).trim()) throw new Problem('Project goal cannot be empty');
    if (!obj.audience || !String(obj.audience).trim()) throw new Problem('Project audience cannot be empty');
    if (!STATES.includes(obj.state)) throw new Problem(`Invalid project state: ${obj.state}`);
    return;
  }

  if (!pid || !objects[pid] || objects[pid].type !== 'Project') {
    throw new Problem(`${kind} must belong to a valid Project`);
  }

  if (kind === 'Material') {
    if (!obj.source || !String(obj.source).trim()) throw new Problem('Material must record a source location');
    if (!obj.body || !String(obj.body).trim()) throw new Problem('Material excerpt cannot be empty');
  } else if (kind === 'Knowledge') {
    const fromList = obj.derived_from || [];
    if (!fromList.length) throw new Problem('Knowledge must be derived from at least one Material');
    for (const sid of fromList) {
      const src = objects[sid];
      if (!src || src.type !== 'Material' || src.project !== pid) {
        throw new Problem(`Knowledge derivation target invalid: ${sid}`);
      }
    }
  } else if (kind === 'Idea') {
    if (!obj.thesis || !String(obj.thesis).trim()) throw new Problem('Idea thesis statement cannot be empty');
  } else if (kind === 'Claim') {
    const fromList = obj.derived_from || [];
    if (!fromList.length) throw new Problem('Claim must be derived from at least one Knowledge object');
    for (const kid of fromList) {
      const k = objects[kid];
      if (!k || k.type !== 'Knowledge' || k.project !== pid) {
        throw new Problem(`Claim derivation target invalid: ${kid}`);
      }
    }
  } else if (kind === 'Evidence') {
    const cid = obj.claim;
    const claim = objects[cid];
    if (!claim || claim.type !== 'Claim' || claim.project !== pid) {
      throw new Problem('Evidence must point to a Claim in the same project');
    }
    const stance = obj.stance || 'supports';
    if (!['supports', 'opposes'].includes(stance)) throw new Problem('Evidence stance must be supports or opposes');
    const mid = obj.material;
    const mat = objects[mid];
    if (!mat || mat.type !== 'Material' || mat.project !== pid) {
      throw new Problem('Evidence must cite a Material object in the same project');
    }
    const quote = obj.quote ? String(obj.quote).trim() : '';
    if (quote && !String(mat.body || '').includes(quote)) {
      throw new Problem('Evidence quote must appear verbatim in cited Material');
    }
  } else if (kind === 'Artifact') {
    if (!obj.body || !String(obj.body).trim()) throw new Problem('Artifact draft cannot be empty');
    for (const cid of obj.derived_from || []) {
      const c = objects[cid];
      if (!c || c.type !== 'Claim' || c.project !== pid) {
        throw new Problem(`Artifact cites unknown Claim: ${cid}`);
      }
    }
  } else if (kind === 'Review') {
    const aid = obj.artifact;
    const a = objects[aid];
    if (!a || a.type !== 'Artifact' || a.project !== pid) throw new Problem('Review must inspect an Artifact');
    const axes = obj.axes || {};
    for (const axis of AXES) {
      if (!axes[axis] || !['PASS', 'WARN', 'FAIL'].includes(axes[axis].status)) {
        throw new Problem(`Review missing valid axis evaluation: ${axis}`);
      }
      if (!axes[axis].reason || !String(axes[axis].reason).trim()) {
        throw new Problem(`Review axis must provide reason: ${axis}`);
      }
    }
  } else if (kind === 'Publication') {
    const aid = obj.artifact;
    const a = objects[aid];
    if (!a || a.type !== 'Artifact' || a.project !== pid) throw new Problem('Publication must package an Artifact');
  }
}

function contextHash(objects, artifact, policies = {}) {
  const pid = artifact.project;
  const components = [];
  const project = objects[pid];
  if (project) {
    components.push(`Project:${project.title}:${project.goal}:${project.thesis || ''}`);
  }
  for (const kind of ['Material', 'Knowledge', 'Idea', 'Claim', 'Evidence']) {
    const list = linked(objects, pid, kind).sort((a, b) => a.oc_id.localeCompare(b.oc_id));
    for (const obj of list) {
      components.push(`${kind}:${obj.oc_id}:${obj.body || ''}:${(obj.derived_from || []).join(',')}:${obj.claim || ''}:${obj.material || ''}:${obj.quote || ''}`);
    }
  }
  components.push(`Artifact:${artifact.oc_id}:${artifact.body || ''}:${(artifact.derived_from || []).join(',')}`);
  for (const name of Object.keys(policies).sort()) {
    components.push(`Policy:${name}:${policies[name]}`);
  }
  return digest(components.join('\n\n---\n\n'));
}

function evidenceGraph(objects, artifact) {
  const graph = [];
  const pid = artifact.project;
  for (const cid of artifact.derived_from || []) {
    const claim = objects[cid];
    if (!claim) continue;
    const supports = [];
    const opposes = [];
    for (const e of linked(objects, pid, 'Evidence')) {
      if (e.claim === cid) {
        if (e.stance === 'supports') supports.push(e);
        else opposes.push(e);
      }
    }
    const knowledge = (claim.derived_from || []).map(kid => objects[kid]).filter(Boolean);
    const mIds = new Set(knowledge.flatMap(k => k.derived_from || []));
    const materials = Array.from(mIds).map(mid => objects[mid]).filter(Boolean);
    const usedBy = Object.values(objects).filter(o => o.project === pid && (o.derived_from || []).includes(cid)).map(o => o.title || o.oc_id);

    graph.push({ claim, supports, opposes, knowledge, materials, used_by: usedBy });
  }
  return graph;
}

function argumentIssues(objects, pid) {
  const issues = [];
  const claims = linked(objects, pid, 'Claim');
  if (!claims.length) {
    issues.push('Project has no Claims');
    return issues;
  }
  for (const claim of claims) {
    try {
      validate(claim, objects);
    } catch (e) {
      issues.push(e.message);
    }
    const evidences = linked(objects, pid, 'Evidence').filter(e => e.claim === claim.oc_id);
    const supports = evidences.filter(e => e.stance === 'supports');
    const opposes = evidences.filter(e => e.stance === 'opposes');
    if (!supports.length) {
      issues.push(`Claim has no supporting Evidence: ${claim.title}`);
    }
    for (const ev of evidences) {
      try {
        validate(ev, objects);
      } catch (e) {
        issues.push(e.message);
      }
    }
    const fromK = claim.derived_from || [];
    if (!fromK.length) {
      issues.push(`Claim is detached from Knowledge: ${claim.title}`);
    } else {
      for (const kid of fromK) {
        const k = objects[kid];
        if (!k || !(k.derived_from || []).length) {
          issues.push(`Knowledge for Claim has no Material: ${claim.title}`);
        }
      }
    }
    if (opposes.length && !supports.some(s => s.rebuts && opposes.map(o => o.oc_id).includes(s.rebuts))) {
      issues.push(`Contested claim missing rebuttal evidence: ${claim.title}`);
    }
  }
  return issues;
}

function gate(objects, artifact, policies = {}, errors = []) {
  const issues = [...errors];
  const pid = artifact.project;

  try {
    const project = requireObject(objects, pid, 'Project');
    validate(project, objects);
    if (!project.thesis || !String(project.thesis).trim()) {
      issues.push('Project thesis is missing');
    }
  } catch (e) {
    issues.push(e.message);
  }

  issues.push(...argumentIssues(objects, pid));

  try {
    validate(artifact, objects);
  } catch (e) {
    issues.push(e.message);
  }

  const body = artifact.body || '';
  if (body.trim().length < 80) {
    issues.push('Draft is shorter than 80 characters');
  }

  const markers = new Set((body.match(/\[\[([0-9a-f]{32})(?:\|[^\]]+)?\]\]/g) || []).map(m => {
    const matched = m.match(/\[\[([0-9a-f]{32})/);
    return matched ? matched[1] : null;
  }).filter(Boolean));

  const derivedFrom = new Set(artifact.derived_from || []);
  let setsEqual = markers.size === derivedFrom.size;
  if (setsEqual) {
    for (const id of markers) {
      if (!derivedFrom.has(id)) { setsEqual = false; break; }
    }
  }
  if (!setsEqual) {
    issues.push('Draft Claim links must match its registered Claims');
  }

  for (const cid of artifact.derived_from || []) {
    const claim = objects[cid];
    if (claim && claim.body && !body.includes(claim.body.trim())) {
      issues.push(`Claim statement is absent from draft: ${claim.title}`);
    }
  }

  for (const text of Object.values(policies)) {
    const headings = ['Audience', 'Voice', 'Editorial Principles', 'Evidence Policy', 'Citation Policy', 'Originality Standard', 'Forbidden Patterns', 'Quality Gates'];
    if (headings.some(h => !text.includes('## ' + h))) {
      issues.push('CONTENT.md is missing required sections');
    }
    const secMatch = text.match(/## Forbidden Patterns\s*\n(.*?)(?=\n## |\Z)/s);
    if (secMatch) {
      const words = (secMatch[1].match(/^-\s+(.+)$/gm) || []).map(w => w.replace(/^-\s+/, '').trim());
      for (const w of words) {
        if (w && body.includes(w)) {
          issues.push(`Forbidden pattern: ${w}`);
        }
      }
    }
  }

  const fingerprint = contextHash(objects, artifact, policies);
  const reviews = linked(objects, pid, 'Review')
    .filter(r => r.artifact === artifact.oc_id && r.mode === 'critique')
    .sort((a, b) => String(a.created).localeCompare(String(b.created)));

  const review = reviews.length ? reviews[reviews.length - 1] : null;
  let axes = {};
  for (const axis of AXES) {
    axes[axis] = { status: 'WARN', reason: 'No current review' };
  }

  if (!review || review.context_hash !== fingerprint) {
    issues.push('Missing or stale Critic Review');
  } else {
    try {
      validate(review, objects);
      if (review.reviewer === artifact.author) {
        throw new Problem('Creator cannot review their own draft');
      }
      axes = review.axes || axes;
      if (!review.claims_complete) {
        issues.push('Important facts are missing from the Claim registry');
      }
      for (const axis of AXES) {
        const ax = axes[axis] || {};
        if (ax.status !== 'PASS') {
          issues.push(`Review failed on axis: ${axis} (${ax.status})`);
        }
      }
    } catch (e) {
      issues.push(e.message);
    }
  }

  const pass = issues.length === 0;
  return {
    status: pass ? 'PASS' : 'FAIL',
    approved: Boolean(artifact.approved && artifact.approval_context_hash === fingerprint && pass),
    context_hash: fingerprint,
    issues,
    axes,
    review: review ? { oc_id: review.oc_id, reviewer: review.reviewer, reviewed_body: review.reviewed_body } : null
  };
}

module.exports = {
  TYPES,
  STATES,
  AXES,
  Problem,
  digest,
  linked,
  requireObject,
  validate,
  contextHash,
  evidenceGraph,
  argumentIssues,
  gate
};
