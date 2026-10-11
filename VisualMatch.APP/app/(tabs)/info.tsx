import { ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { API_BASE_URL } from "@/src/config/api";
import { matchRuleFor } from "@/src/config/recognition";
import { useProducts } from "@/src/hooks/useProducts";
import { localModelFile } from "@/src/services/modelStore";
import { type Theme, useThemedStyles } from "@/src/theme/theme";
import type { ModelInfo } from "@/src/types/ModelInfo";

function localModelStatus(info: ModelInfo | null) {
  if (!info) return "Aguardando sincronização";
  try {
    const file = localModelFile(info);
    return file
      ? `Baixado (${(file.size / 1024 / 1024).toFixed(1)} MB)`
      : "Não baixado — sincronize com a API";
  } catch (error) {
    return error instanceof Error ? error.message : "Desconhecido";
  }
}

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
  const rule = matchRuleFor(modelInfo?.model);

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
          <Text style={styles.cardTitle}>Modelo em uso</Text>
          <InfoRow
            label="Modelo"
            value={
              modelInfo
                ? `${modelInfo.name ?? modelInfo.model} (${modelInfo.model})`
                : "Aguardando sincronização"
            }
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
          <InfoRow
            label="Entrada"
            value={
              modelInfo
                ? `${modelInfo.input_width}×${modelInfo.input_height} px`
                : "—"
            }
            styles={styles}
          />
          <InfoRow
            label="Licença"
            value={modelInfo?.license || "—"}
            styles={styles}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Arquivo no aparelho</Text>
          <InfoRow
            label="Arquivo local"
            value={localModelStatus(modelInfo)}
            styles={styles}
          />
          <InfoRow
            label="MD5"
            value={modelInfo?.model_md5 || "—"}
            styles={styles}
          />
          <InfoRow
            label="Regra de match"
            value={`limiar ${rule.threshold} · margem ${rule.margin}`}
            styles={styles}
          />
          <InfoRow
            label="Execução"
            value="ONNX Runtime no dispositivo"
            styles={styles}
          />
        </View>

        <Text style={styles.note}>
          A API mantém os embeddings de todos os modelos. Troque o modelo no
          topo da tela Câmera: o app baixa o arquivo ONNX (verificado por MD5) e
          os embeddings do modelo escolhido.
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

