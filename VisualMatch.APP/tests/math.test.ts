import assert from "node:assert/strict";
import test from "node:test";
import { buildEmbeddingSpace } from "../src/services/embeddingSpace";
import {
  averageScores,
  findBestMatches,
  rankScores,
  scoreProducts,
} from "../src/services/matchingService";
import {
  centerAndNormalize,
  dotProduct,
  l2Normalize,
  meanVector,
} from "../src/utils/math";

const space = (products: Parameters<typeof buildEmbeddingSpace>[0]) =>
  buildEmbeddingSpace(products);

test("normalização L2 produz norma unitária", () => {
  const value = l2Normalize([3, 4]);
  assert.ok(Math.abs(dotProduct(value, value) - 1) < 1e-6);
});
test("meanVector calcula o centroide", () => {
  assert.deepEqual(Array.from(meanVector([[0, 2], [2, 4]], 2)), [1, 3]);
});
test("centerAndNormalize remove o centroide e normaliza", () => {
  const value = centerAndNormalize([2, 1], [1, 1]);
  assert.ok(value);
  assert.deepEqual(Array.from(value), [1, 0]);
});
test("centerAndNormalize devolve null quando o vetor é o próprio centroide", () => {
  assert.equal(centerAndNormalize([1, 1], [1, 1]), null);
});
test("centralização separa embeddings que o cosseno cru aproxima", () => {
  const a = [0.9, 0.8];
  const b = [0.8, 0.9];
  const raw = dotProduct(l2Normalize(a), l2Normalize(b));
  const mean = meanVector([a, b], 2);
  const centered = dotProduct(
    centerAndNormalize(a, mean)!,
    centerAndNormalize(b, mean)!,
  );
  assert.ok(raw > 0.98);
  assert.ok(centered < raw);
});
test("embedding idêntico a uma referência vence e é match", () => {
  const built = space([
    { id: 1, name: "A", embeddings: [[1, 0]] },
    { id: 2, name: "B", embeddings: [[0, 1]] },
  ]);
  const result = findBestMatches([1, 0], built)[0];
  assert.equal(result.productId, 1);
  assert.ok(Math.abs(result.similarity - 1) < 1e-6);
  assert.equal(result.isMatch, true);
});
test("empate técnico não vira match", () => {
  const built = space([
    { id: 1, name: "A", embeddings: [[1, 0, 0]] },
    { id: 2, name: "B", embeddings: [[0, 1, 0]] },
  ]);
  const results = rankScores([0.7, 0.68], built);
  assert.equal(results[0].isMatch, false);
});
test("apenas o primeiro colocado pode ser match", () => {
  const built = space([
    { id: 1, name: "A", embeddings: [[1, 0, 0]] },
    { id: 2, name: "B", embeddings: [[0, 1, 0]] },
  ]);
  const results = rankScores([0.9, 0.6], built);
  assert.equal(results[0].isMatch, true);
  assert.equal(results[1].isMatch, false);
});
test("scoreProducts respeita a ordem dos produtos do espaço", () => {
  const built = space([
    { id: 1, name: "A", embeddings: [[1, 0]] },
    { id: 2, name: "B", embeddings: [[0, 1]] },
  ]);
  const scores = scoreProducts([1, 0], built);
  assert.equal(scores.length, built.products.length);
  assert.ok(scores[0] > scores[1]);
});
test("averageScores faz a média por produto", () => {
  assert.deepEqual(
    averageScores([
      [1, 0],
      [0, 1],
    ]),
    [0.5, 0.5],
  );
});
test("produto sem embeddings utilizáveis fica fora do espaço", () => {
  const built = space([
    { id: 1, name: "A", embeddings: [[1, 0]] },
    { id: 2, name: "B", embeddings: [] },
  ]);
  assert.deepEqual(
    built.products.map((product) => product.id),
    [1],
  );
});
