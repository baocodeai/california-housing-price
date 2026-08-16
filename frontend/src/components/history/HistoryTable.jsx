import React from 'react';
import { Database, Download } from 'lucide-react';

export function HistoryTable({ history }) {
  const exportToCSV = () => {
    if (!history || history.length === 0) return;

    const headers = [
      'ID',
      'Longitude',
      'Latitude',
      'Age',
      'Rooms',
      'Bedrooms',
      'Population',
      'Households',
      'Income',
      'Ocean Proximity',
      'Predicted Price',
      'Created At',
    ];

    const rows = history.map((item) => [
      item.id,
      item.longitude,
      item.latitude,
      item.housing_median_age,
      item.total_rooms,
      item.total_bedrooms,
      item.population,
      item.households,
      item.median_income,
      `"${item.ocean_proximity}"`,
      item.predicted_price,
      `"${item.created_at}"`,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `california_housing_history_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="history-card">
      <div className="history-header">
        <div className="panel-header">
          <Database size={16} />
          <span>PREDICTION AUDIT LOGS ({history.length} LATEST RECORDS)</span>
        </div>
        {history.length > 0 && (
          <button className="btn-export" onClick={exportToCSV} title="Download CSV ledger">
            <Download size={14} />
            <span>Export CSV</span>
          </button>
        )}
      </div>

      <div className="table-responsive">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Location (Lat, Lng)</th>
              <th>Age</th>
              <th>Rooms / Beds</th>
              <th>Pop / Households</th>
              <th>Income</th>
              <th>Ocean Proximity</th>
              <th>Valuation</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', color: '#8892b0', padding: '20px' }}>
                  No historical prediction records yet.
                </td>
              </tr>
            ) : (
              history.map((row) => (
                <tr key={row.id}>
                  <td>#{row.id}</td>
                  <td>
                    {row.latitude?.toFixed(2)}, {row.longitude?.toFixed(2)}
                  </td>
                  <td>{row.housing_median_age} yr</td>
                  <td>
                    {row.total_rooms} / {row.total_bedrooms}
                  </td>
                  <td>
                    {row.population} / {row.households}
                  </td>
                  <td>${((row.median_income || 0) * 10000).toLocaleString()}</td>
                  <td>
                    <span className="ocean-tag">{row.ocean_proximity}</span>
                  </td>
                  <td className="price-td">${row.predicted_price?.toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
