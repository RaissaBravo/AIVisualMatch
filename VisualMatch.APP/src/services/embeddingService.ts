import { Asset } from "expo-asset";
import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import * as ort from "onnxruntime-react-native";
import * as UPNG from "upng-js";
import type { ModelInfo } from "@/src/types/ModelInfo";
import type { Rect, Size } from "@/src/utils/crop";
import { calculateCropRegion } from "@/src/utils/crop";
import { l2Normalize } from "@/src/utils/math";

let sessionPromise: Promise<ort.InferenceSession> | null = null;
// Metro requires a static reference so the binary is bundled in the native app.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const modelAsset = Asset.fromModule(
  require("../../assets/models/mobilenetv2_embedding.onnx"),
);

function validateContract(info: ModelInfo) {
  if (
    info.input_dtype !== "uint8" ||
    info.input_layout !== "NHWC" ||
    info.color_format !== "RGB"
  )
    throw new Error(
      `Modelo incompatível: esperado uint8/NHWC/RGB, recebido ${info.input_dtype}/${info.input_layout}/${info.color_format}.`,
    );
  if (!info.input_name || !info.output_name || !info.embedding_dimension)
    throw new Error("model-info não contém nomes ou dimensão do modelo.");
}
export async function loadModel(): Promise<ort.InferenceSession> {
  if (!sessionPromise)
    sessionPromise = (async () => {
      await modelAsset.downloadAsync();
      const uri = modelAsset.localUri ?? modelAsset.uri;
      if (!uri) throw new Error("Asset ONNX não encontrado.");
      return ort.InferenceSession.create(uri);
    })().catch((error) => {
      sessionPromise = null;
      throw error;
    });
  return sessionPromise;
}
function rgbaToRgb(data: ArrayLike<number>, pixels: number): Uint8Array {
  if (data.length !== pixels * 4)
    throw new Error("PNG processado não está em RGBA de 8 bits.");
  const rgb = new Uint8Array(pixels * 3);
  for (let p = 0, q = 0; p < data.length; p += 4) {
    rgb[q++] = data[p];
    rgb[q++] = data[p + 1];
    rgb[q++] = data[p + 2];
  }
  return rgb;
}
async function imageUriToTensor(
  uri: string,
  info: ModelInfo,
): Promise<ort.Tensor> {
  const resized = await manipulateAsync(
    uri,
    [{ resize: { width: info.input_width, height: info.input_height } }],
    { format: SaveFormat.PNG, compress: 1 },
  );
  const fileBytes = await new File(resized.uri).bytes();
  const png = UPNG.decode(Uint8Array.from(fileBytes).buffer);
  if (png.width !== info.input_width || png.height !== info.input_height)
    throw new Error("Resize produziu dimensão inesperada.");
  const rgbaFrames = UPNG.toRGBA8(png);
  if (rgbaFrames.length !== 1)
    throw new Error("PNG processado possui múltiplos frames.");
  const rgb = rgbaToRgb(new Uint8Array(rgbaFrames[0]), png.width * png.height);
  return new ort.Tensor("uint8", rgb, [
    1,
    info.input_height,
    info.input_width,
    3,
  ]);
}
export async function preprocessImage(
  uri: string,
  info: ModelInfo,
): Promise<ort.Tensor> {
  validateContract(info);
  return imageUriToTensor(uri, info);
}
export async function preprocessRoi(
  uri: string,
  source: Size,
  preview: Size,
  roi: Rect,
  info: ModelInfo,
): Promise<ort.Tensor> {
  validateContract(info);
  const crop = calculateCropRegion(preview, source, roi);
  const cropped = await manipulateAsync(
    uri,
    [
      {
        crop: {
          originX: crop.x,
          originY: crop.y,
          width: crop.width,
          height: crop.height,
        },
      },
    ],
    { format: SaveFormat.PNG, compress: 1 },
  );
  return imageUriToTensor(cropped.uri, info);
}
export async function generateEmbedding(
  tensor: ort.Tensor,
  info: ModelInfo,
): Promise<Float32Array> {
  validateContract(info);
  const session = await loadModel();
  const feeds: Record<string, ort.Tensor> = { [info.input_name!]: tensor };
  const output = (await session.run(feeds))[info.output_name!];
  if (!output)
    throw new Error(`Output ONNX ${info.output_name} não encontrado.`);
  const values = output.data as ArrayLike<number>;
  if (values.length !== info.embedding_dimension)
    throw new Error(
      `Embedding mobile tem dimensão ${values.length}; esperado ${info.embedding_dimension}.`,
    );
  return info.l2_normalization
    ? l2Normalize(values)
    : Float32Array.from(values);
}
