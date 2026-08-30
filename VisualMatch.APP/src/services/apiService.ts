import { API_BASE_URL, API_TIMEOUT_MS } from "@/src/config/api";
import type { ModelInfo } from "@/src/types/ModelInfo";
import type { Product } from "@/src/types/Product";
async function getJson(path: string): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`API respondeu HTTP ${response.status}.`);
    return await response.json();
  } finally {
    clearTimeout(timeout);
  }
}
function validVector(
  value: unknown,
  dimension?: number | null,
): value is number[] {
  return (
    Array.isArray(value) &&
    (!dimension || value.length === dimension) &&
    value.length > 0 &&
    value.every(Number.isFinite)
  );
}
export function parseProducts(
  payload: unknown,
  dimension?: number | null,
): Product[] {
  if (!Array.isArray(payload))
    throw new Error("Resposta de produtos não é uma lista.");
  return payload.map((item) => {
    if (!item || typeof item !== "object")
      throw new Error("Produto inválido na resposta.");
    const value = item as Record<string, unknown>;
    if (
      !Number.isInteger(value.id) ||
      typeof value.name !== "string" ||
      !Array.isArray(value.embeddings)
    )
      throw new Error("Campos de produto inválidos.");
    const embeddings = value.embeddings.filter((embedding) => {
      const valid = validVector(embedding, dimension);
      if (!valid && typeof __DEV__ !== "undefined" && __DEV__)
        console.warn(
          `Embedding inválido ignorado no produto ${String(value.id)}.`,
        );
      return valid;
    }) as number[][];
    return { id: value.id as number, name: value.name.trim(), embeddings };
  });
}
export function parseModelInfo(payload: unknown): ModelInfo {
  if (!payload || typeof payload !== "object")
    throw new Error("Resposta de model-info inválida.");
  const value = payload as Record<string, unknown>;
  if (
    typeof value.model !== "string" ||
    typeof value.input_width !== "number" ||
    typeof value.input_height !== "number"
  )
    throw new Error("Contrato do modelo incompleto.");
  return value as unknown as ModelInfo;
}
export const fetchProducts = async (dimension?: number | null) =>
  parseProducts(await getJson("/api/products"), dimension);
export const fetchModelInfo = async () =>
  parseModelInfo(await getJson("/api/model-info"));
