import React from 'react';
import { Sidebar } from '../layout/Sidebar';
import { ResultCard } from '../prediction/ResultCard';
import { MapPicker } from '../map/MapPicker';

export function ValuationStudio({
  features,
  onInputChange,
  onLocationChange,
  onPredict,
  prediction,
  latency,
  loading,
  caliGeoJSON,
}) {
  return (
    <div className="app-container">
      {/* Left Sidebar Form Controls */}
      <Sidebar
        features={features}
        onChange={onInputChange}
        onPredict={onPredict}
        loading={loading}
      />

      {/* Main Studio Area: Top is Prediction, Bottom is Map */}
      <main className="main-content">
        {/* Top: Prediction Result Valuation */}
        <section className="prediction-section">
          <ResultCard
            prediction={prediction}
            latency={latency}
            loading={loading}
            modelVersion="1.0.0"
          />
        </section>

        {/* Bottom: Interactive Geospatial Map Selection */}
        <section className="map-section">
          <MapPicker
            latitude={features.latitude}
            longitude={features.longitude}
            onLocationSelect={onLocationChange}
            caliGeoJSON={caliGeoJSON}
          />
        </section>
      </main>
    </div>
  );
}
