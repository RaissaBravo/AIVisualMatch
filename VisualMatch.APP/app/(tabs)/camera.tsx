import { useIsFocused } from "expo-router";
import { useMemo, useState } from "react";
import {
  AppState,
  Linking,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  usePhotoOutput,
} from "react-native-vision-camera";
import { DetectionFrame } from "@/src/components/DetectionFrame";
import { DetectionResults } from "@/src/components/DetectionResults";
import { LoadingView } from "@/src/components/LoadingView";
import { ROI_HEIGHT_RATIO, ROI_WIDTH_RATIO } from "@/src/config/recognition";
import { useProductRecognition } from "@/src/hooks/useProductRecognition";
import { useProducts } from "@/src/hooks/useProducts";
import { type Theme, useThemedStyles } from "@/src/theme/theme";
import type { Size } from "@/src/utils/crop";

const PHOTO_RESOLUTION = { width: 1280, height: 960 } as const;

export default function CameraScreen() {
  const { products, modelInfo } = useProducts();
  const styles = useThemedStyles(createStyles);
  const permission = useCameraPermission();
  const device = useCameraDevice("back");
  const output = usePhotoOutput({
    targetResolution: PHOTO_RESOLUTION,
    containerFormat: "jpeg",
    quality: 1,
    qualityPrioritization: "speed",
  });
  const focused = useIsFocused();
  const appActive = AppState.currentState === "active";
  const { height } = useWindowDimensions();
  const [preview, setPreview] = useState<Size>({ width: 0, height: 0 });
  const [sessionStarted, setSessionStarted] = useState(false);
  const previewHeight = Math.max(320, Math.min(400, height * 0.5));
  const roi = useMemo(
    () => ({
      x: (preview.width * (1 - ROI_WIDTH_RATIO)) / 2,
      y: (preview.height * (1 - ROI_HEIGHT_RATIO)) / 2,
      width: preview.width * ROI_WIDTH_RATIO,
      height: preview.height * ROI_HEIGHT_RATIO,
    }),
    [preview],
  );
  const ready =
    permission.hasPermission &&
    !!device &&
    !!modelInfo &&
    products.length > 0 &&
    preview.width > 0;
  const recognition = useProductRecognition(
    products,
    modelInfo,
    output,
    preview,
    roi,
    ready && focused && appActive && sessionStarted,
  );

  if (!permission.hasPermission)
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.permission}>
          <Text style={styles.permissionTitle}>Permissão da câmera</Text>
          <Text style={styles.permissionText}>
            A câmera é usada somente no aparelho. Nenhuma imagem é enviada à
            API.
          </Text>
          <Pressable
            style={styles.action}
            onPress={() =>
              permission.canRequestPermission
                ? void permission.requestPermission()
                : void Linking.openSettings()
            }
          >
            <Text style={styles.actionText}>
              {permission.canRequestPermission
                ? "Permitir câmera"
                : "Abrir configurações"}
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  if (!device)
    return (
      <SafeAreaView style={styles.safe}>
        <LoadingView message="Câmera traseira indisponível." />
      </SafeAreaView>
    );

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>Câmera</Text>
        <Text style={styles.subtitle}>Reconhecimento 100% offline</Text>
      </View>
      <View
        style={[styles.preview, { height: previewHeight }]}
        onLayout={(event) => setPreview(event.nativeEvent.layout)}
      >
        <Camera
          style={StyleSheet.absoluteFill}
          device={device}
          outputs={[output]}
          isActive={focused && appActive}
          resizeMode="cover"
          orientationSource="device"
          onStarted={() => setSessionStarted(true)}
          onStopped={() => setSessionStarted(false)}
          onError={(error) => console.warn(error)}
        />
        {preview.width > 0 && <DetectionFrame roi={roi} />}
        <View pointerEvents="none" style={styles.instruction}>
          <Text style={styles.instructionText}>
            {recognition.modelLoading
              ? "Carregando modelo…"
              : !modelInfo
                ? "Sincronize as informações do modelo"
                : !products.length
                  ? "Carregue os produtos primeiro"
                  : "Posicione o produto dentro do retângulo"}
          </Text>
        </View>
      </View>
      {recognition.error && (
        <Text style={styles.error}>{recognition.error}</Text>
      )}
      <DetectionResults
        results={recognition.results}
        analyzing={recognition.analyzing}
      />
    </SafeAreaView>
  );
}
const createStyles = (theme: Theme) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: theme.background },
    header: {
      backgroundColor: theme.headerBackground,
      paddingHorizontal: 20,
      paddingTop: 18,
      paddingBottom: 14,
    },
    title: { color: theme.headerTitle, fontSize: 28, fontWeight: "800" },
    subtitle: { color: theme.headerSubtitle },
    preview: { backgroundColor: theme.cameraBackground, overflow: "hidden" },
    instruction: {
      position: "absolute",
      bottom: 16,
      alignSelf: "center",
      backgroundColor: theme.overlay,
      borderRadius: 12,
      paddingHorizontal: 14,
      paddingVertical: 9,
    },
    instructionText: { color: theme.overlayText, fontWeight: "600" },
    error: {
      color: theme.danger,
      backgroundColor: theme.dangerBackground,
      padding: 10,
      fontSize: 12,
    },
    permission: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      padding: 32,
      gap: 16,
    },
    permissionTitle: {
      fontSize: 24,
      fontWeight: "800",
      color: theme.textPrimary,
    },
    permissionText: {
      color: theme.textMuted,
      textAlign: "center",
      lineHeight: 21,
    },
    action: {
      backgroundColor: theme.accent,
      paddingHorizontal: 20,
      paddingVertical: 13,
      borderRadius: 12,
    },
    actionText: { color: theme.accentText, fontWeight: "700" },
  });
