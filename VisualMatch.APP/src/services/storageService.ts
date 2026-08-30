import AsyncStorage from "@react-native-async-storage/async-storage";
import type { ModelInfo } from "@/src/types/ModelInfo";
import type { Product } from "@/src/types/Product";
export const PRODUCTS_STORAGE_KEY = "@visualmatch/products/v1";
export const MODEL_INFO_STORAGE_KEY = "@visualmatch/model-info/v1";
export const LAST_SYNC_STORAGE_KEY = "@visualmatch/last-sync/v1";
async function readJson<T>(key: string): Promise<T | null> {
  const raw = await AsyncStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}
export const getProducts = () => readJson<Product[]>(PRODUCTS_STORAGE_KEY);
export const getModelInfo = () => readJson<ModelInfo>(MODEL_INFO_STORAGE_KEY);
export const getLastSync = () => AsyncStorage.getItem(LAST_SYNC_STORAGE_KEY);
export const saveProducts = (products: Product[]) =>
  AsyncStorage.setItem(PRODUCTS_STORAGE_KEY, JSON.stringify(products));
export const saveModelInfo = (info: ModelInfo) =>
  AsyncStorage.setItem(MODEL_INFO_STORAGE_KEY, JSON.stringify(info));
export const saveLastSync = (timestamp: string) =>
  AsyncStorage.setItem(LAST_SYNC_STORAGE_KEY, timestamp);
export const clearProducts = () =>
  AsyncStorage.multiRemove([
    PRODUCTS_STORAGE_KEY,
    MODEL_INFO_STORAGE_KEY,
    LAST_SYNC_STORAGE_KEY,
  ]);
