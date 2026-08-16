import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { BarChart3 } from 'lucide-react';

export function ModelComparisonChart({ data }) {
  const [metric, setMetric] = useState('rmse');

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p style={{ color: '#888', marginBottom: '4px' }}>{label}</p>
          <p style={{ color: '#ff4500', fontWeight: 'bold' }}>
            {metric.toUpperCase()}:{' '}
            {typeof payload[0].value === 'number'
              ? payload[0].value.toLocaleString(undefined, { maximumFractionDigits: 2 })
              : payload[0].value}
          </p>
        </div>
      );
    }
    return null;
  };

  const metricKey = `Test_${metric.toUpperCase()}`;

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div className="panel-header">
          <BarChart3 size={16} />
          <span>MODEL BENCHMARK COMPARISON</span>
        </div>
        <div className="metric-toggle-group">
          {['rmse', 'mae', 'r2'].map((m) => (
            <button
              key={m}
              className={`toggle-btn ${metric === m ? 'active' : ''}`}
              onClick={() => setMetric(m)}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis dataKey="Model" stroke="#888" angle={-15} textAnchor="end" height={45} tick={{ fontSize: 12 }} />
            <YAxis stroke="#888" tick={{ fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey={metricKey} fill="#ff4500" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
