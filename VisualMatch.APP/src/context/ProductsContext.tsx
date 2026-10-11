import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { fetchModels, fetchProducts } from "@/src/services/apiService";
import { ensureModelFile } from "@/src/services/modelStore";
import * as storage from "@/src/services/storageService";
import type { ModelInfo } from "@/src/types/ModelInfo";
import type { Product } from "@/src/types/Product";

interface ProductsState {
  products: Product[];
  /** Model the cached embeddings belong to, i.e. the one the camera runs. */
  modelInfo: ModelInfo | null;
  /** Every model the API keeps ready, for the model picker. */
  models: ModelInfo[];
  /** Model being downloaded after a pick, until it replaces modelInfo. */
  switchingTo: string | null;
  lastSync: string | null;
  isLoadingLocal: boolean;
  isSyncing: boolean;
  error: string | null;
  warning: string | null;
  usingOfflineData: boolean;
  sync: (silent?: boolean) => Promise<boolean>;
  /** Downloads the model's ONNX and embeddings, then switches to it; resolves to an error or null. */
  selectModel: (model: string) => Promise<string | null>;
}
const ProductsContext = createContext<ProductsState | null>(null);
const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Erro inesperado.";
function coverageWarning(products: Product[], model: ModelInfo) {
  const missing = products.filter((p) => !p.embeddings.length).length;
  return missing
    ? `${missing} de ${products.length} produtos sem embeddings de ${model.name ?? model.model}. Gere-os no painel da API.`
    : null;
}

export function ProductsProvider({ children }: PropsWithChildren) {
  const [products, setProducts] = useState<Product[]>([]);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [switchingTo, setSwitchingTo] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [isLoadingLocal, setLoadingLocal] = useState(true);
  const [isSyncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [usingOfflineData, setUsingOfflineData] = useState(false);
  // Refs keep syncModel stable; depending on state would re-run the startup sync.
  const currentModel = useRef<string | null>(null);
  const syncing = useRef(false);

  /** Syncs the requested model, else the current one, else the first available. */
  const syncModel = useCallback(
    async (requested: string | null, silent: boolean) => {
      if (syncing.current) return "Uma sincronização já está em andamento.";
      syncing.current = true;
      setSyncing(true);
      if (!silent) setError(null);
      try {
        const remoteModels = await fetchModels();
        setModels(remoteModels);
        await storage.saveModels(remoteModels);
        const target = requested ?? currentModel.current;
        const remoteModel = target
          ? remoteModels.find((model) => model.model === target)
          : remoteModels.find((model) => model.available);
        if (!remoteModel)
          throw new Error(
            target
              ? `o modelo ${target} não está registrado na API.`
              : "a API não tem modelos disponíveis.",
          );
        if (!remoteModel.available)
          throw new Error(
            remoteModel.error ||
              `o modelo ${remoteModel.model} não está disponível na API.`,
          );
        const remoteProducts = await fetchProducts(
          remoteModel.model,
          remoteModel.embedding_dimension,
        );
        // The cache must only ever point at a model already stored on the device.
        await ensureModelFile(remoteModel);
        const timestamp = new Date().toISOString();
        await Promise.all([
          storage.saveProducts(remoteProducts),
          storage.saveModelInfo(remoteModel),
          storage.saveLastSync(timestamp),
        ]);
        currentModel.current = remoteModel.model;
        setProducts(remoteProducts);
        setModelInfo(remoteModel);
        setLastSync(timestamp);
        setUsingOfflineData(false);
        setError(null);
        setWarning(coverageWarning(remoteProducts, remoteModel));
        return null;
      } catch (caught) {
        const message = errorMessage(caught);
        setError(`Não foi possível sincronizar: ${message}`);
        setWarning(null);
        setUsingOfflineData(true);
        return message;
      } finally {
        syncing.current = false;
        setSyncing(false);
      }
    },
    [],
  );
  const sync = useCallback(
    async (silent = false) => (await syncModel(null, silent)) === null,
    [syncModel],
  );
  const selectModel = useCallback(
    async (model: string) => {
      setSwitchingTo(model);
      try {
        return await syncModel(model, false);
      } finally {
        setSwitchingTo(null);
      }
    },
    [syncModel],
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [savedProducts, savedModel, savedModels, savedSync] =
          await Promise.all([
            storage.getProducts(),
            storage.getModelInfo(),
            storage.getModels(),
            storage.getLastSync(),
          ]);
        if (mounted) {
          currentModel.current = savedModel?.model ?? null;
          setProducts(savedProducts ?? []);
          setModelInfo(savedModel);
          setModels(savedModels ?? []);
          setLastSync(savedSync);
        }
      } catch (caught) {
        if (mounted)
          setError(`Falha ao carregar dados locais: ${errorMessage(caught)}`);
      } finally {
        if (mounted) {
          setLoadingLocal(false);
          void sync(true);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, [sync]);

  const value = useMemo(
    () => ({
      products,
      modelInfo,
      models,
      switchingTo,
      lastSync,
      isLoadingLocal,
      isSyncing,
      error,
      warning,
      usingOfflineData,
      sync,
      selectModel,
    }),
    [
      products,
      modelInfo,
      models,
      switchingTo,
      lastSync,
      isLoadingLocal,
      isSyncing,
      error,
      warning,
      usingOfflineData,
      sync,
      selectModel,
    ],
  );
  return (
    <ProductsContext.Provider value={value}>
      {children}
    </ProductsContext.Provider>
  );
}
export function useProducts() {
  const value = useContext(ProductsContext);
  if (!value)
    throw new Error("useProducts deve estar dentro de ProductsProvider.");
  return value;
}
