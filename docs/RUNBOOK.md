# Production Runbook & Incident Response Guide

Tài liệu hướng dẫn vận hành, giám sát và xử lý sự cố cho hệ thống **California Housing Price Prediction Serving**.

---

## 1. Kiến Trúc & Cổng Dịch Vụ

| Dịch Vụ | Container Name | Port Mặc Định | URL Kiểm Tra |
| :--- | :--- | :--- | :--- |
| **FastAPI Serving API** | `california-housing-api` | `8000` | `http://localhost:8000/health` |
| **Frontend React/Nginx** | `california-housing-frontend` | `80` | `http://localhost:80` |
| **Prometheus Scraper** | `california-housing-prometheus` | `9090` | `http://localhost:9090/targets` |
| **Grafana Monitoring** | `california-housing-grafana` | `3001` | `http://localhost:3001` |

---

## 2. Quy Trình Vận Hành Thường Nhật

### 2.1. Kiểm Tra Sức Khỏe Toàn Bộ Cụm Container
```bash
docker-compose ps
```
Tất cả các container phải ở trạng thái `Up (healthy)`.

### 2.2. Theo Dõi Logs Trực Tiếp (Structured JSON)
```bash
# Xem log API
docker logs -f california-housing-api

# Xem log Nginx Frontend
docker logs -f california-housing-frontend
```

### 2.3. Chạy Kiểm Tra Data Drift Thủ Công
```bash
python -m src.monitoring.drift_worker --min-samples 10
```
Báo cáo kết quả sẽ được ghi vào thư mục `data/drift_reports/drift_report_YYYYMMDD_HHMMSS.json`.

---

## 3. Cẩm Nang Xử Lý Sự Cố (Incident Response Playbook)

### Kịch Bản 1: API Trả Về Lỗi HTTP 500 Spike (Error Rate > 2%)
**Dấu hiệu:** Grafana hiển thị cảnh báo đỏ trên panel *HTTP 5xx Error Rate*.
**Nguyên nhân có thể:** Model artifact bị lỗi khi load, hoặc SQLite bị lock đồng thời, hoặc lỗi dữ liệu ngoài khoảng dự kiến.
**Các bước xử lý:**
1. Kiểm tra log chi tiết:
   ```bash
   docker logs --tail 100 california-housing-api | grep '"level": "ERROR"'
   ```
2. Kiểm tra endpoint `/health`:
   ```bash
   curl -s http://localhost:8000/health | jq
   ```
3. Nếu model không load được (`model_loaded: false`), khởi động lại container:
   ```bash
   docker-compose restart api
   ```

---

### Kịch Bản 2: Độ Trễ Cao Bất Thường (P95 Latency > 200ms)
**Dấu hiệu:** Panel *API Latency (P50, P95, P99)* trên Grafana tăng vọt.
**Nguyên nhân có thể:** CPU bị nghẽn do nhiều request batch lớn, hoặc thiếu worker threads.
**Các bước xử lý:**
1. Kiểm tra tải CPU/RAM trên máy chủ:
   ```bash
   docker stats california-housing-api
   ```
2. Nếu CPU > 80%, tăng số lượng Gunicorn workers trong `backend/Dockerfile` (`-w 4` $\rightarrow$ `-w 8`) hoặc tăng replica pod trên Kubernetes:
   ```bash
   kubectl scale deployment california-housing-api --replicas=4
   ```

---

### Kịch Bản 3: Cảnh Báo Phát Hiện Sai Lệch Dữ Liệu (Data Drift Alert)
**Dấu hiệu:** Worker `drift_worker.py` log cảnh báo `🚨 ALERT: Data Drift detected`.
**Nguyên nhân:** Dữ liệu phân phối thực tế của khách hàng (ví dụ `median_income` hoặc vùng `latitude/longitude`) đã thay đổi đáng kể so với dữ liệu huấn luyện ban đầu ($p$-value $< 0.05$ hoặc $\text{PSI} \ge 0.2$).
**Các bước xử lý:**
1. Xem báo cáo trực quan tại `http://localhost:8000/api/v1/drift-report`.
2. Xác định các trường bị drift nặng nhất (ví dụ `median_income`).
3. Kích hoạt pipeline huấn luyện lại tự động:
   ```bash
   python -m src.models.train
   ```
4. Đánh giá mô hình mới trên tập holdout. Nếu chỉ số $R^2$ cải thiện, tiến hành reload model:
   ```bash
   docker-compose restart api
   ```

---

### Kịch Bản 4: Rollback Model Về Phiên Bản Trước
Nếu mô hình mới sau khi cập nhật cho kết quả bất thường:
1. Sao chép lại artifact model backup:
   ```bash
   cp models/backup/stacking_pipeline_v1.0.0.joblib models/stacking_pipeline.joblib
   ```
2. Khởi động lại API server:
   ```bash
   docker-compose restart api
   ```
3. Chạy test xác nhận:
   ```bash
   pytest -v tests/
   ```

---

## 4. Tài Liệu API & Mẫu Dữ Liệu (API Documentation)

### 4.1. Swagger UI & Redoc Interactive Docs
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4.2. Mẫu Gọi API Dự Đoán (cURL Example)

```bash
curl -X POST "http://localhost:8000/api/v1/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "longitude": -122.23,
       "latitude": 37.88,
       "housing_median_age": 41.0,
       "total_rooms": 880.0,
       "total_bedrooms": 129.0,
       "population": 322.0,
       "households": 126.0,
       "median_income": 8.3252,
       "ocean_proximity": "NEAR BAY"
     }'
```

**Response mẫu (200 OK):**
```json
{
  "status": "success",
  "predicted_price": 452600.0,
  "formatted_price": "$452,600.00",
  "model_version": "1.0.0",
  "inference_latency_ms": 14.25,
  "timestamp": "2026-08-14T11:20:00.123456Z"
}
```

---

## 5. Danh Mục Kiểm Tra Khi Triển Khai (Production Checklist)

- [x] Model Artifact được lưu trữ tại `models/stacking_pipeline.joblib` và pre-warmed thành công.
- [x] Pydantic v2 schemas bắt chặt chẽ mọi input không hợp lệ (trả về 422 Unprocessable Entity).
- [x] Health Probes (`/health`, `/live`, `/ready`) phản hồi đúng chuẩn Kubernetes.
- [x] Prometheus Metrics exporter (`/prometheus-metrics`) cào dữ liệu ổn định.
- [x] Grafana Dashboard tự động nạp cấu hình và hiển thị đúng thông số.
- [x] Data Drift service (`drift_worker.py`) tính toán KS-test và PSI chuẩn xác.
- [x] Toàn bộ 11 bài kiểm thử tự động `pytest -v` vượt qua 100%.
