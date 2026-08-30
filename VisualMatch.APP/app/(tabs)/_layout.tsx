import { SymbolView } from "expo-symbols";
import { Tabs } from "expo-router";
import { useTheme } from "@/src/theme/theme";

export default function TabLayout() {
  const theme = useTheme();
  return (
    <Tabs
      initialRouteName="products"
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.accent,
        tabBarInactiveTintColor: theme.tabInactive,
        tabBarStyle: { backgroundColor: theme.card },
        sceneStyle: { backgroundColor: theme.background },
      }}
    >
      <Tabs.Screen
        name="products"
        options={{
          title: "Produtos",
          tabBarIcon: ({ color }) => (
            <SymbolView
              name={{
                ios: "shippingbox",
                android: "inventory_2",
                web: "inventory_2",
              }}
              size={24}
              tintColor={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="camera"
        options={{
          title: "Câmera",
          tabBarIcon: ({ color }) => (
            <SymbolView
              name={{ ios: "camera", android: "camera_alt", web: "camera_alt" }}
              size={24}
              tintColor={color}
            />
          ),
        }}
      />
    </Tabs>
  );
}
