import React, { useState } from 'react';
import {
  Activity,
  Database,
  Cpu,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Download,
  ExternalLink,
  Layers,
  CheckCircle2,
  TrendingUp,
  Server,
} from 'lucide-react';
import { ModelComparisonChart } from '../charts/ModelComparisonChart';
import { ScatterActualPredChart } from '../charts/ScatterActualPredChart';
import { HistoryTable } from '../history/HistoryTable';
import { api } from '../../api/client';

export function AdminDashboard({
  history,
  metrics,
  scatterData,
  driftStatus,
  onRefresh,
}) {
  const [activeTab, setActiveTab] = useState('overview');
  const [runningDrift, setRunningDrift] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const hasDrift = driftStatus?.overall_drift_detected;
  const totalRequests = history.length;
  const avgPrice =
    totalRequests > 0
      ? history.reduce((acc, curr) => acc + (curr.predicted_price || 0), 0) /
        totalRequests
      : 0;

  const handleManualDriftCheck = async () => {
    setRunningDrift(true);
    try {
      await onRefresh();
    } finally {
      setTimeout(() => setRunningDrift(false), 600);
    }
  };

  // Filter history by search term
  const filteredHistory = history.filter((item) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.ocean_proximity?.toLowerCase().includes(term) ||
      String(item.id).includes(term) ||
      String(item.predicted_price).includes(term)
    );
  });

  return (
    <div className="admin-dashboard-container">
      {/* Admin Subheader Navigation */}
      <div className="admin-subheader">
        <div className="admin-title-box">
          <Server size={20} color="#66fcf1" />
          <div>
            <h2>MLOps & Production Admin Portal</h2>
            <p>California Housing Serving Cluster // Environment: Production</p>
          </div>
        </div>

        <div className="admin-actions">
          <button
            className="btn-secondary"
            onClick={handleManualDriftCheck}
            disabled={runningDrift}
            title="Refresh logs & run drift analysis"
          >
            <RefreshCw size={14} className={runningDrift ? 'spin' : ''} />
            <span>{runningDrift ? 'Analyzing...' : 'Refresh Metrics'}</span>
          </button>

          <a
            href="http://localhost:3001/d/california-housing-mlops"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
            title="Open Grafana Real-time Observability"
          >
            <ExternalLink size={14} />
            <span>Grafana Dashboard</span>
          </a>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
            title="Open Swagger API documentation"
          >
            <ExternalLink size={14} />
            <span>API Docs (Swagger)</span>
          </a>
        </div>
      </div>

      {/* KPI Top Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span>TOTAL PREDICTION REQUESTS</span>
            <Database size={16} color="#66fcf1" />
          </div>
          <div className="kpi-value">{totalRequests.toLocaleString()}</div>
          <div className="kpi-footer text-muted">Logged in history database</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>AVG PREDICTED VALUATION</span>
            <TrendingUp size={16} color="#66fcf1" />
          </div>
          <div className="kpi-value">
            ${avgPrice > 0 ? avgPrice.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '---'}
          </div>
          <div className="kpi-footer text-muted">Across all user requests</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>MODEL QUALITY (R² SCORE)</span>
            <CheckCircle2 size={16} color="#81c995" />
          </div>
          <div className="kpi-value" style={{ color: '#81c995' }}>0.8196</div>
          <div className="kpi-footer text-muted">Test Holdout Benchmark</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span>DATA DRIFT STATUS (KS-TEST)</span>
            {hasDrift ? (
              <AlertTriangle size={16} color="#f28b82" />
            ) : (
              <ShieldCheck size={16} color="#81c995" />
            )}
          </div>
          <div className="kpi-value" style={{ color: hasDrift ? '#f28b82' : '#81c995' }}>
            {hasDrift ? 'DRIFT DETECTED' : 'HEALTHY (NO DRIFT)'}
          </div>
          <div className="kpi-footer text-muted">
            {driftStatus?.drifted_features_count || 0} / {driftStatus?.total_features_tested || 8} features drifted
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="admin-tabs">
        <button
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Layers size={15} />
          <span>System & Analytics Overview</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'drift' ? 'active' : ''}`}
          onClick={() => setActiveTab('drift')}
        >
          <Activity size={15} />
          <span>Statistical Data Drift Monitor</span>
        </button>
        <button
          className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <Database size={15} />
          <span>Prediction Audit Ledger ({totalRequests})</span>
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="admin-content-section">
          {/* Model Registry Card */}
          <div className="admin-card model-registry-box">
            <div className="panel-header">
              <Cpu size={16} />
              <span>ACTIVE MODEL REGISTRY SPECIFICATION</span>
            </div>
            <div className="meta-grid">
              <div className="meta-item">
                <span className="meta-label">Model Architecture:</span>
                <span className="meta-value">Stacking Regressor (RF + SVR + Ridge)</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Artifact Version:</span>
                <span className="meta-value">v1.0.0 (Production Stage)</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Holdout Test RMSE:</span>
                <span className="meta-value">$48,619.66</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Holdout Test MAE:</span>
                <span className="meta-value">$30,305.92</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Mean Absolute % Error (MAPE):</span>
                <span className="meta-value">15.95%</span>
              </div>
              <div className="meta-item">
                <span className="meta-label">Inference Engine:</span>
                <span className="meta-value">FastAPI + Gunicorn / Non-root Container</span>
              </div>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="charts-grid" style={{ marginTop: '1.5rem' }}>
            <ModelComparisonChart data={metrics} />
            <ScatterActualPredChart data={scatterData} />
          </div>
        </div>
      )}

      {/* Tab 2: Data Drift */}
      {activeTab === 'drift' && (
        <div className="admin-content-section">
          <div className="admin-card">
            <div className="panel-header">
              <Activity size={16} />
              <span>KOLMOGOROV-SMIRNOV (KS) TWO-SAMPLE DRIFT ANALYSIS</span>
            </div>
            <p style={{ color: '#8892b0', fontSize: '0.85rem', marginBottom: '1.2rem' }}>
              Kiểm định sự khác biệt phân phối xác suất giữa tập dữ liệu huấn luyện cơ sở (Reference Baseline - 20,640 mẫu) và các yêu cầu người dùng gửi lên môi trường Production (Current Stream).
            </p>

            {driftStatus?.feature_metrics && driftStatus.feature_metrics.length > 0 ? (
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>Feature Name</th>
                      <th>Reference Baseline Mean</th>
                      <th>Production Stream Mean</th>
                      <th>KS Statistic</th>
                      <th>P-Value</th>
                      <th>Drift Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {driftStatus.feature_metrics.map((item) => (
                      <tr key={item.feature}>
                        <td><strong>{item.feature}</strong></td>
                        <td>{item.ref_mean}</td>
                        <td>{item.current_mean}</td>
                        <td>{item.ks_statistic}</td>
                        <td>{item.p_value}</td>
                        <td>
                          {item.drift_detected ? (
                            <span className="badge-drift-yes">YES (DRIFT)</span>
                          ) : (
                            <span className="badge-drift-no">NO (STABLE)</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '30px', color: '#8892b0' }}>
                <p>Chưa có đủ dữ liệu dự đoán để tính toán Data Drift (Cần ít nhất 5 bản ghi trong lịch sử).</p>
                <p>Hãy thực hiện một vài dự đoán trên trang User Studio để xem bảng thống kê.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Prediction Audit Logs */}
      {activeTab === 'logs' && (
        <div className="admin-content-section">
          <div className="admin-card">
            <div className="search-bar-wrapper">
              <input
                type="text"
                placeholder="🔍 Tìm kiếm theo Ocean Proximity, ID, hoặc Giá dự đoán..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="admin-search-input"
              />
            </div>
            <HistoryTable history={filteredHistory} />
          </div>
        </div>
      )}
    </div>
  );
}
