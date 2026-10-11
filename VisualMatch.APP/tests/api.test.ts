import assert from "node:assert/strict";
import test from "node:test";
import { parseModels, parseProducts } from "../src/services/apiService";
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
test("lista de modelos alimenta o seletor e rejeita payload inválido", () => {
  const models = parseModels([
    { model: "mobilenetv2", input_width: 224, input_height: 224, available: true },
    { model: "dinov2-small", input_width: 224, input_height: 224, available: false },
  ]);
  assert.deepEqual(
    models.map((model) => [model.model, model.available]),
    [
      ["mobilenetv2", true],
      ["dinov2-small", false],
    ],
  );
  assert.throws(() => parseModels({}), /não é uma lista/);
  assert.throws(() => parseModels([{ model: "x" }]), /Contrato do modelo/);
});
