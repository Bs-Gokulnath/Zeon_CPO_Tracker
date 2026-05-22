import axios, { type AxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const message = err.response?.data?.detail ?? err.message ?? "Unknown error";
    return Promise.reject(new Error(message));
  }
);

export async function apiFetch<T>(
  path: string,
  params?: Record<string, unknown>,
  config?: AxiosRequestConfig
): Promise<T> {
  const cleaned = params
    ? Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ""))
    : undefined;
  const { data } = await apiClient.get<T>(path, { params: cleaned, ...config });
  return data;
}
