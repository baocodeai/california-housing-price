import React, { useState } from 'react';
import { X, Upload, FileCheck, Download, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';

export function BatchPredictModal({ isOpen, onClose, onBatchSuccess }) {
  const [file, setFile] = useState(null);
  const [parsedData, setParsedData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (!uploadedFile) return;

    setFile(uploadedFile);
    setError(null);
    setResults(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
        if (lines.length < 2) {
          setError('File CSV cần ít nhất 1 dòng tiêu đề và 1 dòng dữ liệu.');
          return;
        }

        const headers = lines[0].split(',').map((h) => h.trim().replace(/^["']|["']$/g, ''));
        const items = [];

        for (let i = 1; i < lines.length; i++) {
          const vals = lines[i].split(',').map((v) => v.trim().replace(/^["']|["']$/g, ''));
          if (vals.length < headers.length) continue;

          const rowObj = {};
          headers.forEach((h, idx) => {
            const val = vals[idx];
            if (h === 'ocean_proximity') {
              rowObj[h] = val;
            } else {
              rowObj[h] = parseFloat(val) || 0;
            }
          });
          items.push(rowObj);
        }

        setParsedData(items);
      } catch (err) {
        setError(`Lỗi đọc file: ${err.message}`);
      }
    };
    reader.readAsText(uploadedFile);
  };

  const handleRunBatch = async () => {
    if (parsedData.length === 0) return;
    setLoading(true);
    setError(null);

    try {
      const res = await api.predictBatch(parsedData.slice(0, 500));
      setResults(res.data);
      if (onBatchSuccess) onBatchSuccess();
    } catch (err) {
      setError(err.message || 'Lỗi xử lý dự đoán hàng loạt');
    } finally {
      setLoading(false);
    }
  };

  const downloadResultsCSV = () => {
    if (!results || !results.predictions) return;

    const merged = parsedData.map((item, idx) => {
      const pred = results.predictions[idx];
      return {
        ...item,
        predicted_price: pred ? pred.predicted_price : '',
      };
    });

    const headers = Object.keys(merged[0]);
    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [
        headers.join(','),
        ...merged.map((row) => headers.map((h) => row[h]).join(',')),
      ].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `california_housing_batch_results_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>⚡ VECTORIZED BATCH PREDICTION (CSV)</h3>
          <button className="btn-icon" onClick={onClose} title="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <p style={{ color: '#8892b0', fontSize: '0.9rem', marginBottom: '16px' }}>
            Tải lên file CSV chứa các cột dữ liệu nhà California (tối đa 500 dòng/lần) để chạy suy luận mô hình siêu tốc.
          </p>

          <div className="file-upload-box">
            <input type="file" accept=".csv" id="batch-file-input" onChange={handleFileUpload} />
            <label htmlFor="batch-file-input" className="upload-label">
              <Upload size={24} color="#66fcf1" />
              <span>{file ? file.name : 'Chọn hoặc kéo thả file CSV vào đây'}</span>
            </label>
          </div>

          {parsedData.length > 0 && (
            <div className="parsed-summary">
              <FileCheck size={16} color="#66fcf1" />
              <span>Đã nạp thành công <strong>{parsedData.length}</strong> căn nhà sẵn sàng dự đoán.</span>
            </div>
          )}

          {error && (
            <div className="error-alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {results && (
            <div className="batch-success-card">
              <h4>✅ Dự Đoán Hoàn Tất!</h4>
              <p>Tổng số căn nhà: <strong>{results.total_items}</strong></p>
              <p>Thời gian xử lý: <strong>{results.total_inference_latency_ms} ms</strong></p>
              <button className="btn-primary" onClick={downloadResultsCSV} style={{ marginTop: '12px' }}>
                <Download size={16} />
                <span>Tải Về File CSV Đã Dự Đoán</span>
              </button>
            </div>
          )}

          {!results && (
            <button
              className="btn-primary"
              onClick={handleRunBatch}
              disabled={loading || parsedData.length === 0}
              style={{ width: '100%', marginTop: '16px' }}
            >
              {loading ? 'ĐANG XỬ LÝ...' : `DỰ ĐOÁN HÀNG LOẠT (${parsedData.length} MẪU)`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
