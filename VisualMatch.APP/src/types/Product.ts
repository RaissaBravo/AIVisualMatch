export interface Product {
  id: number;
  name: string;
  embeddings: number[][];
}
export interface DetectionResult {
  productId: number;
  productName: string;
  similarity: number;
  confidencePercent: number;
  isMatch: boolean;
}
