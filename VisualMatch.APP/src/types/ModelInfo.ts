export interface ModelInfo {
  model: string;
  version: string;
  model_file?: string;
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
}
