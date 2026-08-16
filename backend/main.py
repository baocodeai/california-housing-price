"""
Điểm khởi chạy Backend cho môi trường phát triển (Development Entrypoint)
Tương thích với lệnh: uvicorn main:app hoặc uvicorn backend.main:app
"""
import uvicorn
from backend.app.main import app

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
