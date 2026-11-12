import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { getFields, getFieldHealth, getFieldTimeSeries } from '../api/client';
import {
  getFarmerAnalysisHistory,
  saveAnalysisHistoryRecord,
  deleteAnalysisHistoryRecord,
  clearFarmerAnalysisHistory,
  getCurrentFarmerName,
  formatAnalysisDate,
} from '../services/fieldHealthHistory';

/**
 * FieldHealth Component
 * Displays live field health status, vegetation indices (NDVI, NDRE, GNDVI),
 * and Sentinel-2 satellite time-series observations from the FastAPI backend.
 * Uses the standard color scheme:
 * Green = Healthy
 * Amber = Needs Attention
 * Red = High Risk
 */
const FieldHealth = () => {
  const [fields, setFields] = useState([]);
  const [selectedFieldId, setSelectedFieldId] = useState('');
  const [healthData, setHealthData] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fieldsLoading, setFieldsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeMetric, setActiveMetric] = useState('all'); // 'all', 'ndvi', 'ndre', 'gndvi'

  // Persistent Client-Side History State (IndexedDB)
  const [historyList, setHistoryList] = useState([]);
  const [isHistoricalSnapshot, setIsHistoricalSnapshot] = useState(false);
  const [snapshotDate, setSnapshotDate] = useState('');
  const [farmerName, setFarmerName] = useState(() => getCurrentFarmerName());

  const loadHistory = useCallback(async () => {
    try {
      const records = await getFarmerAnalysisHistory();
      setHistoryList(records || []);
      setFarmerName(getCurrentFarmerName());
    } catch (e) {
      console.warn('Failed to load farmer analysis history in React:', e);
    }
  }, []);

  useEffect(() => {
    loadHistory();

    const handleAuthEvent = () => loadHistory();
    window.addEventListener('auth:login', handleAuthEvent);
    window.addEventListener('auth:logout', () => {
      setHistoryList([]);
      setIsHistoricalSnapshot(false);
    });

    return () => {
      window.removeEventListener('auth:login', handleAuthEvent);
    };
  }, [loadHistory]);

  // Fetch field catalog on mount
  useEffect(() => {
    let isMounted = true;
    setFieldsLoading(true);

    getFields(0, 100)
      .then((res) => {
        if (!isMounted) return;
        const fieldList = res.fields || [];
        setFields(fieldList);
        if (fieldList.length > 0) {
          setSelectedFieldId(fieldList[0].field_id);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Error fetching field catalog:', err);
        setError('Failed to connect to field catalog service.');
      })
      .finally(() => {
        if (isMounted) setFieldsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch health and time-series for selected field
  const fetchFieldData = useCallback(async (fieldId) => {
    if (!fieldId) return;
    setLoading(true);
    setError(null);

    try {
      const [healthRes, tsRes] = await Promise.all([
        getFieldHealth(fieldId),
        getFieldTimeSeries(fieldId)
      ]);
      setHealthData(healthRes);
      setTimeSeriesData(tsRes);
      setIsHistoricalSnapshot(false);

      // Automatically preserve analysis snapshot in local IndexedDB under current farmer
      const activeField = fields.find(f => f.field_id === fieldId);
      saveAnalysisHistoryRecord({
        fieldId: fieldId,
        fieldName: activeField?.field_name || `Field ${fieldId}`,
        latitude: activeField?.latitude,
        longitude: activeField?.longitude,
        healthData: healthRes,
        timeSeries: tsRes,
        isLive: true,
        timestamp: Date.now(),
      }).then(() => loadHistory()).catch(e => console.warn('IndexedDB auto-save note:', e));
    } catch (err) {
      console.error(`Error loading health for field ${fieldId}:`, err);
      const msg = err instanceof Error ? err.message : 'Failed to retrieve field health data.';
      const sanitized = msg
        .replace(/[A-Za-z]:\\[^"'\n\r\t<>]*/g, '[internal path]')
        .replace(/\/[\w.-]+(\/[\w.-]+)+/g, '[internal path]');
      setError(sanitized);
      setHealthData(null);
      setTimeSeriesData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedFieldId) {
      fetchFieldData(selectedFieldId);
    }
  }, [selectedFieldId, fetchFieldData]);

  // Derive health category and styling
  const healthStatus = useMemo(() => {
    if (!healthData) return { label: 'Unknown', color: '#64748b', bg: '#f1f5f9', border: '#cbd5e1', level: 'Unknown' };

    if (healthData.overall_health) {
      const oh = healthData.overall_health;
      const isRed = oh.color === 'red' || oh.status === 'High Vegetation Stress';
      const isAmber = oh.color === 'amber' || oh.status === 'Moderate Stress';
      return {
        label: oh.label || oh.status,
        color: isRed ? '#991b1b' : isAmber ? '#92400e' : '#166534',
        bg: isRed ? '#fee2e2' : isAmber ? '#fef3c7' : '#dcfce7',
        border: isRed ? '#fca5a5' : isAmber ? '#fde68a' : '#86efac',
        level: isRed ? 'High Stress' : isAmber ? 'Moderate' : 'Good',
        explanation: oh.summary
      };
    }

    const ndviTrend = healthData.changes_and_trends?.ndvi;
    const latestNdvi = healthData.latest_indices?.ndvi ?? 0;
    const direction = ndviTrend?.direction;

    // Fallback based on provisional thresholds (NDVI >= 0.50 healthy, 0.30-0.50 moderate, < 0.30 unhealthy)
    if (latestNdvi >= 0.50) {
      return {
        label: 'Healthy',
        color: '#166534',
        bg: '#dcfce7',
        border: '#86efac',
        level: 'Good',
        explanation: direction === 'decreasing'
          ? 'Crop canopy is currently in the healthy range, though trajectory shows slight decline.'
          : 'Your crop shows robust vegetative vigor and optimal canopy greenness.'
      };
    }

    if (latestNdvi >= 0.30) {
      return {
        label: 'Needs Attention',
        color: '#92400e',
        bg: '#fef3c7',
        border: '#fde68a',
        level: 'Moderate',
        explanation: direction === 'increasing'
          ? 'Vegetation indices indicate moderate canopy density with an improving trajectory.'
          : 'Vegetation indices indicate moderate canopy density. Routine field scouting recommended.'
      };
    }

    // Unhealthy / High Stress (< 0.30)
    return {
      label: 'High Risk',
      color: '#991b1b',
      bg: '#fee2e2',
      border: '#fca5a5',
      level: 'High Stress',
      explanation: direction === 'increasing'
        ? 'Current vegetation indices remain low, though multi-temporal vigor has improved from baseline.'
        : 'Vegetation indices reflect low canopy cover and persistent stress. Timely field inspection recommended.'
    };
  }, [healthData]);

  // Selected field details
  const selectedField = useMemo(() => {
    return fields.find((f) => f.field_id === selectedFieldId);
  }, [fields, selectedFieldId]);

  // Chart data calculations
  const chartPoints = useMemo(() => {
    if (!timeSeriesData || !timeSeriesData.timesteps || timeSeriesData.timesteps.length === 0) {
      return [];
    }
    return timeSeriesData.timesteps;
  }, [timeSeriesData]);

  return (
    <div className="glass-panel" style={{ width: '100%', marginBottom: '1.5rem', padding: '1.5rem', borderRadius: '16px' }}>
      {/* Component Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: 'var(--brand-primary, #0d5c38)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>🛰️</span> Field Health & Satellite Monitoring
          </h3>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary, #64748b)' }}>
            Real-time vegetation health, canopy vigor, and Sentinel-2 multi-spectral temporal trends
          </p>
        </div>

        {/* Field Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: '220px' }}>
          <label htmlFor="field-select-dropdown" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>
            Select Field:
          </label>
          <select
            id="field-select-dropdown"
            value={selectedFieldId}
            onChange={(e) => setSelectedFieldId(e.target.value)}
            disabled={fieldsLoading || fields.length === 0}
            style={{
              padding: '0.45rem 0.85rem',
              borderRadius: '8px',
              border: '1px solid rgba(13, 92, 56, 0.3)',
              background: '#ffffff',
              color: 'var(--brand-primary, #0d5c38)',
              fontWeight: 700,
              fontSize: '0.875rem',
              cursor: fieldsLoading ? 'wait' : 'pointer',
              outline: 'none'
            }}
          >
            {fieldsLoading ? (
              <option value="">Loading fields...</option>
            ) : fields.length === 0 ? (
              <option value="">No fields available</option>
            ) : (
              fields.map((f) => (
                <option key={f.field_id} value={f.field_id}>
                  {f.field_name || f.field_id} ({f.field_id})
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Historical Snapshot Viewing Notice */}
      {isHistoricalSnapshot && (
        <div style={{
          background: '#fffbeb',
          border: '1px solid #fde68a',
          borderRadius: '12px',
          padding: '0.85rem 1.15rem',
          marginBottom: '1.25rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          fontSize: '0.825rem',
          color: '#92400e'
        }}>
          <div>
            <strong>Viewing Saved Field Analysis Snapshot</strong> ({snapshotDate})
            <div style={{ fontSize: '0.75rem', color: '#b45309', marginTop: '0.15rem' }}>
              Preserved locally on your device without re-querying satellites.
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={() => fetchFieldData(selectedFieldId)}
              style={{
                background: '#0d5c38',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '0.4rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Re-analyze Live
            </button>
            <button
              type="button"
              onClick={() => setIsHistoricalSnapshot(false)}
              style={{
                background: '#f1f5f9',
                color: '#475569',
                border: '1px solid #cbd5e1',
                borderRadius: '8px',
                padding: '0.4rem 0.75rem',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              Exit Snapshot
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{
          padding: '2.5rem',
          textAlign: 'center',
          background: 'rgba(13, 92, 56, 0.03)',
          borderRadius: '12px',
          border: '1px solid rgba(13, 92, 56, 0.15)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <div style={{
            width: '36px',
            height: '36px',
            border: '3px solid rgba(13, 92, 56, 0.2)',
            borderTop: '3px solid var(--brand-primary, #0d5c38)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
          <div>
            <strong style={{ fontSize: '0.95rem', color: 'var(--brand-primary, #0d5c38)' }}>
              Loading Field Health Observations...
            </strong>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary, #64748b)' }}>
              Retrieving multi-spectral Sentinel-2 satellite observations...
            </p>
          </div>
        </div>
      )}

      {/* Error Alert State */}
      {error && !loading && (
        <div style={{
          padding: '1.25rem',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '12px',
          color: '#991b1b',
          marginBottom: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.25rem' }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <strong style={{ display: 'block', fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                Field Health Query Error
              </strong>
              <p style={{ margin: 0, fontSize: '0.85rem' }}>{error}</p>
              <button
                type="button"
                onClick={() => fetchFieldData(selectedFieldId)}
                className="btn btn-primary"
                style={{ marginTop: '0.75rem', padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
              >
                Retry Request
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Field Health Content Display */}
      {healthData && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Top Row: Overall Status Card & Field Summary Card */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {/* Status Card */}
            <div style={{
              background: '#ffffff',
              borderRadius: '12px',
              border: `1px solid ${healthStatus.border}`,
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
            }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Vegetation Health Status
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.35rem' }}>
                  <span style={{
                    padding: '0.35rem 0.85rem',
                    borderRadius: '9999px',
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    background: healthStatus.bg,
                    color: healthStatus.color,
                    border: `1px solid ${healthStatus.border}`
                  }}>
                    {healthStatus.label}
                  </span>
                  <span style={{ fontSize: '0.85rem', color: '#475569', fontWeight: 600 }}>
                    Vigor: {healthStatus.level}
                  </span>
                </div>
              </div>
              <p style={{ margin: '0.75rem 0 0 0', fontSize: '0.825rem', color: '#475569', lineHeight: '1.5' }}>
                {healthStatus.explanation}
              </p>
            </div>

            {/* Field Overview Card */}
            <div style={{
              background: '#ffffff',
              borderRadius: '12px',
              border: '1px solid #e2e8f0',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
            }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Field Information
                </span>
                <h4 style={{ margin: '0.25rem 0', fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                  {selectedField?.field_name || healthData.field_id}
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <span>Identifier: <strong>{healthData.field_id}</strong> ({healthData.clean_field_id || 'Catalog Field'})</span>
                  <span>Sentinel-2 Observations: <strong>{healthData.observation_count} Timesteps</strong></span>
                  <span>Latest Scan: <strong>{healthData.latest_observation_date || 'N/A'}</strong></span>
                </div>
              </div>
            </div>
          </div>

          {/* Middle Row: Latest Multi-Spectral Indices */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem'
          }}>
            {/* NDVI Card */}
            <div style={{
              background: 'rgba(13, 92, 56, 0.04)',
              border: '1px solid rgba(13, 92, 56, 0.2)',
              borderRadius: '10px',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--brand-primary, #0d5c38)', textTransform: 'uppercase' }}>
                    NDVI (Vegetation Index)
                  </span>
                  {healthData.classifications?.ndvi && (
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px',
                      background: healthData.classifications.ndvi.badge_color === 'green' ? '#dcfce7' : healthData.classifications.ndvi.badge_color === 'amber' ? '#fef3c7' : '#fee2e2',
                      color: healthData.classifications.ndvi.badge_color === 'green' ? '#166534' : healthData.classifications.ndvi.badge_color === 'amber' ? '#92400e' : '#991b1b',
                      border: `1px solid ${healthData.classifications.ndvi.badge_color === 'green' ? '#86efac' : healthData.classifications.ndvi.badge_color === 'amber' ? '#fde68a' : '#fca5a5'}`
                    }}>
                      {healthData.classifications.ndvi.label}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--brand-primary, #0d5c38)', margin: '0.25rem 0' }}>
                  {healthData.latest_indices?.ndvi?.toFixed(4) ?? '0.0000'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                  Trend: <strong>{healthData.changes_and_trends?.ndvi?.direction || 'stable'}</strong> ({healthData.changes_and_trends?.ndvi?.overall_change >= 0 ? '+' : ''}{healthData.changes_and_trends?.ndvi?.overall_change?.toFixed(4)})
                </div>
                {healthData.classifications?.ndvi?.condition_name && (
                  <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 600, marginTop: '0.2rem' }}>
                    {healthData.classifications.ndvi.condition_name}
                  </div>
                )}
              </div>
              {(healthData.classifications?.ndvi?.combined_explanation || healthData.classifications?.ndvi?.description) && (
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.72rem', color: '#64748b', borderTop: '1px solid rgba(0,0,0,0.06)', paddingTop: '0.4rem' }}>
                  {healthData.classifications.ndvi.combined_explanation || healthData.classifications.ndvi.description}
                </p>
              )}
            </div>

            {/* NDRE Card */}
            <div style={{
              background: 'rgba(5, 150, 105, 0.04)',
              border: '1px solid rgba(5, 150, 105, 0.2)',
              borderRadius: '10px',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#059669', textTransform: 'uppercase' }}>
                    NDRE (Red Edge Chlorophyll)
                  </span>
                  {healthData.classifications?.ndre && (
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px',
                      background: healthData.classifications.ndre.badge_color === 'green' ? '#dcfce7' : healthData.classifications.ndre.badge_color === 'amber' ? '#fef3c7' : '#fee2e2',
                      color: healthData.classifications.ndre.badge_color === 'green' ? '#166534' : healthData.classifications.ndre.badge_color === 'amber' ? '#92400e' : '#991b1b',
                      border: `1px solid ${healthData.classifications.ndre.badge_color === 'green' ? '#86efac' : healthData.classifications.ndre.badge_color === 'amber' ? '#fde68a' : '#fca5a5'}`
                    }}>
                      {healthData.classifications.ndre.label}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#059669', margin: '0.25rem 0' }}>
                  {healthData.latest_indices?.ndre?.toFixed(4) ?? '0.0000'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                  Trend: <strong>{healthData.changes_and_trends?.ndre?.direction || 'stable'}</strong> ({healthData.changes_and_trends?.ndre?.overall_change >= 0 ? '+' : ''}{healthData.changes_and_trends?.ndre?.overall_change?.toFixed(4)})
                </div>
                {healthData.classifications?.ndre?.condition_name && (
                  <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 600, marginTop: '0.2rem' }}>
                    {healthData.classifications.ndre.condition_name}
                  </div>
                )}
              </div>
              {(healthData.classifications?.ndre?.combined_explanation || healthData.classifications?.ndre?.description) && (
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.72rem', color: '#64748b', borderTop: '1px solid rgba(0,0,0,0.06)', paddingTop: '0.4rem' }}>
                  {healthData.classifications.ndre.combined_explanation || healthData.classifications.ndre.description}
                </p>
              )}
            </div>

            {/* GNDVI Card - SCIENTIFIC CORRECTION: Never claim nitrogen deficiency */}
            <div style={{
              background: 'rgba(16, 185, 129, 0.04)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: '10px',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#10b981', textTransform: 'uppercase' }}>
                    GNDVI (Green Canopy Vigor)
                  </span>
                  {healthData.classifications?.gndvi && (
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '0.15rem 0.45rem',
                      borderRadius: '4px',
                      background: healthData.classifications.gndvi.badge_color === 'green' ? '#dcfce7' : healthData.classifications.gndvi.badge_color === 'amber' ? '#fef3c7' : '#fee2e2',
                      color: healthData.classifications.gndvi.badge_color === 'green' ? '#166534' : healthData.classifications.gndvi.badge_color === 'amber' ? '#92400e' : '#991b1b',
                      border: `1px solid ${healthData.classifications.gndvi.badge_color === 'green' ? '#86efac' : healthData.classifications.gndvi.badge_color === 'amber' ? '#fde68a' : '#fca5a5'}`
                    }}>
                      {healthData.classifications.gndvi.label}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#10b981', margin: '0.25rem 0' }}>
                  {healthData.latest_indices?.gndvi?.toFixed(4) ?? '0.0000'}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#475569' }}>
                  Trend: <strong>{healthData.changes_and_trends?.gndvi?.direction || 'stable'}</strong> ({healthData.changes_and_trends?.gndvi?.overall_change >= 0 ? '+' : ''}{healthData.changes_and_trends?.gndvi?.overall_change?.toFixed(4)})
                </div>
                {healthData.classifications?.gndvi?.condition_name && (
                  <div style={{ fontSize: '0.72rem', color: '#334155', fontWeight: 600, marginTop: '0.2rem' }}>
                    {healthData.classifications.gndvi.condition_name}
                  </div>
                )}
              </div>
              {(healthData.classifications?.gndvi?.combined_explanation || healthData.classifications?.gndvi?.description) && (
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.72rem', color: '#64748b', borderTop: '1px solid rgba(0,0,0,0.06)', paddingTop: '0.4rem' }}>
                  {healthData.classifications.gndvi.combined_explanation || healthData.classifications.gndvi.description}
                </p>
              )}
            </div>
          </div>

          {/* Satellite Multi-Spectral Time-Series Chart */}
          <div style={{
            background: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #e2e8f0',
            padding: '1.25rem',
            boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#0f172a' }}>
                  Satellite Vegetation Trajectory (10 Sentinel-2 Timesteps)
                </h4>
                <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.775rem', color: '#64748b' }}>
                  Chronological progression of optical surface reflectance indices
                </p>
              </div>

              {/* Metric Filter Tabs */}
              <div style={{ display: 'flex', gap: '0.35rem', background: '#f1f5f9', padding: '0.2rem', borderRadius: '8px' }}>
                {['all', 'ndvi', 'ndre', 'gndvi'].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setActiveMetric(m)}
                    style={{
                      padding: '0.25rem 0.65rem',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      borderRadius: '6px',
                      border: 'none',
                      background: activeMetric === m ? '#ffffff' : 'transparent',
                      color: activeMetric === m ? 'var(--brand-primary, #0d5c38)' : '#64748b',
                      boxShadow: activeMetric === m ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                      cursor: 'pointer'
                    }}
                  >
                    {m.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Responsive SVG Chart */}
            {chartPoints.length > 0 ? (
              <div style={{ width: '100%', overflowX: 'auto' }}>
                <svg
                  viewBox="0 0 700 240"
                  style={{ width: '100%', height: 'auto', minWidth: '550px', maxHeight: '280px' }}
                >
                  <defs>
                    <linearGradient id="ndviGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0d5c38" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#0d5c38" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Horizontal Grid lines */}
                  {[0.0, 0.1, 0.2, 0.3, 0.4].map((val, idx) => {
                    const y = 200 - (val / 0.4) * 160;
                    return (
                      <g key={idx}>
                        <line x1="45" y1={y} x2="680" y2={y} stroke="#e2e8f0" strokeDasharray="3 3" />
                        <text x="38" y={y + 4} fontSize="10" fill="#94a3b8" textAnchor="end">
                          {val.toFixed(1)}
                        </text>
                      </g>
                    );
                  })}

                  {/* Lines & Data Points */}
                  {(() => {
                    const paddingLeft = 60;
                    const paddingRight = 660;
                    const stepWidth = (paddingRight - paddingLeft) / (chartPoints.length - 1 || 1);

                    const getY = (val) => 200 - (Math.max(0, Math.min(0.4, val)) / 0.4) * 160;

                    const ndviCoords = chartPoints.map((p, i) => ({ x: paddingLeft + i * stepWidth, y: getY(p.ndvi) }));
                    const ndreCoords = chartPoints.map((p, i) => ({ x: paddingLeft + i * stepWidth, y: getY(p.ndre) }));
                    const gndviCoords = chartPoints.map((p, i) => ({ x: paddingLeft + i * stepWidth, y: getY(p.gndvi) }));

                    const toPath = (coords) => coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ');

                    return (
                      <>
                        {/* Area fill for NDVI if active */}
                        {(activeMetric === 'all' || activeMetric === 'ndvi') && (
                          <path
                            d={`${toPath(ndviCoords)} L ${ndviCoords[ndviCoords.length - 1].x} 200 L ${ndviCoords[0].x} 200 Z`}
                            fill="url(#ndviGrad)"
                          />
                        )}

                        {/* NDVI Line */}
                        {(activeMetric === 'all' || activeMetric === 'ndvi') && (
                          <>
                            <path d={toPath(ndviCoords)} fill="none" stroke="#0d5c38" strokeWidth="2.5" />
                            {ndviCoords.map((c, i) => (
                              <circle key={`ndvi-${i}`} cx={c.x} cy={c.y} r="3.5" fill="#0d5c38" />
                            ))}
                          </>
                        )}

                        {/* NDRE Line */}
                        {(activeMetric === 'all' || activeMetric === 'ndre') && (
                          <>
                            <path d={toPath(ndreCoords)} fill="none" stroke="#059669" strokeWidth="2" strokeDasharray="4 4" />
                            {ndreCoords.map((c, i) => (
                              <circle key={`ndre-${i}`} cx={c.x} cy={c.y} r="3" fill="#059669" />
                            ))}
                          </>
                        )}

                        {/* GNDVI Line */}
                        {(activeMetric === 'all' || activeMetric === 'gndvi') && (
                          <>
                            <path d={toPath(gndviCoords)} fill="none" stroke="#10b981" strokeWidth="2" />
                            {gndviCoords.map((c, i) => (
                              <circle key={`gndvi-${i}`} cx={c.x} cy={c.y} r="3" fill="#10b981" />
                            ))}
                          </>
                        )}

                        {/* X-axis Date Labels */}
                        {chartPoints.map((p, i) => {
                          const x = paddingLeft + i * stepWidth;
                          const dateLabel = p.date ? p.date.slice(5) : `T${p.timestep}`;
                          return (
                            <text
                              key={`label-${i}`}
                              x={x}
                              y="218"
                              fontSize="9.5"
                              fill="#64748b"
                              textAnchor="middle"
                            >
                              {dateLabel}
                            </text>
                          );
                        })}
                      </>
                    );
                  })()}
                </svg>
                {/* Legend indicator */}
                <div style={{ display: 'flex', justifyContent: 'center', gap: '1.25rem', marginTop: '0.5rem', fontSize: '0.75rem', color: '#64748b' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '12px', height: '3px', background: '#0d5c38', display: 'inline-block' }}></span> NDVI
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '12px', height: '3px', background: '#059669', borderTop: '1px dashed #059669', display: 'inline-block' }}></span> NDRE
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '12px', height: '3px', background: '#10b981', display: 'inline-block' }}></span> GNDVI
                  </span>
                </div>
              </div>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
                No satellite observations available for this field.
              </div>
            )}
          </div>

          {/* Advisory & Data Quality Notes */}
          <div style={{
            background: 'rgba(13, 92, 56, 0.03)',
            borderRadius: '10px',
            border: '1px solid rgba(13, 92, 56, 0.12)',
            padding: '1rem',
            fontSize: '0.825rem',
            color: '#334155',
            lineHeight: '1.5'
          }}>
            <strong>Agronomic Summary:</strong> {healthData.advisory_summary}
            <div style={{ marginTop: '0.5rem', fontSize: '0.775rem', color: '#64748b' }}>
              <em>Note:</em> {healthData.limitations_and_interpretation_notes?.[0] || 'Satellite vegetation indices quantify canopy chlorophyll absorption.'}
            </div>
          </div>
        </div>
      )}

      {/* Persistent Field Health Analysis History Section */}
      <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
        {/* History Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>📜</span> Field Health Analysis History
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '0.15rem 0.6rem',
                borderRadius: '9999px',
                background: '#f1f5f9',
                color: '#334155',
                border: '1px solid #cbd5e1'
              }}>
                {historyList.length} {historyList.length === 1 ? 'Analysis' : 'Analyses'}
              </span>
            </h4>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>
              Locally stored analysis snapshots for account <strong>{farmerName}</strong>.
            </p>
          </div>

          {historyList.length > 0 && (
            <button
              type="button"
              onClick={async () => {
                if (window.confirm('Delete all locally stored field analysis records for your current account?')) {
                  await clearFarmerAnalysisHistory();
                  await loadHistory();
                }
              }}
              style={{
                background: '#fff1f2',
                color: '#be123c',
                border: '1px solid #fecdd3',
                borderRadius: '8px',
                padding: '0.4rem 0.8rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Clear All History
            </button>
          )}
        </div>

        {/* History List or Empty State */}
        {historyList.length === 0 ? (
          <div style={{
            background: '#ffffff',
            border: '1px dashed #cbd5e1',
            borderRadius: '12px',
            padding: '2rem',
            textAlign: 'center',
            color: '#64748b',
            fontSize: '0.85rem'
          }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>🌱</div>
            <strong>No Analysis History Yet</strong>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.775rem', color: '#94a3b8' }}>
              Select a field above to analyze its health. Records will be saved automatically to your device.
            </p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem'
          }}>
            {historyList.map((rec) => {
              const overall = rec.healthData?.overall_health?.status || 'Active';
              const ndvi = rec.healthData?.latest_indices?.ndvi;
              const ndre = rec.healthData?.latest_indices?.ndre;
              const gndvi = rec.healthData?.latest_indices?.gndvi;

              const ndviCat = rec.healthData?.indices_classification?.ndvi?.status?.category || 'Provisional';
              const ndreCat = rec.healthData?.indices_classification?.ndre?.status?.category || 'Provisional';
              const gndviCat = rec.healthData?.indices_classification?.gndvi?.status?.category || 'Provisional';

              let overallBg = '#f1f5f9';
              let overallColor = '#334155';
              if (overall.toLowerCase().includes('healthy')) {
                overallBg = '#dcfce7';
                overallColor = '#15803d';
              } else if (overall.toLowerCase().includes('moderate') || overall.toLowerCase().includes('attention')) {
                overallBg = '#fef3c7';
                overallColor = '#b45309';
              } else if (overall.toLowerCase().includes('unhealthy') || overall.toLowerCase().includes('risk')) {
                overallBg = '#fee2e2';
                overallColor = '#b91c1c';
              }

              return (
                <div
                  key={rec.id}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '12px',
                    padding: '1rem',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '0.75rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.5rem' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a' }}>
                        {rec.fieldName || rec.fieldId}
                      </div>
                      <div style={{ fontSize: '0.725rem', color: '#64748b', fontFamily: 'monospace' }}>
                        {rec.displayDate || formatAnalysisDate(rec.timestamp)}
                      </div>
                    </div>
                    <span style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.5rem',
                      borderRadius: '9999px',
                      background: overallBg,
                      color: overallColor
                    }}>
                      {overall}
                    </span>
                  </div>

                  {/* Indices strip */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    gap: '0.5rem',
                    background: '#f8fafc',
                    padding: '0.5rem',
                    borderRadius: '8px',
                    textAlign: 'center'
                  }}>
                    <div>
                      <span style={{ fontSize: '0.65rem', color: '#64748b', display: 'block', fontWeight: 700 }}>NDVI</span>
                      <strong style={{ fontSize: '0.8rem', color: '#0f172a' }}>{ndvi !== undefined && ndvi !== null ? Number(ndvi).toFixed(2) : '--'}</strong>
                      <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#15803d' }}>{ndviCat}</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.65rem', color: '#64748b', display: 'block', fontWeight: 700 }}>NDRE</span>
                      <strong style={{ fontSize: '0.8rem', color: '#0f172a' }}>{ndre !== undefined && ndre !== null ? Number(ndre).toFixed(2) : '--'}</strong>
                      <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#059669' }}>{ndreCat}</div>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.65rem', color: '#64748b', display: 'block', fontWeight: 700 }}>GNDVI</span>
                      <strong style={{ fontSize: '0.8rem', color: '#0f172a' }}>{gndvi !== undefined && gndvi !== null ? Number(gndvi).toFixed(2) : '--'}</strong>
                      <div style={{ fontSize: '0.65rem', fontWeight: 600, color: '#0d5c38' }}>{gndviCat}</div>
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid #f1f5f9' }}>
                    <button
                      type="button"
                      onClick={() => {
                        setHealthData(rec.healthData);
                        setTimeSeriesData(rec.timeSeries);
                        setIsHistoricalSnapshot(true);
                        setSnapshotDate(rec.displayDate || formatAnalysisDate(rec.timestamp));
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      style={{
                        background: '#ecfdf5',
                        color: '#065f46',
                        border: '1px solid #a7f3d0',
                        borderRadius: '6px',
                        padding: '0.3rem 0.65rem',
                        fontSize: '0.725rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      View Details
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        if (window.confirm('Delete this field analysis record from local history?')) {
                          await deleteAnalysisHistoryRecord(rec.id);
                          await loadHistory();
                        }
                      }}
                      style={{
                        background: 'transparent',
                        color: '#94a3b8',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '0.85rem'
                      }}
                      title="Delete Record"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default FieldHealth;
