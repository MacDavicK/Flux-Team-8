import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: log method + URL in dev mode
apiClient.interceptors.request.use((config) => {
  if (import.meta.env.DEV) {
    (config as Record<string, unknown>)._startTime = Date.now();
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
  }
  return config;
});

// Response interceptor: log status + timing in dev mode
apiClient.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      const start = (response.config as Record<string, unknown>)._startTime as number | undefined;
      const duration = start ? `${Date.now() - start}ms` : 'unknown';
      console.log(`[API] ${response.status} ${response.config.url} (${duration})`);
    }
    return response;
  },
  (error) => {
    if (import.meta.env.DEV) {
      const status = error.response?.status ?? 'NETWORK_ERROR';
      const url = error.config?.url ?? 'unknown';
      console.error(`[API] ${status} ${url}`, error.message);
    }

    // Standardize error format
    const standardized = {
      status: error.response?.status ?? 0,
      message: error.response?.data?.detail ?? error.message ?? 'Unknown error',
      url: error.config?.url ?? 'unknown',
    };

    return Promise.reject(standardized);
  },
);

export default apiClient;
