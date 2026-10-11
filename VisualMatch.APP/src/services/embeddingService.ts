import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";
import * as ort from "onnxruntime-react-native";
import * as UPNG from "upng-js";
import { localModelFile } from "@/src/services/modelStore";
import type { ModelInfo } from "@/src/types/ModelInfo";
import type { Rect, Size } from "@/src/utils/crop";
import { calculateCropRegion } from "@/src/utils/crop";
import { l2Normalize } from "@/src/utils/math";

interface LoadedModel {
  uri: string;
  session: Promise<ort.InferenceSession>;
  runs: number;
  retired: boolean;
}
let current: LoadedModel | null = null;

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
function release(model: LoadedModel) {
  model.session.then((session) => session.release()).catch(() => undefined);
}
/**
 * One session for the model in info. Switching models retires the previous
 * session, which is released only after its in-flight inferences finish.
 */
function acquire(info: ModelInfo): LoadedModel {
  const file = localModelFile(info);
  if (!file)
    throw new Error(
      `Modelo ${info.name ?? info.model} ainda não foi baixado; sincronize com a API.`,
    );
  if (current?.uri !== file.uri) {
    const previous = current;
    const model: LoadedModel = {
      uri: file.uri,
      session: ort.InferenceSession.create(file.uri),
      runs: 0,
      retired: false,
    };
    model.session.catch(() => {
      if (current === model) current = null;
    });
    current = model;
    if (previous) {
      previous.retired = true;
      if (!previous.runs) release(previous);
    }
  }
  return current;
}
export async function loadModel(
  info: ModelInfo,
): Promise<ort.InferenceSession> {
  return acquire(info).session;
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
  const model = acquire(info);
  const feeds: Record<string, ort.Tensor> = { [info.input_name!]: tensor };
  model.runs += 1;
  let output: ort.Tensor | undefined;
  try {
    output = (await (await model.session).run(feeds))[info.output_name!];
  } finally {
    model.runs -= 1;
    if (model.retired && !model.runs) release(model);
  }
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
