import { cosineSimilarity } from '@/src/services/matchingService';
export interface CompatibilityMetrics { maxDifference: number; meanDifference: number; cosineSimilarity: number; }
export function compareEmbeddings(mobile: ArrayLike<number>, expected: ArrayLike<number>): CompatibilityMetrics {
  if (mobile.length !== expected.length || !mobile.length) throw new Error('Embeddings de compatibilidade incompatíveis.');
  let maxDifference = 0; let total = 0;
  for (let i = 0; i < mobile.length; i += 1) { const difference = Math.abs(mobile[i] - expected[i]); maxDifference = Math.max(maxDifference, difference); total += difference; }
  return { maxDifference, meanDifference: total / mobile.length, cosineSimilarity: cosineSimilarity(mobile, expected) };
}
