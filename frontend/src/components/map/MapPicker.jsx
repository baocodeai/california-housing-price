import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, useMapEvents, useMap, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, AlertTriangle } from 'lucide-react';

function MapRecenter({ lat, lng }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lng], map.getZoom(), { duration: 0.8 });
  }, [lat, lng, map]);
  return null;
}

export function MapPicker({ latitude, longitude, onLocationSelect, caliGeoJSON }) {
  const [toastMessage, setToastMessage] = useState(null);

  function showInAppToast(msg) {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  }

  function MapEvents() {
    useMapEvents({
      click(e) {
        const lat = parseFloat(e.latlng.lat.toFixed(4));
        const lng = parseFloat(e.latlng.lng.toFixed(4));

        // California perimeter bounds check
        if (lat < 32.0 || lat > 42.0 || lng < -125.0 || lng > -114.0) {
          showInAppToast(
            `VỊ TRÍ NGOÀI RANH GIỚI CALIFORNIA (Tọa độ: ${lat}, ${lng}). Vui lòng chọn trong phạm vi Vĩ độ [32.0 - 42.0], Kinh độ [-125.0 - -114.0]!`
          );
          return;
        }

        onLocationSelect(lat, lng);
      },
    });
    return null;
  }

  return (
    <div className="map-wrapper">
      {/* In-app Toast Alert Notification */}
      {toastMessage && (
        <div className="in-app-toast">
          <div className="toast-header">
            <AlertTriangle size={16} color="#ff4a4a" />
            <span>CẢNH BÁO TỌA ĐỘ NGOÀI PHẠM VI</span>
          </div>
          <p className="toast-body">{toastMessage}</p>
        </div>
      )}

      <div className="panel-header">
        <MapPin size={16} />
        <span>GEOSPATIAL SELECTION (CLICK MAP TO SET LOCATION)</span>
      </div>

      <div className="map-view-container">
        <MapContainer
          center={[37.0, -119.5]}
          zoom={6.2}
          minZoom={5.5}
          maxZoom={12}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            noWrap={true}
            tileSize={256}
          />
          {caliGeoJSON && (
            <GeoJSON
              data={caliGeoJSON}
              style={{
                color: '#ff4500',
                weight: 2,
                fillColor: '#ff4500',
                fillOpacity: 0.08,
              }}
            />
          )}
          <MapEvents />
          <MapRecenter lat={latitude} lng={longitude} />
          <CircleMarker
            center={[latitude, longitude]}
            radius={10}
            pathOptions={{
              color: '#ffffff',
              fillColor: '#ff4500',
              fillOpacity: 0.95,
              weight: 3,
            }}
          />
        </MapContainer>
      </div>
    </div>
  );
}
