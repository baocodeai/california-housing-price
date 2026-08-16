.PHONY: help install data train evaluate visualize test test-unit test-integration run-api docker-build docker-up clean

PYTHON := python
PIP := pip
PYTEST := pytest
UVICORN := uvicorn

help:
	@echo "Các lệnh điều khiển MLOps dự án California Housing:"
	@echo "  make install          Cài đặt package và các thư viện phụ thuộc"
	@echo "  make data             Chạy pipeline dữ liệu (ingest, clean, split)"
	@echo "  make train            Huấn luyện mô hình Stacking Regressor"
	@echo "  make evaluate         Tạo biểu đồ và báo cáo đánh giá mô hình"
	@echo "  make visualize        Tạo biểu đồ phân bố và bản đồ EDA"
	@echo "  make test             Chạy toàn bộ test suites"
	@echo "  make test-unit        Chạy các bài kiểm thử đơn vị (Unit Tests)"
	@echo "  make test-integration Chạy các bài kiểm thử tích hợp (Integration Tests)"
	@echo "  make run-api          Khởi chạy máy chủ FastAPI (cổng 8000)"
	@echo "  make docker-up        Khởi chạy toàn bộ hệ sinh thái Docker (API, UI, Prometheus, Grafana)"
	@echo "  make clean            Dọn dẹp cache và các file tạm"

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	$(PIP) install -e .

data:
	@echo "==> Đang chạy Pipeline Thu thập, Làm sạch và Chia dữ liệu..."
	$(PYTHON) src/data/ingestion.py
	$(PYTHON) src/data/cleaning.py
	$(PYTHON) src/data/splitting.py

train:
	@echo "==> Đang huấn luyện Pipeline Stacking Regressor..."
	$(PYTHON) -m src.models.stacking.train --config configs/stacking.yaml

evaluate:
	@echo "==> Đang sinh biểu đồ đánh giá mô hình..."
	$(PYTHON) src/visualization/evaluation.py

visualize:
	@echo "==> Đang sinh biểu đồ khám phá dữ liệu EDA..."
	$(PYTHON) src/visualization/exploration.py

test:
	@echo "==> Đang chạy toàn bộ Pytest Suites..."
	$(PYTEST) -v tests/

test-unit:
	@echo "==> Đang chạy Unit Tests..."
	$(PYTEST) -v tests/unit/

test-integration:
	@echo "==> Đang chạy Integration Tests..."
	$(PYTEST) -v tests/integration/

run-api:
	@echo "==> Đang khởi động FastAPI Development Server tại cổng 8000..."
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker compose build

docker-up:
	docker compose up -d

clean:
	@echo "==> Đang dọn dẹp các thư mục cache..."
	$(PYTHON) -c "import shutil, pathlib, glob; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]"
