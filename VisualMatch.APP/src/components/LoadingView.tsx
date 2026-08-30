import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { type Theme, useTheme, useThemedStyles } from "@/src/theme/theme";
export function LoadingView({ message }: { message: string }) {
  const theme = useTheme();
  const styles = useThemedStyles(createStyles);
  return (
    <View style={styles.root}>
      <ActivityIndicator color={theme.accent} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}
const createStyles = (theme: Theme) =>
  StyleSheet.create({
    root: {
      flex: 1,
      alignItems: "center",
      justifyContent: "center",
      gap: 12,
      padding: 24,
    },
    text: { color: theme.textMuted, textAlign: "center" },
  });
