import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ProductsProvider } from "@/src/context/ProductsContext";
import { useTheme } from "@/src/theme/theme";

export default function RootLayout() {
  const theme = useTheme();
  return (
    <ProductsProvider>
      <StatusBar style="auto" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: theme.background },
        }}
      />
    </ProductsProvider>
  );
}
