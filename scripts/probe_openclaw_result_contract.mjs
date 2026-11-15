#!/usr/bin/env node
// Execute only the pinned, dependency-free result classifier, never the CLI.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const source = process.argv[2];
if (!source || process.argv.length !== 3) {
  throw new Error('Usage: node probe_openclaw_result_contract.mjs <pinned agent-exec-result.ts>');
}
const expected = '84cb782d2100f703a158afca578a8ee468035f508089a6029eb9e0348e2d9008';
const digest = createHash('sha256').update(readFileSync(source)).digest('hex');
assert.equal(digest, expected, 'Refuse changed upstream source before importing');
const { classifyAgentExecResult: classify } = await import(pathToFileURL(source).href);
const cases = [];
const sample = (meta = {}, payloads = [{ text: 'synthetic final' }]) => ({
  meta: { stopReason: 'stop', agentMeta: { sessionId: 'synthetic-session' }, ...meta }, payloads,
});
function check(name, run, verify) {
  const result = run();
  verify(result);
  cases.push({ name, passed: true, status: result.status });
}
const failed = (r) => { assert.equal(r.ok, false); assert.equal(r.status, 'error'); };
check('successful_terminal', () => classify(sample()), r => {
  assert.equal(r.ok, true); assert.equal(r.status, 'ok');
  assert.equal(r.final, 'synthetic final'); assert.equal(r.sessionId, 'synthetic-session');
});
check('reasoning_and_commentary_excluded', () => classify(sample({}, [
  { text: 'hidden', isReasoning: true }, { text: 'progress', isCommentary: true },
  { text: 'result  \n' },
])), r => assert.equal(r.final, 'result'));
check('visible_text_fallback', () => classify(sample({ finalAssistantVisibleText: 'visible\n' }, [])),
  r => assert.equal(r.final, 'visible'));
check('error_payload', () => classify(sample({}, [{ text: 'partial' }, { text: 'failed', isError: true }])),
  r => { failed(r); assert.equal(r.error.kind, 'error_payload'); assert.equal(r.error.message, 'failed'); });
check('projected_error_payload', () => classify(sample({}, [{ text: 'projection' }]), false, 'projection'),
  r => { failed(r); assert.equal(r.final, ''); assert.equal(r.payloads[0].isError, true); });
check('projected_untyped_error', () => classify(sample(), false, true), failed);
check('aborted', () => classify(sample({ aborted: true })),
  r => { failed(r); assert.equal(r.error.kind, 'aborted'); });
check('meta_error', () => classify(sample({ error: { kind: 'synthetic_error', message: 'failure' } })),
  r => { failed(r); assert.equal(r.error.kind, 'synthetic_error'); });
check('error_stop_reason', () => classify(sample({ stopReason: 'error' })), failed);
check('fallback_exhausted', () => classify(sample(), true),
  r => { failed(r); assert.equal(r.error.kind, 'fallback_exhausted'); });
check('timeout_reason', () => classify(sample({ stopReason: 'timeout' })),
  r => { assert.equal(r.ok, false); assert.equal(r.status, 'timeout'); });
check('timeout_phase', () => classify(sample({ timeoutPhase: 'model_request' })),
  r => { assert.equal(r.ok, false); assert.equal(r.status, 'timeout'); });
check('incomplete_turn_error_preserved', () => classify(sample({
  stopReason: 'length', error: { kind: 'incomplete_turn', message: 'Output limit reached' },
})), r => { failed(r); assert.equal(r.error.kind, 'incomplete_turn'); });
check('unavailable_usage_not_invented', () => classify(sample()), r => {
  assert.equal('usage' in r, false); assert.equal('costUsd' in r, false);
});

// Deliberately incomplete internal inputs show why this function alone cannot
// prove a successful CLI turn. The caller must supply upstream terminal facts.
const lengthOnly = classify(sample({ stopReason: 'length' }));
const missingStopReason = classify({ meta: {}, payloads: [{ text: 'unproven' }] });
assert.equal(lengthOnly.ok, true);
assert.equal(missingStopReason.ok, true);
console.log(JSON.stringify({
  upstreamCommit: '41f2b981d240cab9e55b07cba991282a795317b5',
  sourceSha256: digest, nodeVersion: process.version,
  executed: 'classifyAgentExecResult only', checks: cases,
  boundaryObservations: { lengthWithoutMetaErrorClassifiedOk: lengthOnly.ok,
    missingStopReasonClassifiedOk: missingStopReason.ok },
  fullCliTested: false, providerCalled: false, sessionResumeTested: false,
  cancellationCleanupTested: false, adapterReady: false,
}, null, 2));
