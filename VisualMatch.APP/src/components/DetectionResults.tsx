import { ScrollView, StyleSheet, Text, View } from "react-native";
import type { DetectionResult } from "@/src/types/Product";
export function DetectionResults({
  results,
  analyzing,
}: {
  results: DetectionResult[];
  analyzing: boolean;
}) {
  const hasMatch = results.some((result) => result.isMatch);
  return (
    <View style={styles.root}>
      <View style={styles.heading}>
        <Text style={styles.title}>Detectados</Text>
        {analyzing && <Text style={styles.analyzing}>Analisando…</Text>}
      </View>
      {!results.length ? (
        <Text style={styles.empty}>
          Posicione o produto dentro do retângulo.
        </Text>
      ) : (
        <>
          {/* <Text
            style={[styles.summary, hasMatch ? styles.success : styles.miss]}
          >
            {hasMatch
              ? "✓ Produto identificado"
              : "Nenhum produto identificado"}
          </Text> */}
          <ScrollView contentContainerStyle={{ gap: 5, paddingBottom: 5 }} style={{ maxHeight: 200, flex: 1 }}>
          {results.map((result) => (
            <View
              key={result.productId}
              style={[styles.row, result.isMatch && styles.match]}
            >
              <Text style={styles.name}>
                {result.isMatch ? "✓ " : ""}
                {result.productName}
              </Text>
              <Text style={[styles.score, result.isMatch && styles.scoreMatch]}>
                {Math.round(result.confidencePercent)}%
              </Text>
            </View>
          ))}
          </ScrollView>
        </>
      )}
    </View>
  );
}
const styles = StyleSheet.create({
  root: { padding: 18, backgroundColor: "#f8fafc", gap: 9, flex: 1, paddingBottom: 0},
  heading: { flexDirection: "row", justifyContent: "space-between" },
  title: { fontSize: 19, fontWeight: "800", color: "#0f172a" },
  analyzing: { color: "#2563eb" },
  empty: { color: "#64748b", paddingVertical: 14 },
  summary: { fontWeight: "700" },
  success: { color: "#15803d" },
  miss: { color: "#b45309" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 12,
    borderRadius: 10,
    backgroundColor: "#fff",
  },
  match: { backgroundColor: "#dcfce7", borderWidth: 1, borderColor: "#86efac" },
  name: { color: "#1e293b", fontWeight: "600" },
  score: { color: "#64748b", fontWeight: "800" },
  scoreMatch: { color: "#15803d" },
});
