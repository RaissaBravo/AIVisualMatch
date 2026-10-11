import { Directory, File, Paths } from "expo-file-system";
import { API_BASE_URL } from "@/src/config/api";
import type { ModelInfo } from "@/src/types/ModelInfo";

const modelsDirectory = new Directory(Paths.document, "models");

/** The md5 in the name changes whenever the API re-exports the model. */
function modelFile(info: ModelInfo): File {
  if (!info.model_md5 || !info.model_size)
    throw new Error(
      "model-info não informa md5/tamanho do ONNX; atualize a API.",
    );
  return new File(modelsDirectory, `${info.model}-${info.model_md5}.onnx`);
}

const isVersionOf = (name: string, model: string) =>
  name.startsWith(`${model}-`) &&
  /^[0-9a-f]{32}\.onnx(\.part)?$/.test(name.slice(model.length + 1));

/** Copy of the exact ONNX described by info, or null if it was never downloaded. */
export function localModelFile(info: ModelInfo): File | null {
  const file = modelFile(info);
  return file.exists && file.size === info.model_size ? file : null;
}

/**
 * Downloads the ONNX the API serves for this model and verifies it before use.
 * Other models stay cached, so switching back does not download them again.
 */
export async function ensureModelFile(info: ModelInfo): Promise<File> {
  const cached = localModelFile(info);
  if (cached) return cached;
  if (!info.model_url)
    throw new Error("model-info não informa a URL do modelo.");
  modelsDirectory.create({ idempotent: true, intermediates: true });
  const target = modelFile(info);
  const partial = new File(modelsDirectory, `${target.name}.part`);
  await File.downloadFileAsync(`${API_BASE_URL}${info.model_url}`, partial, {
    idempotent: true,
  });
  if (
    partial.size !== info.model_size ||
    partial.info({ md5: true }).md5 !== info.model_md5
  ) {
    partial.delete();
    throw new Error(`Download do modelo ${info.model} chegou corrompido.`);
  }
  if (target.exists) target.delete();
  partial.rename(target.name);
  for (const entry of modelsDirectory.list())
    if (
      entry instanceof File &&
      entry.name !== target.name &&
      isVersionOf(entry.name, info.model)
    )
      entry.delete();
  return target;
}
