export interface ModelInfo {
  model: string;
  name?: string;
  version: string;
  license?: string;
  model_file?: string;
  /** Path on the API to download the exact ONNX it uses for this model. */
  model_url?: string;
  model_size?: number | null;
  model_md5?: string | null;
  available: boolean;
  error?: string | null;
  input_name: string | null;
  output_name: string | null;
  input_shape: (number | string | null)[] | null;
  output_shape: (number | string | null)[] | null;
  input_width: number;
  input_height: number;
  input_layout: "NHWC" | "NCHW" | null;
  color_format: "RGB";
  input_dtype: "uint8" | "float32" | null;
  resize_mode: string;
  resize_algorithm: string;
  normalization: { location?: string; mean?: number[]; std?: number[] };
  l2_normalization: boolean;
  embedding_dimension: number | null;
  /** Coverage reported by /api/models: images with a current embedding of this model. */
  embedded_images?: number;
  pending_images?: number;
  total_images?: number;
}
