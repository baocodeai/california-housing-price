import React from 'react';
import { Crosshair, Sliders } from 'lucide-react';

export function Sidebar({ features, onChange, onPredict, loading }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-section-title">
        <Sliders size={16} />
        <span>MODEL INPUT PARAMETERS</span>
      </div>

      <div className="controls">
        <div className="input-group">
          <label>
            Longitude <span>{features.longitude}</span>
          </label>
          <input
            type="range"
            name="longitude"
            min="-124.35"
            max="-114.31"
            step="0.01"
            value={features.longitude}
            onChange={onChange}
          />
          <input type="number" name="longitude" value={features.longitude} onChange={onChange} />
        </div>

        <div className="input-group">
          <label>
            Latitude <span>{features.latitude}</span>
          </label>
          <input
            type="range"
            name="latitude"
            min="32.54"
            max="41.95"
            step="0.01"
            value={features.latitude}
            onChange={onChange}
          />
          <input type="number" name="latitude" value={features.latitude} onChange={onChange} />
        </div>

        <div className="input-group">
          <label>Housing Median Age (Years)</label>
          <input
            type="number"
            name="housing_median_age"
            value={features.housing_median_age}
            onChange={onChange}
          />
        </div>

        <div className="input-group">
          <label>Total Rooms</label>
          <input type="number" name="total_rooms" value={features.total_rooms} onChange={onChange} />
        </div>

        <div className="input-group">
          <label>Total Bedrooms</label>
          <input
            type="number"
            name="total_bedrooms"
            value={features.total_bedrooms}
            onChange={onChange}
          />
        </div>

        <div className="input-group">
          <label>Population in Block</label>
          <input type="number" name="population" value={features.population} onChange={onChange} />
        </div>

        <div className="input-group">
          <label>Total Households</label>
          <input type="number" name="households" value={features.households} onChange={onChange} />
        </div>

        <div className="input-group">
          <label>Median Income ($10k)</label>
          <input
            type="number"
            name="median_income"
            step="0.0001"
            value={features.median_income}
            onChange={onChange}
          />
        </div>

        <div className="input-group">
          <label>Ocean Proximity</label>
          <select name="ocean_proximity" value={features.ocean_proximity} onChange={onChange}>
            <option value="<1H OCEAN">&lt;1H OCEAN</option>
            <option value="INLAND">INLAND</option>
            <option value="NEAR OCEAN">NEAR OCEAN</option>
            <option value="NEAR BAY">NEAR BAY</option>
            <option value="ISLAND">ISLAND</option>
          </select>
        </div>

        <button
          className="btn-primary"
          onClick={onPredict}
          disabled={loading}
          style={{ width: '100%', marginTop: '1rem' }}
        >
          <Crosshair size={18} />
          <span>{loading ? 'COMPUTING VALUATION...' : 'INITIATE PREDICTION'}</span>
        </button>
      </div>
    </aside>
  );
}
