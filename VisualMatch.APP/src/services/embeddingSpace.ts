import { MIN_REFERENCES_FOR_CENTERING } from "@/src/config/recognition";
import type { Product } from "@/src/types/Product";
import { centerAndNormalize, meanVector } from "@/src/utils/math";

export interface SpaceProduct {
  id: number;
  name: string;
  references: Float32Array[];
}
export interface EmbeddingSpace {
  dimension: number;
  mean: Float32Array;
  products: SpaceProduct[];
}

const EMPTY: EmbeddingSpace = {
  dimension: 0,
  mean: new Float32Array(0),
  products: [],
};

/**
 * Precomputes the reference centroid and the centered/normalized references so
 * every frame only pays for the query-side centering.
 */
export function buildEmbeddingSpace(products: Product[]): EmbeddingSpace {
  const dimension =
    products.flatMap((product) => product.embeddings).find((e) => e.length > 0)
      ?.length ?? 0;
  if (!dimension) return EMPTY;
  const usable = products.map((product) => ({
    product,
    embeddings: product.embeddings.filter((e) => e.length === dimension),
  }));
  const all = usable.flatMap((entry) => entry.embeddings);
  const mean =
    all.length >= MIN_REFERENCES_FOR_CENTERING
      ? meanVector(all, dimension)
      : new Float32Array(dimension);
  const spaceProducts = usable.flatMap<SpaceProduct>(
    ({ product, embeddings }) => {
      const references = embeddings
        .map((embedding) => centerAndNormalize(embedding, mean))
        .filter((value): value is Float32Array => value !== null);
      return references.length
        ? [{ id: product.id, name: product.name, references }]
        : [];
    },
  );
  return spaceProducts.length
    ? { dimension, mean, products: spaceProducts }
    : EMPTY;
}
