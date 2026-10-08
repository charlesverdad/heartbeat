import test from 'node:test';
import assert from 'node:assert/strict';
await import('../src/shared/core.js');
const { tick, fmt, secondsUntil, clamp, mod, G, formatClockTime } = globalThis.HB;

test('tick: whole seconds left and phase into the second', () => {
  assert.deepEqual(tick(0, 10), { n: 10, phase: 0, done: false });
  const a = tick(0.25, 10);
  assert.equal(a.n, 10);
  assert.ok(Math.abs(a.phase - 0.25) < 1e-9);
  assert.equal(tick(9.5, 10).n, 1);
  assert.equal(tick(10, 10).done, true);
  assert.deepEqual(tick(10.4, 10), { n: 0, phase: 0.40000000000000036, done: true });
});

test('fmt: M:SS, H:MM:SS from an hour', () => {
  assert.equal(fmt(0), '0:00');
  assert.equal(fmt(59), '0:59');
  assert.equal(fmt(300), '5:00');
  assert.equal(fmt(3599), '59:59');
  assert.equal(fmt(3600), '1:00:00');
  assert.equal(fmt(3725), '1:02:05');
});

test('secondsUntil: today if ahead, tomorrow if gone, null if invalid', () => {
  const now = new Date(2026, 0, 4, 10, 30, 0).getTime();
  assert.equal(secondsUntil('11:00', now), 1800);
  assert.equal(secondsUntil('10:30', now), 86400); // exactly now means tomorrow
  assert.equal(secondsUntil('10:00', now), 23.5 * 3600);
  assert.equal(secondsUntil('', now), null);
  assert.equal(secondsUntil('nope', now), null);
});

test('helpers', () => {
  assert.equal(clamp(5, 0, 1), 1);
  assert.equal(mod(-1, 5), 4);
  assert.equal(G(2, 2, 1), 1);
  assert.match(formatClockTime('11:00'), /11:00/);
  assert.equal(formatClockTime('x'), '');
});
