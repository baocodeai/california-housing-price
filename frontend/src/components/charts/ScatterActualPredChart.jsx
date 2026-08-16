import React from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Activity } from 'lucide-react';

export function ScatterActualPredChart({ data }) {
  const CustomScatterTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p>Actual: ${dataPoint.actual?.toLocaleString()}</p>
          <p style={{ color: '#ff4500' }}>Predicted: ${dataPoint.predicted?.toLocaleString()}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-card">
      <div className="panel-header">
        <Activity size={16} />
        <span>ACTUAL VS PREDICTED VALUATION (HOLDOUT SAMPLE)</span>
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis
              dataKey="actual"
              type="number"
              name="Actual Price"
              unit="$"
              stroke="#888"
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              dataKey="predicted"
              type="number"
              name="Predicted Price"
              unit="$"
              stroke="#888"
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip content={<CustomScatterTooltip />} />
            <Scatter name="Test Samples" data={data} fill="#ff4500" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
