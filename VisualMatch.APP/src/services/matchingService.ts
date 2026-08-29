import { MATCH_THRESHOLD, MAX_RESULTS } from '@/src/config/recognition';
import type { DetectionResult, Product } from '@/src/types/Product';
import { dotProduct } from '@/src/utils/math';
export const cosineSimilarity = (a: ArrayLike<number>, b: ArrayLike<number>) => dotProduct(a, b);
export function findBestMatches(query: ArrayLike<number>, products: Product[], limit = MAX_RESULTS): DetectionResult[] {
  return products.flatMap((product) => {
    let best = -Infinity;
    for (const embedding of product.embeddings) if (embedding.length === query.length) best = Math.max(best, cosineSimilarity(query, embedding));
    if (!Number.isFinite(best)) return [];
    return [{ productId: product.id, productName: product.name, similarity: best, confidencePercent: Math.max(0, Math.min(100, best * 100)), isMatch: best >= MATCH_THRESHOLD }];
  }).sort((a, b) => b.similarity - a.similarity).slice(0, limit);
}
