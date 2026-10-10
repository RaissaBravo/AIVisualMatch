export function l2Normalize(values: ArrayLike<number>): Float32Array {
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    const value = values[i];
    if (!Number.isFinite(value))
      throw new Error("Embedding contém valor inválido.");
    sum += value * value;
  }
  const norm = Math.sqrt(sum);
  if (!Number.isFinite(norm) || norm <= 0)
    throw new Error("Embedding possui norma zero ou inválida.");
  const result = new Float32Array(values.length);
  for (let i = 0; i < values.length; i += 1) result[i] = values[i] / norm;
  return result;
}
export function dotProduct(a: ArrayLike<number>, b: ArrayLike<number>): number {
  if (a.length !== b.length || a.length === 0)
    throw new Error("Embeddings incompatíveis.");
  let result = 0;
  for (let i = 0; i < a.length; i += 1) result += a[i] * b[i];
  return result;
}
export function meanVector(
  vectors: ArrayLike<number>[],
  dimension: number,
): Float32Array {
  const mean = new Float32Array(dimension);
  if (!vectors.length) return mean;
  for (const vector of vectors)
    for (let i = 0; i < dimension; i += 1) mean[i] += vector[i];
  for (let i = 0; i < dimension; i += 1) mean[i] /= vectors.length;
  return mean;
}
/**
 * Subtracts the dataset centroid before normalizing. MobileNetV2 features are
 * post-ReLU (all non-negative), so raw cosine stays high between any two images;
 * removing the shared component is what makes the scores separable.
 */
export function centerAndNormalize(
  values: ArrayLike<number>,
  mean: ArrayLike<number>,
): Float32Array | null {
  if (values.length !== mean.length || values.length === 0) return null;
  const centered = new Float32Array(values.length);
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    const value = values[i] - mean[i];
    if (!Number.isFinite(value)) return null;
    centered[i] = value;
    sum += value * value;
  }
  const norm = Math.sqrt(sum);
  if (!Number.isFinite(norm) || norm <= 0) return null;
  for (let i = 0; i < centered.length; i += 1) centered[i] /= norm;
  return centered;
}
