import { StyleSheet, Text, View } from 'react-native';
import type { Rect } from '@/src/utils/crop';
export function DetectionFrame({ roi }: { roi: Rect }) { return <View pointerEvents="none" style={[styles.frame, { left: roi.x, top: roi.y, width: roi.width, height: roi.height }]}><View style={styles.label}><Text style={styles.text}>ÁREA DE DETECÇÃO</Text></View></View>; }
const styles = StyleSheet.create({ frame: { position: 'absolute', borderWidth: 3, borderColor: '#60a5fa', borderRadius: 18, backgroundColor: 'transparent' }, label: { position: 'absolute', top: -28, alignSelf: 'center', backgroundColor: '#2563eb', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 }, text: { color: '#fff', fontSize: 10, fontWeight: '800', letterSpacing: 0.7 } });
