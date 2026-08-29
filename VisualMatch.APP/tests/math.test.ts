import assert from 'node:assert/strict'; import test from 'node:test';
import { findBestMatches } from '../src/services/matchingService'; import { dotProduct, l2Normalize } from '../src/utils/math';
test('normalização L2 produz norma unitária', () => { const value = l2Normalize([3, 4]); assert.ok(Math.abs(dotProduct(value, value) - 1) < 1e-6); });
test('embedding idêntico tem 100% e respeita threshold', () => { const result = findBestMatches([1, 0], [{ id: 1, name: 'A', embeddings: [[0, 1], [1, 0]] }])[0]; assert.equal(result.similarity, 1); assert.equal(result.confidencePercent, 100); assert.equal(result.isMatch, true); });
test('usa maior score entre referências e ordena', () => { const results = findBestMatches([1, 0], [{ id: 1, name: 'A', embeddings: [[0.5, 0.5], [0.7, 0.3]] }, { id: 2, name: 'B', embeddings: [[0.9, 0.1]] }]); assert.deepEqual(results.map((item) => item.productId), [2, 1]); assert.equal(results[1].similarity, 0.7); });
test('score abaixo de 0.65 não é match', () => { assert.equal(findBestMatches([1, 0], [{ id: 1, name: 'A', embeddings: [[0.649, 0]] }])[0].isMatch, false); });
