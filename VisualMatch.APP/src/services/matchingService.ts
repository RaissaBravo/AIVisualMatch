import {
  type MatchRule,
  MAX_RESULTS,
  matchRuleFor,
} from "@/src/config/recognition";
import type { EmbeddingSpace } from "@/src/services/embeddingSpace";
import type { DetectionResult } from "@/src/types/Product";
import { centerAndNormalize, dotProduct } from "@/src/utils/math";
export const cosineSimilarity = (a: ArrayLike<number>, b: ArrayLike<number>) =>
  dotProduct(a, b);
/** Similarity of the query against every product, aligned with space.products. */
export function scoreProducts(
  query: ArrayLike<number>,
  space: EmbeddingSpace,
): number[] {
  const centered = centerAndNormalize(query, space.mean);
  if (!centered) return space.products.map(() => -1);
  return space.products.map((product) => {
    let best = -1;
    for (const reference of product.references)
      best = Math.max(best, cosineSimilarity(centered, reference));
    return best;
  });
}
export function averageScores(frames: number[][]): number[] {
  const [first] = frames;
  if (!first) return [];
  const total = new Array<number>(first.length).fill(0);
  for (const frame of frames)
    for (let i = 0; i < total.length; i += 1) total[i] += frame[i] ?? -1;
  return total.map((value) => value / frames.length);
}
/**
 * Only the top candidate can be a match, and it must beat the runner-up by
 * the rule's margin — an absolute threshold alone cannot separate near-ties.
 */
export function rankScores(
  scores: number[],
  space: EmbeddingSpace,
  rule: MatchRule = matchRuleFor(),
  limit = MAX_RESULTS,
): DetectionResult[] {
  const ranked = space.products
    .map((product, index) => ({ product, similarity: scores[index] ?? -1 }))
    .sort((a, b) => b.similarity - a.similarity);
  const runnerUp = ranked[1]?.similarity ?? -1;
  return ranked.slice(0, limit).map(({ product, similarity }, index) => ({
    productId: product.id,
    productName: product.name,
    similarity,
    confidencePercent: Math.max(0, Math.min(100, similarity * 100)),
    isMatch:
      index === 0 &&
      similarity >= rule.threshold &&
      similarity - runnerUp >= rule.margin,
  }));
}
export function findBestMatches(
  query: ArrayLike<number>,
  space: EmbeddingSpace,
  rule: MatchRule = matchRuleFor(),
  limit = MAX_RESULTS,
): DetectionResult[] {
  return rankScores(scoreProducts(query, space), space, rule, limit);
}
