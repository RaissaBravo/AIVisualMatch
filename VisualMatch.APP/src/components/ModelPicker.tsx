import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useProducts } from "@/src/hooks/useProducts";
import { type Theme, useTheme, useThemedStyles } from "@/src/theme/theme";
import type { ModelInfo } from "@/src/types/ModelInfo";

function describe(model: ModelInfo) {
  if (!model.available) return "Indisponível na API";
  const details = [
    `${model.embedding_dimension ?? "?"} dimensões`,
    `${model.input_width}×${model.input_height} px`,
  ];
  if (model.pending_images)
    details.push(`${model.pending_images} imagens sem embedding`);
  return details.join(" · ");
}

/** Picks the model the camera runs; switching downloads its ONNX and embeddings from the API. */
export function ModelPicker() {
  const { models, modelInfo, isSyncing, switchingTo, selectModel } =
    useProducts();
  const theme = useTheme();
  const styles = useThemedStyles(createStyles);
  const [open, setOpen] = useState(false);
  const nameOf = (id: string) =>
    models.find((model) => model.model === id)?.name ?? id;
  const label = switchingTo
    ? `Baixando ${nameOf(switchingTo)}…`
    : modelInfo
      ? (modelInfo.name ?? modelInfo.model)
      : "Escolher modelo";

  const pick = async (model: ModelInfo) => {
    setOpen(false);
    if (model.model === modelInfo?.model) return;
    const error = await selectModel(model.model);
    if (error) Alert.alert("Não foi possível trocar o modelo", error);
  };

  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Modelo de reconhecimento: ${label}. Toque para trocar.`}
        disabled={isSyncing || !models.length}
        onPress={() => setOpen(true)}
        style={({ pressed }) => [styles.trigger, pressed && styles.pressed]}
      >
        {switchingTo && (
          <ActivityIndicator size="small" color={theme.badgeText} />
        )}
        <Text style={styles.triggerText} numberOfLines={1}>
          {label}
        </Text>
        {!switchingTo && <Text style={styles.triggerText}>▾</Text>}
      </Pressable>
      <Modal
        visible={open}
        transparent
        animationType="fade"
        onRequestClose={() => setOpen(false)}
      >
        <View style={styles.overlay}>
          <Pressable
            accessibilityLabel="Fechar"
            style={StyleSheet.absoluteFill}
            onPress={() => setOpen(false)}
          />
          <View style={styles.sheet}>
            <Text style={styles.title}>Modelo de reconhecimento</Text>
            <Text style={styles.hint}>
              Ao trocar, o app baixa da API o modelo e os embeddings dele.
            </Text>
            {models.map((model) => {
              const selected = model.model === modelInfo?.model;
              return (
                <Pressable
                  key={model.model}
                  accessibilityRole="button"
                  accessibilityState={{
                    selected,
                    disabled: !model.available,
                  }}
                  disabled={!model.available}
                  onPress={() => void pick(model)}
                  style={({ pressed }) => [
                    styles.option,
                    selected && styles.optionSelected,
                    !model.available && styles.optionDisabled,
                    pressed && styles.pressed,
                  ]}
                >
                  <View style={styles.optionText}>
                    <Text style={styles.optionName}>
                      {model.name ?? model.model}
                    </Text>
                    <Text style={styles.optionMeta}>{describe(model)}</Text>
                  </View>
                  {selected && <Text style={styles.check}>✓</Text>}
                </Pressable>
              );
            })}
          </View>
        </View>
      </Modal>
    </>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    trigger: {
      flexDirection: "row",
      alignItems: "center",
      gap: 6,
      maxWidth: 200,
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: 999,
      backgroundColor: theme.badgeBackground,
    },
    triggerText: { color: theme.badgeText, fontWeight: "700", flexShrink: 1 },
    pressed: { opacity: 0.7 },
    overlay: {
      flex: 1,
      justifyContent: "center",
      padding: 24,
      backgroundColor: "rgba(2,6,23,.55)",
    },
    sheet: {
      alignSelf: "center",
      width: "100%",
      maxWidth: 420,
      padding: 18,
      gap: 10,
      borderRadius: 18,
      backgroundColor: theme.card,
    },
    title: { color: theme.textPrimary, fontSize: 19, fontWeight: "800" },
    hint: { color: theme.textMuted, marginBottom: 4 },
    option: {
      flexDirection: "row",
      alignItems: "center",
      gap: 10,
      padding: 13,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: theme.border,
    },
    optionSelected: {
      borderColor: theme.accent,
      backgroundColor: theme.badgeBackground,
    },
    optionDisabled: { opacity: 0.45 },
    optionText: { flex: 1, gap: 2 },
    optionName: { color: theme.textPrimary, fontSize: 16, fontWeight: "700" },
    optionMeta: { color: theme.textMuted, fontSize: 13 },
    check: { color: theme.accent, fontSize: 18, fontWeight: "800" },
  });
