import { StyleSheet, Text, View } from "react-native";
import type { Product } from "@/src/types/Product";
import { type Theme, useThemedStyles } from "@/src/theme/theme";
export function ProductListItem({ product }: { product: Product }) {
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.card}>
      <View style={styles.id}>
        <Text style={styles.idText}>{product.id}</Text>
      </View>
      <View style={styles.body}>
        <Text style={styles.name}>{product.name}</Text>
        <Text style={styles.count}>
          {product.embeddings.length}{" "}
          {product.embeddings.length === 1 ? "referência" : "referências"}
        </Text>
      </View>
    </View>
  );
}
const createStyles = (theme: Theme) =>
  StyleSheet.create({
    card: {
      flexDirection: "row",
      gap: 14,
      padding: 16,
      backgroundColor: theme.card,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: theme.border,
    },
    id: {
      width: 38,
      height: 38,
      borderRadius: 12,
      backgroundColor: theme.badgeBackground,
      alignItems: "center",
      justifyContent: "center",
    },
    idText: { color: theme.badgeText, fontWeight: "700" },
    body: { flex: 1 },
    name: { fontSize: 17, fontWeight: "700", color: theme.textPrimary },
    count: { marginTop: 4, color: theme.textMuted },
  });
