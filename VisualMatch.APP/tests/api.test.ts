import assert from "node:assert/strict";
import test from "node:test";
import { parseProducts } from "../src/services/apiService";
test("parser aceita contrato e remove embeddings inválidos", () => {
  const products = parseProducts(
    [{ id: 1, name: " Produto ", embeddings: [[1, 0], [1], [Number.NaN, 0]] }],
    2,
  );
  assert.equal(products[0].name, "Produto");
  assert.deepEqual(products[0].embeddings, [[1, 0]]);
});
test("parser rejeita payload que não é lista", () =>
  assert.throws(() => parseProducts({}), /não é uma lista/));
