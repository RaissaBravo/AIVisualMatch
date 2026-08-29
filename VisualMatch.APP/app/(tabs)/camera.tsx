import { useIsFocused } from '@react-navigation/native';
import { useMemo, useState } from 'react';
import { AppState, Linking, Pressable, SafeAreaView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { Camera, useCameraDevice, useCameraPermission, usePhotoOutput } from 'react-native-vision-camera';
import { DetectionFrame } from '@/src/components/DetectionFrame';
import { DetectionResults } from '@/src/components/DetectionResults';
import { LoadingView } from '@/src/components/LoadingView';
import { ROI_HEIGHT_RATIO, ROI_WIDTH_RATIO } from '@/src/config/recognition';
import { useProductRecognition } from '@/src/hooks/useProductRecognition';
import { useProducts } from '@/src/hooks/useProducts';
import type { Size } from '@/src/utils/crop';

export default function CameraScreen() {
  const { products, modelInfo } = useProducts(); const permission = useCameraPermission(); const device = useCameraDevice('back');
  const output = usePhotoOutput({ targetResolution: { width: 1280, height: 960 }, containerFormat: 'jpeg', quality: 1, qualityPrioritization: 'speed' });
  const focused = useIsFocused(); const appActive = AppState.currentState === 'active'; const { height } = useWindowDimensions();
  const [preview, setPreview] = useState<Size>({ width: 0, height: 0 }); const previewHeight = Math.max(320, Math.min(520, height * 0.56));
  const roi = useMemo(() => ({ x: preview.width * (1 - ROI_WIDTH_RATIO) / 2, y: preview.height * (1 - ROI_HEIGHT_RATIO) / 2, width: preview.width * ROI_WIDTH_RATIO, height: preview.height * ROI_HEIGHT_RATIO }), [preview]);
  const ready = permission.hasPermission && !!device && !!modelInfo && products.length > 0 && preview.width > 0;
  const recognition = useProductRecognition(products, modelInfo, output, preview, roi, ready && focused && appActive);

  if (!permission.hasPermission) return <SafeAreaView style={styles.safe}><View style={styles.permission}><Text style={styles.permissionTitle}>Permissão da câmera</Text><Text style={styles.permissionText}>A câmera é usada somente no aparelho. Nenhuma imagem é enviada à API.</Text><Pressable style={styles.action} onPress={() => permission.canRequestPermission ? void permission.requestPermission() : void Linking.openSettings()}><Text style={styles.actionText}>{permission.canRequestPermission ? 'Permitir câmera' : 'Abrir configurações'}</Text></Pressable></View></SafeAreaView>;
  if (!device) return <SafeAreaView style={styles.safe}><LoadingView message="Câmera traseira indisponível." /></SafeAreaView>;

  return <SafeAreaView style={styles.safe}><View style={styles.header}><Text style={styles.title}>Câmera</Text><Text style={styles.subtitle}>Reconhecimento 100% offline</Text></View>
    <View style={[styles.preview, { height: previewHeight }]} onLayout={(event) => setPreview(event.nativeEvent.layout)}>
      <Camera style={StyleSheet.absoluteFill} device={device} outputs={[output]} isActive={focused && appActive} resizeMode="cover" orientationSource="device" onError={(error) => console.warn(error)} />
      {preview.width > 0 && <DetectionFrame roi={roi} />}
      <View pointerEvents="none" style={styles.instruction}><Text style={styles.instructionText}>{recognition.modelLoading ? 'Carregando modelo…' : !modelInfo ? 'Sincronize as informações do modelo' : !products.length ? 'Carregue os produtos primeiro' : 'Posicione o produto dentro do retângulo'}</Text></View>
    </View>
    {recognition.error && <Text style={styles.error}>{recognition.error}</Text>}
    <DetectionResults results={recognition.results} analyzing={recognition.analyzing} />
  </SafeAreaView>;
}
const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: '#f8fafc' }, header: { backgroundColor: '#0f172a', paddingHorizontal: 20, paddingTop: 18, paddingBottom: 14 }, title: { color: '#fff', fontSize: 28, fontWeight: '800' }, subtitle: { color: '#94a3b8' }, preview: { backgroundColor: '#020617', overflow: 'hidden' }, instruction: { position: 'absolute', bottom: 16, alignSelf: 'center', backgroundColor: 'rgba(15,23,42,.82)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 9 }, instructionText: { color: '#fff', fontWeight: '600' }, error: { color: '#b91c1c', backgroundColor: '#fee2e2', padding: 10, fontSize: 12 }, permission: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 16 }, permissionTitle: { fontSize: 24, fontWeight: '800', color: '#0f172a' }, permissionText: { color: '#475569', textAlign: 'center', lineHeight: 21 }, action: { backgroundColor: '#2563eb', paddingHorizontal: 20, paddingVertical: 13, borderRadius: 12 }, actionText: { color: '#fff', fontWeight: '700' } });
