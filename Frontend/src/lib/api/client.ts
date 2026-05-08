import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for auth tokens
apiClient.interceptors.request.use(
  (config) => {
    console.log("[apiClient] Request", {
      method: config.method,
      url: `${config.baseURL ?? ""}${config.url ?? ""}`,
    });
    const token = localStorage.getItem("wardrobewiz-auth-token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log("[apiClient] Response", {
      status: response.status,
      url: `${response.config.baseURL ?? ""}${response.config.url ?? ""}`,
    });
    return response;
  },
  (error) => {
    console.error("[apiClient] Response error", {
      status: error.response?.status,
      url: `${error.config?.baseURL ?? ""}${error.config?.url ?? ""}`,
      message: error.message,
    });
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem("wardrobewiz-auth-token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;

