import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis
} from 'recharts';
import { Crosshair, Database, Activity, Map as MapIcon } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip, useMapEvents, GeoJSON } from 'react-leaflet';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [features, setFeatures] = useState({
    longitude: -121.9,
    latitude: 37.66,
    housing_median_age: 18.0,
    total_rooms: 7397.0,
    total_bedrooms: 1137.0,
    population: 3126.0,
    households: 1115.0,
    median_income: 6.4994,
    ocean_proximity: 'INLAND'
  });

  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [scatterData, setScatterData] = useState([]);
  const [metricType, setMetricType] = useState('rmse');
  const [errorToast, setErrorToast] = useState(null);
  const [caliGeoJSON, setCaliGeoJSON] = useState(null);

  useEffect(() => {
    fetchHistory();
    fetchMetrics();
    fetchScatter();

    // Dynamically fetch accurate California polygon borders
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
      .then(res => res.json())
      .then(data => {
        const california = data.features.find(f => f.properties.name === 'California');
        if (california) setCaliGeoJSON(california);
      })
      .catch(e => console.error("GeoJSON Error: ", e));
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE}/history`);
      setHistory(res.data.history);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMetrics = async () => {
    try {
      const res = await axios.get(`${API_BASE}/metrics`);
      setMetrics(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchScatter = async () => {
    try {
      const res = await axios.get(`${API_BASE}/scatter-data`);
      setScatterData(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFeatures(prev => ({
      ...prev,
      [name]: name === 'ocean_proximity' ? value : parseFloat(value)
    }));
  };

  const handlePredict = async () => {
    // Front-end Pre-flight Validation Check
    const errors = [];
    if (features.longitude < -125.0 || features.longitude > -114.0) errors.push("- LONGITUDE: Range must be -125.0 to -114.0");
    if (features.latitude < 32.0 || features.latitude > 42.0) errors.push("- LATITUDE: Range must be 32.0 to 42.0");
    if (features.housing_median_age < 1.0 || features.housing_median_age > 100.0) errors.push("- AGE: Range must be 1.0 to 100.0");
    if (features.total_rooms < 1.0 || features.total_rooms > 50000.0) errors.push("- TOTAL ROOMS: Cannot exceed 50,000");
    if (features.total_bedrooms < 1.0 || features.total_bedrooms > 20000.0) errors.push("- TOTAL BEDROOMS: Cannot exceed 20,000");
    if (features.population < 1.0 || features.population > 50000.0) errors.push("- POPULATION: Cannot exceed 50,000");
    if (features.households < 1.0 || features.households > 20000.0) errors.push("- HOUSEHOLDS: Cannot exceed 20,000");
    if (features.median_income < 0.0 || features.median_income > 25.0) errors.push("- INCOME: Range must be 0 to 25.0");

    if (errors.length > 0) {
      setErrorToast("MISSION ABORTED - LIMITS EXCEEDED:\n\n" + errors.join('\n'));
      setTimeout(() => setErrorToast(null), 5000);
      return; // Stop function completely, do not hit backend
    }

    setLoading(true);
    setErrorToast(null);
    try {
      const res = await axios.post(`${API_BASE}/predict`, features);
      setPrediction(res.data.predicted_price);
      fetchHistory(); // refresh history
    } catch (e) {
      console.error(e);
      if (e.response && e.response.status === 422) {
        const issues = e.response.data.detail.map(err => `- ${err.loc[err.loc.length - 1].toUpperCase()}: ${err.msg}`).join('\n');
        setErrorToast(issues);
      } else {
        setErrorToast(`SERVER ERROR: ${e.response?.data?.detail || e.message}`);
      }
      setTimeout(() => setErrorToast(null), 8000);
    }
    setTimeout(() => setLoading(false), 800); // artificial delay for aesthetic effect
  };

  // Custom tooltips for brutalist theme
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', padding: '10px' }}>
          <p style={{ color: 'var(--text-main)', marginBottom: '5px' }}>{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color, margin: 0 }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const MapClickHandler = () => {
    useMapEvents({
      click(e) {
        const lat = parseFloat(e.latlng.lat.toFixed(4));
        const lng = parseFloat(e.latlng.lng.toFixed(4));

        if (lat < 32.0 || lat > 42.0 || lng < -125.0 || lng > -114.0) {
          setErrorToast("TARGET OUTSIDE CALIFORNIA PERIMETER\nPlease select a valid coordinate.");
          setTimeout(() => setErrorToast(null), 5000);
          return; // Stop marker movement completely
        }

        setFeatures(prev => ({
          ...prev,
          latitude: lat,
          longitude: lng
        }));
      }
    });
    return null;
  };

  return (
    <div className="app-container">
      {loading && <div className="scanner"></div>}

      {/* Error Toast Notification */}
      {errorToast && (
        <div className="error-toast">
          <div className="toast-header">ACCESS DENIED - SYSTEM ALERT</div>
          <pre>{errorToast}</pre>
        </div>
      )}

      {/* Sidebar Controls */}
      <aside className="sidebar">
        <div className="branding">
          <h1>CALI_HOUSING</h1>
          <p>PREDICTIVE TERM // v1.0.0 // STATUS: ONLINE</p>
        </div>

        <div className="controls">
          <div className="input-group">
            <label>Longitude <span>{features.longitude}</span></label>
            <input type="range" name="longitude" min="-124.35" max="-114.31" step="0.01" value={features.longitude} onChange={handleChange} />
            <input type="number" name="longitude" value={features.longitude} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Latitude <span>{features.latitude}</span></label>
            <input type="range" name="latitude" min="32.54" max="41.95" step="0.01" value={features.latitude} onChange={handleChange} />
            <input type="number" name="latitude" value={features.latitude} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Housing Median Age</label>
            <input type="number" name="housing_median_age" value={features.housing_median_age} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Total Rooms</label>
            <input type="number" name="total_rooms" value={features.total_rooms} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Total Bedrooms</label>
            <input type="number" name="total_bedrooms" value={features.total_bedrooms} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Population</label>
            <input type="number" name="population" value={features.population} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Households</label>
            <input type="number" name="households" value={features.households} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Median Income (10k)</label>
            <input type="number" name="median_income" step="0.0001" value={features.median_income} onChange={handleChange} />
          </div>

          <div className="input-group">
            <label>Ocean Proximity</label>
            <select name="ocean_proximity" value={features.ocean_proximity} onChange={handleChange}>
              <option value="<1H OCEAN">&lt;1H OCEAN</option>
              <option value="INLAND">INLAND</option>
              <option value="NEAR OCEAN">NEAR OCEAN</option>
              <option value="NEAR BAY">NEAR BAY</option>
              <option value="ISLAND">ISLAND</option>
            </select>
          </div>

          <button onClick={handlePredict} style={{ width: '100%', marginTop: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <Crosshair size={18} />
            INITIATE PREDICTION
          </button>
        </div>
      </aside>

      {/* Main Dashboard */}
      <main className="main-content">
        <section className="result-panel">
          {loading && <div className="predicting-overlay">ANALYZING...</div>}
          <div className="price-display">
            <span className="currency">$</span>
            {prediction ? prediction.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '---,---'}
          </div>
          <div className="price-label">ESTIMATED VALUATION</div>
        </section>

        <section className="dashboard">
          {/* Panel 3: Map Protocol */}
          <div className="panel" style={{ gridColumn: '1 / 2', gridRow: '1 / 3', display: 'flex', flexDirection: 'column' }}>
            <div className="panel-title">
              GEOGRAPHICAL DISTRIBUTION <MapIcon size={18} />
            </div>
            <div style={{ position: 'relative', width: '100%', flexGrow: 1, minHeight: '550px', zIndex: 0 }}>
              <MapContainer center={[36.77, -119.41]} zoom={6} scrollWheelZoom={false} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, right: 0, backgroundColor: 'var(--bg-primary)', cursor: 'crosshair' }}>
                <MapClickHandler />
                <TileLayer
                  attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                />

                {/* California Exact GeoJSON Border */}
                {caliGeoJSON && (
                  <GeoJSON
                    key="california-border"
                    data={caliGeoJSON}
                    style={{ color: 'var(--text-muted)', fillColor: 'transparent', weight: 2, dashArray: '4, 4' }}
                  />
                )}

                {history.map(row => (
                  <CircleMarker
                    key={`hist-${row.id}`}
                    center={[parseFloat(row.latitude), parseFloat(row.longitude)]}
                    radius={5}
                    pathOptions={{ color: 'transparent', fillColor: 'var(--text-muted)', fillOpacity: 0.5 }}
                  >
                    <LeafletTooltip direction="top" opacity={1}>
                      Price: ${parseFloat(row.predicted_price).toLocaleString()}
                    </LeafletTooltip>
                  </CircleMarker>
                ))}

                <CircleMarker
                  center={[features.latitude, features.longitude]}
                  radius={8}
                  pathOptions={{ color: 'var(--accent)', fillColor: 'var(--accent)', fillOpacity: 0.9, weight: 2 }}
                >
                  <LeafletTooltip direction="top" opacity={1} permanent={false}>
                    CURRENT TARGET
                  </LeafletTooltip>
                </CircleMarker>
              </MapContainer>
            </div>
          </div>

          {/* Panel 1: RMSE Comparison */}
          <div className="panel">
            <div className="panel-title">
              PERFORMANCE
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <select
                  value={metricType}
                  onChange={(e) => setMetricType(e.target.value)}
                  style={{ background: 'var(--bg-primary)', color: 'var(--accent)', border: '1px solid var(--border-color)', padding: '2px 5px', fontSize: '12px', fontFamily: 'var(--font-mono)', outline: 'none', cursor: 'pointer' }}
                >
                  <option value="rmse">RMSE</option>
                  <option value="mae">MAE</option>
                  <option value="r2">R² SCORE</option>
                </select>
                <Activity size={18} />
              </div>
            </div>
            <div style={{ width: '100%', height: 250 }}>
              <ResponsiveContainer>
                <BarChart data={metrics} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis dataKey="model" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} width={60} domain={metricType === 'r2' ? ['auto', 'auto'] : ['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend iconType="square" wrapperStyle={{ fontSize: '10px', color: 'var(--text-muted)' }} />
                  <Bar dataKey={`train_${metricType}`} fill="#64748b" name={`Train ${metricType.toUpperCase()}`} />
                  <Bar dataKey={`test_${metricType}`} fill="var(--accent)" name={`Test ${metricType.toUpperCase()}`} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Panel 2: Scatter Protocol */}
          <div className="panel">
            <div className="panel-title">
              ACTUAL VS PREDICTED (SAMPLE SET) <Crosshair size={18} />
            </div>
            <div style={{ width: '100%', height: 250 }}>
              <ResponsiveContainer>
                <ScatterChart margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis type="number" dataKey="actual" name="Actual Price" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                  <YAxis type="number" dataKey="predicted" name="Predicted" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} width={60} domain={['auto', 'auto']} />
                  <ZAxis type="number" range={[20, 20]} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
                  <Scatter name="Houses" data={scatterData} fill="var(--accent)" shape="square" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Panel 4: History Ledger */}
          <div className="panel" style={{ gridColumn: '1 / -1' }}>
            <div className="panel-title">
              PREDICTION LEDGER <Database size={18} />
            </div>
            <div style={{ overflowX: 'auto', maxHeight: '250px', overflowY: 'auto' }}>
              <table className="history-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>TIME</th>
                    <th>LOC (Lon, Lat)</th>
                    <th>AGE</th>
                    <th>ROOMS</th>
                    <th>BEDS</th>
                    <th>POP</th>
                    <th>HH</th>
                    <th>INCOME</th>
                    <th>PROXIMITY</th>
                    <th style={{ color: 'var(--accent)', textAlign: 'right' }}>VALUATION</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(row => (
                    <tr key={row.id}>
                      <td>#{row.id.toString().padStart(4, '0')}</td>
                      <td>{new Date(row.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                      <td>[{parseFloat(row.longitude).toFixed(2)}, {parseFloat(row.latitude).toFixed(2)}]</td>
                      <td>{parseFloat(row.housing_median_age).toFixed(1)}</td>
                      <td>{parseFloat(row.total_rooms).toFixed(0)}</td>
                      <td>{parseFloat(row.total_bedrooms).toFixed(0)}</td>
                      <td>{parseFloat(row.population).toFixed(0)}</td>
                      <td>{parseFloat(row.households).toFixed(0)}</td>
                      <td>{parseFloat(row.median_income).toFixed(4)}</td>
                      <td>{row.ocean_proximity}</td>
                      <td style={{ textAlign: 'right', color: 'var(--text-main)' }}>
                        ${parseFloat(row.predicted_price).toLocaleString('en-US', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                  {history.length === 0 && (
                    <tr>
                      <td colSpan="11" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        NO PREVIOUS DATA FOUND
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </section>
      </main>
    </div>
  );
}

export default App;
