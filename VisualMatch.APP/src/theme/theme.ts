import { useMemo } from "react";
import { useColorScheme } from "react-native";

const light = {
  background: "#f8fafc",
  card: "#ffffff",
  border: "#e2e8f0",
  headerBackground: "#0f172a",
  headerTitle: "#ffffff",
  headerSubtitle: "#94a3b8",
  cameraBackground: "#020617",
  overlay: "rgba(15,23,42,.82)",
  overlayText: "#ffffff",
  textPrimary: "#0f172a",
  textBody: "#1e293b",
  textMuted: "#64748b",
  accent: "#2563eb",
  accentText: "#ffffff",
  badgeBackground: "#dbeafe",
  badgeText: "#1d4ed8",
  success: "#15803d",
  successBackground: "#dcfce7",
  successBorder: "#86efac",
  warning: "#b45309",
  danger: "#b91c1c",
  dangerBackground: "#fee2e2",
  tabInactive: "#64748b",
};

export type Theme = typeof light;

const dark: Theme = {
  background: "#0b1220",
  card: "#1e293b",
  border: "#334155",
  headerBackground: "#020617",
  headerTitle: "#f8fafc",
  headerSubtitle: "#94a3b8",
  cameraBackground: "#000000",
  overlay: "rgba(2,6,23,.85)",
  overlayText: "#f8fafc",
  textPrimary: "#f1f5f9",
  textBody: "#e2e8f0",
  textMuted: "#94a3b8",
  accent: "#3b82f6",
  accentText: "#f8fafc",
  badgeBackground: "#1e3a8a",
  badgeText: "#bfdbfe",
  success: "#4ade80",
  successBackground: "#14532d",
  successBorder: "#166534",
  warning: "#fbbf24",
  danger: "#fca5a5",
  dangerBackground: "#450a0a",
  tabInactive: "#94a3b8",
};

export function useTheme(): Theme {
  return useColorScheme() === "dark" ? dark : light;
}

/** Rebuilds a StyleSheet whenever the OS color scheme changes. */
export function useThemedStyles<T>(factory: (theme: Theme) => T): T {
  const theme = useTheme();
  return useMemo(() => factory(theme), [factory, theme]);
}
