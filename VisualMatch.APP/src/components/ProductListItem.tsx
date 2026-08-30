import { StyleSheet, Text, View } from "react-native";
import type { Product } from "@/src/types/Product";
export function ProductListItem({ product }: { product: Product }) {
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
const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    gap: 14,
    padding: 16,
    backgroundColor: "#fff",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  id: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: "#dbeafe",
    alignItems: "center",
    justifyContent: "center",
  },
  idText: { color: "#1d4ed8", fontWeight: "700" },
  body: { flex: 1 },
  name: { fontSize: 17, fontWeight: "700", color: "#0f172a" },
  count: { marginTop: 4, color: "#64748b" },
});
