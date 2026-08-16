import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  predict: (features) => apiClient.post('/predict', features),
  predictBatch: (items) => apiClient.post('/predict-batch', { items }),
  lookupLocation: (latitude, longitude) =>
    apiClient.get(`/enrichment/lookup?latitude=${latitude}&longitude=${longitude}`),
  getHistory: (limit = 50) => apiClient.get(`/history?limit=${limit}`),
  getMetrics: () => apiClient.get('/metrics'),
  getScatterData: (sampleSize = 100) => apiClient.get(`/scatter-data?sample_size=${sampleSize}`),
  getDriftStatus: () => apiClient.get('/drift-status'),
  getDriftReportUrl: () => `${API_BASE_URL}/drift-report`,
  getHealth: () => apiClient.get('/health'),
};
