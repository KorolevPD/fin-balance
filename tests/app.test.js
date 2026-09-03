import test from 'node:test';
import assert from 'node:assert/strict';
import { createInitialState } from '../src/app.js';

test('начальное состояние не содержит элементов', () => {
  const state = createInitialState();
  assert.deepEqual(state.items, []);
});

test('в начальном состоянии нет времени последнего обновления', () => {
  const state = createInitialState();
  assert.equal(state.updatedAt, null);
});
