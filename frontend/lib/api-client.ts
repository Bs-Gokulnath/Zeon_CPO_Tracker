import axios, { type AxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
  paramsSerializer: (params) => {
    const qs = new URLSearchParams();
    for (const [key, val] of Object.entries(params)) {
      if (val == null || val === "") continue;
      if (Array.isArray(val)) {
        val.forEach((v) => qs.append(key, String(v)));
      } else {
        qs.append(key, String(val));
      }
    }
    return qs.toString();
  },
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
    ? Object.fromEntries(
        Object.entries(params).filter(([, v]) => {
          if (v == null || v === "") return false;
          if (Array.isArray(v) && v.length === 0) return false;
          return true;
        })
      )
    : undefined;
  const { data } = await apiClient.get<T>(path, { params: cleaned, ...config });
  return data;
}
