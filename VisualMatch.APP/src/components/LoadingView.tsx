import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
export function LoadingView({ message }: { message: string }) { return <View style={styles.root}><ActivityIndicator color="#2563eb" /><Text style={styles.text}>{message}</Text></View>; }
const styles = StyleSheet.create({ root: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, padding: 24 }, text: { color: '#475569', textAlign: 'center' } });
