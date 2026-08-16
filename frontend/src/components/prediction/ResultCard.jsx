import React from 'react';
import { DollarSign, Clock, CheckCircle } from 'lucide-react';

export function ResultCard({ prediction, latency, loading, modelVersion = '1.0.0' }) {
  return (
    <div className="result-card">
      <div className="result-header">
        <span>PREDICTED MEDIAN VALUATION</span>
        {latency && (
          <span className="latency-tag">
            <Clock size={13} /> {latency}ms inference
          </span>
        )}
      </div>

      <div className="price-display-wrapper">
        <span className="currency-symbol">$</span>
        <span className="price-value">
          {loading
            ? 'CALCULATING...'
            : prediction !== null
            ? prediction.toLocaleString('en-US', { maximumFractionDigits: 0 })
            : '---,---'}
        </span>
      </div>

      <div className="result-footer">
        <div className="model-meta">
          <CheckCircle size={14} color="#66fcf1" />
          <span>Serving Model: Stacking Pipeline (v{modelVersion})</span>
        </div>
      </div>
    </div>
  );
}
