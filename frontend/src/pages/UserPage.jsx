import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, MapPinCheck, Sparkles } from 'lucide-react';
import { api } from '../api/client';
import { Sidebar } from '../components/layout/Sidebar';
import { ResultCard } from '../components/prediction/ResultCard';
import { MapPicker } from '../components/map/MapPicker';
import { BatchPredictModal } from '../components/prediction/BatchPredictModal';

export function UserPage() {
  const [features, setFeatures] = useState({
    longitude: -121.9,
    latitude: 37.66,
    housing_median_age: 18.0,
    total_rooms: 7397.0,
    total_bedrooms: 1137.0,
    population: 3126.0,
    households: 1115.0,
    median_income: 6.4994,
    ocean_proximity: 'INLAND',
  });

  const [prediction, setPrediction] = useState(null);
  const [latency, setLatency] = useState(null);
  const [loading, setLoading] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [enrichInfo, setEnrichInfo] = useState(null);
  const [caliGeoJSON, setCaliGeoJSON] = useState(null);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);

  useEffect(() => {
    // Fetch California GeoJSON borders
    fetch('https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json')
      .then((res) => res.json())
      .then((data) => {
        const california = data.features?.find((f) => f.properties.name === 'California');
        if (california) setCaliGeoJSON(california);
      })
      .catch((err) => console.error('GeoJSON fetch error:', err));
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFeatures((prev) => ({
      ...prev,
      [name]: name === 'ocean_proximity' ? value : parseFloat(value) || 0,
    }));
  };

  // Geospatial Auto-Enrichment when Map location changes
  const handleLocationChange = async (lat, lng) => {
    setEnriching(true);
    try {
      // 1. Lookup actual census demographics from nearest neighborhood
      const enrichRes = await api.lookupLocation(lat, lng);
      if (enrichRes.data?.features) {
        const enriched = enrichRes.data.features;
        const newFeatures = {
          latitude: lat,
          longitude: lng,
          housing_median_age: enriched.housing_median_age,
          total_rooms: enriched.total_rooms,
          total_bedrooms: enriched.total_bedrooms,
          population: enriched.population,
          households: enriched.households,
          median_income: enriched.median_income,
          ocean_proximity: enriched.ocean_proximity,
        };

        setFeatures(newFeatures);
        setEnrichInfo(`Tự động điền dữ liệu khu dân cư (${enriched.ocean_proximity} - Cách điểm đo ${enriched.lookup_distance_km}km)`);

        // 2. Instant auto-prediction for seamless real-time valuation experience
        setLoading(true);
        const predRes = await api.predict(newFeatures);
        setPrediction(predRes.data.predicted_price);
        setLatency(predRes.data.inference_latency_ms);
      }
    } catch (err) {
      console.error('Enrichment lookup failed:', err);
      // Fallback: just update lat/lng
      setFeatures((prev) => ({ ...prev, latitude: lat, longitude: lng }));
    } finally {
      setEnriching(false);
      setLoading(false);
    }
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const res = await api.predict(features);
      setPrediction(res.data.predicted_price);
      setLatency(res.data.inference_latency_ms);
    } catch (err) {
      alert(`Lỗi dự đoán: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-wrapper">
      {/* User Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="system-title">
            <h1>CALI_HOUSING</h1>
            <span className="version-tag">AI VALUATION STUDIO</span>
          </div>
        </div>

        <div className="header-right">
          {enrichInfo && (
            <div className="enrichment-badge">
              <MapPinCheck size={14} color="#00ff66" />
              <span>{enrichInfo}</span>
            </div>
          )}

          <button
            className="btn-secondary"
            onClick={() => setIsBatchModalOpen(true)}
            title="Upload CSV to predict multiple houses"
          >
            <FileSpreadsheet size={15} />
            <span>Batch Predict CSV</span>
          </button>

          <div className="status-live">
            <span className="pulse-dot"></span>
            <span>SYSTEM ONLINE</span>
          </div>
        </div>
      </header>

      {/* User Studio Body */}
      <div className="app-container">
        {/* Left Sidebar Input Form */}
        <Sidebar
          features={features}
          onChange={handleInputChange}
          onPredict={handlePredict}
          loading={loading || enriching}
        />

        {/* Main Content: Top is Result, Bottom is Expanded Map */}
        <main className="main-content">
          <section className="prediction-section">
            <ResultCard
              prediction={prediction}
              latency={latency}
              loading={loading || enriching}
              modelVersion="1.0.0"
            />
          </section>

          <section className="map-section">
            <MapPicker
              latitude={features.latitude}
              longitude={features.longitude}
              onLocationSelect={handleLocationChange}
              caliGeoJSON={caliGeoJSON}
            />
          </section>
        </main>
      </div>

      {/* Batch Predict CSV Modal */}
      <BatchPredictModal
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
      />
    </div>
  );
}
