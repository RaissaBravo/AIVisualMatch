import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { API_BASE_URL } from "@/src/config/api";
import { APP_MODEL_FILE, APP_MODEL_NAME } from "@/src/config/model";
import { useProducts } from "@/src/hooks/useProducts";
import { type Theme, useThemedStyles } from "@/src/theme/theme";

interface InfoRowProps {
  label: string;
  value: string;
  styles: ReturnType<typeof createStyles>;
}

function InfoRow({ label, value, styles }: InfoRowProps) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text selectable style={styles.value}>
        {value}
      </Text>
    </View>
  );
}

export default function InfoScreen() {
  const { modelInfo, lastSync, usingOfflineData } = useProducts();
  const styles = useThemedStyles(createStyles);

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.title}>Info</Text>
        <Text style={styles.subtitle}>Configuração do VisualMatch</Text>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.cardTitle}>API</Text>
          <InfoRow label="Endereço" value={API_BASE_URL} styles={styles} />
          <InfoRow
            label="Estado"
            value={usingOfflineData ? "Offline — usando cache local" : "Conectada"}
            styles={styles}
          />
          <InfoRow
            label="Última sincronização"
            value={
              lastSync ? new Date(lastSync).toLocaleString("pt-BR") : "Nunca"
            }
            styles={styles}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Modelo da API</Text>
          <InfoRow
            label="Modelo"
            value={modelInfo?.model || "Aguardando sincronização"}
            styles={styles}
          />
          <InfoRow
            label="Versão"
            value={modelInfo?.version || "—"}
            styles={styles}
          />
          <InfoRow
            label="Arquivo"
            value={modelInfo?.model_file || "—"}
            styles={styles}
          />
          <InfoRow
            label="Disponibilidade"
            value={
              modelInfo
                ? modelInfo.available
                  ? "Disponível"
                  : "Indisponível"
                : "Desconhecida"
            }
            styles={styles}
          />
          <InfoRow
            label="Dimensão do embedding"
            value={modelInfo?.embedding_dimension?.toString() || "—"}
            styles={styles}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Modelo do app</Text>
          <InfoRow label="Modelo" value={APP_MODEL_NAME} styles={styles} />
          <InfoRow label="Arquivo" value={APP_MODEL_FILE} styles={styles} />
          <InfoRow
            label="Execução"
            value="ONNX Runtime no dispositivo"
            styles={styles}
          />
        </View>

        <Text style={styles.note}>
          A API e o aplicativo devem usar o mesmo modelo ONNX para que os
          embeddings sejam compatíveis.
        </Text>
      </ScrollView>
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
    },
    title: { color: theme.headerTitle, fontSize: 28, fontWeight: "800" },
    subtitle: { color: theme.headerSubtitle, marginTop: 2 },
    content: { padding: 16, gap: 14, paddingBottom: 32 },
    card: {
      padding: 16,
      borderRadius: 16,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: theme.border,
      backgroundColor: theme.card,
      gap: 12,
    },
    cardTitle: {
      color: theme.textPrimary,
      fontSize: 18,
      fontWeight: "800",
      marginBottom: 2,
    },
    row: { gap: 3 },
    label: {
      color: theme.textMuted,
      fontSize: 12,
      fontWeight: "600",
      textTransform: "uppercase",
    },
    value: { color: theme.textBody, fontSize: 16, lineHeight: 22 },
    note: {
      color: theme.textMuted,
      fontSize: 13,
      lineHeight: 19,
      paddingHorizontal: 4,
    },
  });

