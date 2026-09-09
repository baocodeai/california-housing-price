import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://1modfu9v9k.execute-api.us-east-1.amazonaws.com';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  predict: async (features) => {
    const startTime = performance.now();
    // Chuyển dict features sang định dạng instances 2D mảng cho SageMaker
    const instance = [
      features.longitude,
      features.latitude,
      features.housing_median_age,
      features.total_rooms,
      features.total_bedrooms,
      features.population,
      features.households,
      features.median_income,
      features.ocean_proximity
    ];
    const res = await apiClient.post('/predict', { instances: [instance] });
    const endTime = performance.now();
    return {
      data: {
        predicted_price: res.data.predicted_value,
        prediction_id: res.data.prediction_id,
        inference_latency_ms: Math.round(endTime - startTime)
      }
    };
  },
  sendFeedback: (predictionId, actualPrice) =>
    apiClient.post('/feedback', { prediction_id: predictionId, actual_price: actualPrice }),
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
