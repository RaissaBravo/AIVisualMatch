import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ProductsProvider } from '@/src/context/ProductsContext';

export default function RootLayout() {
  return <ProductsProvider><StatusBar style="light" /><Stack screenOptions={{ headerShown: false }} /></ProductsProvider>;
}
