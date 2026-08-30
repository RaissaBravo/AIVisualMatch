import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { ProductListItem } from "@/src/components/ProductListItem";
import { useProducts } from "@/src/hooks/useProducts";
import { type Theme, useTheme, useThemedStyles } from "@/src/theme/theme";

export default function ProductsScreen() {
  const {
    products,
    lastSync,
    isLoadingLocal,
    isSyncing,
    error,
    warning,
    usingOfflineData,
    sync,
  } = useProducts();
  const theme = useTheme();
  const styles = useThemedStyles(createStyles);
  const [message, setMessage] = useState<string | null>(null);
  const refresh = async () => {
    const ok = await sync();
    setMessage(
      ok
        ? "Produtos atualizados e salvos no aparelho."
        : "API indisponível. Os dados locais foram mantidos.",
    );
    if (ok)
      Alert.alert(
        "Sincronização concluída",
        "Os produtos estão disponíveis offline.",
      );
  };
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Produtos</Text>
          <Text style={styles.subtitle}>{products.length} cadastrados</Text>
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Atualizar produtos"
          disabled={isSyncing}
          onPress={refresh}
          style={styles.button}
        >
          {isSyncing ? (
            <ActivityIndicator color={theme.accentText} />
          ) : (
            <Text style={styles.refresh}>↻</Text>
          )}
        </Pressable>
      </View>
      <View style={styles.meta}>
        <Text style={styles.sync}>
          Última atualização:{" "}
          {lastSync ? new Date(lastSync).toLocaleString("pt-BR") : "nunca"}
        </Text>
        {usingOfflineData && (
          <Text style={styles.warning}>
            Modo offline — dados locais em uso.
          </Text>
        )}
        {warning && <Text style={styles.warning}>{warning}</Text>}
        {error && <Text style={styles.error}>{error}</Text>}
        {message && <Text style={styles.message}>{message}</Text>}
      </View>
      <FlatList
        data={products}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        refreshing={isSyncing}
        onRefresh={refresh}
        renderItem={({ item }) => <ProductListItem product={item} />}
        ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
        ListEmptyComponent={
          <Text style={styles.empty}>
            {isLoadingLocal
              ? "Carregando produtos locais…"
              : "Nenhum produto salvo. Toque em ↻ para sincronizar."}
          </Text>
        }
      />
    </SafeAreaView>
  );
}
const createStyles = (theme: Theme) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: theme.background },
    header: {
      paddingHorizontal: 20,
      paddingTop: 18,
      paddingBottom: 14,
      backgroundColor: theme.headerBackground,
      flexDirection: "row",
      justifyContent: "space-between",
      alignItems: "center",
    },
    title: { color: theme.headerTitle, fontSize: 28, fontWeight: "800" },
    subtitle: { color: theme.headerSubtitle, marginTop: 2 },
    button: {
      width: 44,
      height: 44,
      borderRadius: 14,
      backgroundColor: theme.accent,
      alignItems: "center",
      justifyContent: "center",
    },
    refresh: { color: theme.accentText, fontSize: 28, lineHeight: 30 },
    meta: { padding: 16, gap: 4 },
    sync: { color: theme.textMuted, fontSize: 12 },
    warning: { color: theme.warning, fontWeight: "600" },
    error: { color: theme.danger, fontWeight: "600" },
    message: { color: theme.textBody },
    list: { padding: 16, paddingTop: 0, flexGrow: 1 },
    empty: {
      color: theme.textMuted,
      textAlign: "center",
      marginTop: 60,
      paddingHorizontal: 30,
    },
  });
