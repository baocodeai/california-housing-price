import React from 'react';
import { X, ExternalLink } from 'lucide-react';
import { api } from '../../api/client';

export function DriftModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const reportUrl = api.getDriftReportUrl();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>📊 STATISTICAL DATA DRIFT MONITOR</h3>
          <div className="modal-actions">
            <a
              href={reportUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-icon"
              title="Open full page in new tab"
            >
              <ExternalLink size={16} />
            </a>
            <button className="btn-icon" onClick={onClose} title="Close modal">
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          <iframe
            src={reportUrl}
            title="Drift Report"
            style={{ width: '100%', height: '550px', border: 'none', borderRadius: '4px' }}
          />
        </div>
      </div>
    </div>
  );
}
