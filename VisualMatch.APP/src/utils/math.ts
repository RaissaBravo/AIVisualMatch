export function l2Normalize(values: ArrayLike<number>): Float32Array {
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) { const value = values[i]; if (!Number.isFinite(value)) throw new Error('Embedding contém valor inválido.'); sum += value * value; }
  const norm = Math.sqrt(sum);
  if (!Number.isFinite(norm) || norm <= 0) throw new Error('Embedding possui norma zero ou inválida.');
  const result = new Float32Array(values.length);
  for (let i = 0; i < values.length; i += 1) result[i] = values[i] / norm;
  return result;
}
export function dotProduct(a: ArrayLike<number>, b: ArrayLike<number>): number {
  if (a.length !== b.length || a.length === 0) throw new Error('Embeddings incompatíveis.');
  let result = 0; for (let i = 0; i < a.length; i += 1) result += a[i] * b[i]; return result;
}
