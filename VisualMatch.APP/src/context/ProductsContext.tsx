import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchModelInfo, fetchProducts } from '@/src/services/apiService';
import * as storage from '@/src/services/storageService';
import type { ModelInfo } from '@/src/types/ModelInfo';
import type { Product } from '@/src/types/Product';

interface ProductsState {
  products: Product[]; modelInfo: ModelInfo | null; lastSync: string | null;
  isLoadingLocal: boolean; isSyncing: boolean; error: string | null; usingOfflineData: boolean;
  sync: (silent?: boolean) => Promise<boolean>;
}
const ProductsContext = createContext<ProductsState | null>(null);
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Erro inesperado.';

export function ProductsProvider({ children }: PropsWithChildren) {
  const [products, setProducts] = useState<Product[]>([]); const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [lastSync, setLastSync] = useState<string | null>(null); const [isLoadingLocal, setLoadingLocal] = useState(true);
  const [isSyncing, setSyncing] = useState(false); const [error, setError] = useState<string | null>(null);
  const [usingOfflineData, setUsingOfflineData] = useState(false);

  const sync = useCallback(async (silent = false) => {
    setSyncing(true); if (!silent) setError(null);
    try {
      const remoteModel = await fetchModelInfo();
      if (!remoteModel.available) throw new Error(remoteModel.error || 'Modelo indisponível no backend.');
      const remoteProducts = await fetchProducts(remoteModel.embedding_dimension);
      const timestamp = new Date().toISOString();
      await Promise.all([storage.saveProducts(remoteProducts), storage.saveModelInfo(remoteModel), storage.saveLastSync(timestamp)]);
      setProducts(remoteProducts); setModelInfo(remoteModel); setLastSync(timestamp); setUsingOfflineData(false); return true;
    } catch (caught) {
      setError(`Não foi possível sincronizar: ${errorMessage(caught)}`); setUsingOfflineData(true); return false;
    } finally { setSyncing(false); }
  }, []);

  useEffect(() => { let mounted = true; (async () => {
    try {
      const [savedProducts, savedModel, savedSync] = await Promise.all([storage.getProducts(), storage.getModelInfo(), storage.getLastSync()]);
      if (mounted) { setProducts(savedProducts ?? []); setModelInfo(savedModel); setLastSync(savedSync); }
    } catch (caught) { if (mounted) setError(`Falha ao carregar dados locais: ${errorMessage(caught)}`); }
    finally { if (mounted) { setLoadingLocal(false); void sync(true); } }
  })(); return () => { mounted = false; }; }, [sync]);

  const value = useMemo(() => ({ products, modelInfo, lastSync, isLoadingLocal, isSyncing, error, usingOfflineData, sync }), [products, modelInfo, lastSync, isLoadingLocal, isSyncing, error, usingOfflineData, sync]);
  return <ProductsContext.Provider value={value}>{children}</ProductsContext.Provider>;
}
export function useProducts() { const value = useContext(ProductsContext); if (!value) throw new Error('useProducts deve estar dentro de ProductsProvider.'); return value; }
