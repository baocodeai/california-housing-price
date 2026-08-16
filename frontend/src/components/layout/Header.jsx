import React from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  FileSpreadsheet,
  Home,
  LayoutDashboard,
  ExternalLink,
} from 'lucide-react';

export function Header({
  currentView,
  onChangeView,
  driftStatus,
  onOpenDriftModal,
  onOpenBatchModal,
}) {
  const hasDrift = driftStatus?.overall_drift_detected;

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="system-title">
          <h1>CALI_HOUSING</h1>
        </div>

        {/* View Switcher Tabs */}
        <nav className="nav-tabs-header">
          <button
            className={`nav-tab-btn ${currentView === 'user' ? 'active' : ''}`}
            onClick={() => onChangeView('user')}
          >
            <Home size={15} />
            <span>User Studio (Dự Đoán)</span>
          </button>

          <button
            className={`nav-tab-btn ${currentView === 'admin' ? 'active' : ''}`}
            onClick={() => onChangeView('admin')}
          >
            <LayoutDashboard size={15} />
            <span>Admin MLOps Dashboard</span>
          </button>
        </nav>
      </div>

      <div className="header-right">
        {/* Batch Prediction Button (available in user view) */}
        {currentView === 'user' && (
          <button
            className="btn-secondary"
            onClick={onOpenBatchModal}
            title="Upload CSV to predict multiple houses"
          >
            <FileSpreadsheet size={15} />
            <span>Batch Predict CSV</span>
          </button>
        )}

        {/* Drift Status Indicator */}
        <button
          className={`drift-indicator ${hasDrift ? 'drift-warning' : 'drift-healthy'}`}
          onClick={onOpenDriftModal}
          title="Click to view full Data Drift report"
        >
          {hasDrift ? (
            <>
              <AlertTriangle size={14} />
              <span>Drift Alert</span>
            </>
          ) : (
            <>
              <ShieldCheck size={14} />
              <span>Data Normal</span>
            </>
          )}
        </button>

        {/* Status indicator */}
        <div className="status-live">
          <span className="pulse-dot"></span>
          <span>API ACTIVE</span>
        </div>
      </div>
    </header>
  );
}
