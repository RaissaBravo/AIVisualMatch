const configuredUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
export const API_BASE_URL = (configuredUrl || "http://10.0.2.2:8000").replace(
  /\/$/,
  "",
);
export const API_TIMEOUT_MS = 10_000;
