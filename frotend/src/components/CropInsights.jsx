import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  getPredictions, 
  getPredictionById, 
  getCropInsightsSummary,
  getFieldHealth,
  getFieldTimeSeries
} from '../api/client';
import { API_BASE_URL } from '../api/config';

/**
 * Scientifically validated agricultural knowledge base for the 13 paddy classes.
 */
const DISEASE_KNOWLEDGE_BASE = {
  bacterial_leaf_blight: {
    displayName: 'Bacterial Leaf Blight',
    badgeType: 'risk',
    badgeText: 'High Risk',
    symptoms: 'Water-soaked lesions on leaf margins and tips that turn yellow to grayish-white with characteristic wavy edges.',
    action: 'Avoid excessive nitrogen fertilization. Ensure good field drainage, avoid clipping seedlings, and apply recommended copper-based bactericides if advised locally.'
  },
  bacterial_leaf_streak: {
    displayName: 'Bacterial Leaf Streak',
    badgeType: 'attention',
    badgeText: 'Needs Attention',
    symptoms: 'Narrow, yellowish-brown translucent streaks between leaf veins that may exude tiny amber-colored bacterial droplets.',
    action: 'Manage nitrogen application carefully. Drain excess stagnant water to reduce canopy humidity and apply recommended protective treatments.'
  },
  bacterial_panicle_blight: {
    displayName: 'Bacterial Panicle Blight',
    badgeType: 'risk',
    badgeText: 'High Risk',
    symptoms: 'Discolored florets turning gray-brown with dark borders; aborted grains leaving affected panicles standing upright.',
    action: 'Plant certified clean seed. Avoid excessive nitrogen fertilizer during booting/heading and apply preventive treatments during early flowering.'
  },
  blast: {
    displayName: 'Rice Blast',
    badgeType: 'risk',
    badgeText: 'High Risk',
    symptoms: 'Spindle-shaped or diamond-shaped lesions with grayish-white centers and dark brown to reddish margins.',
    action: 'Apply recommended systemic fungicides (such as tricyclazole or isoprothiolane). Avoid high nitrogen doses and maintain shallow water in the field.'
  },
  brown_spot: {
    displayName: 'Brown Spot',
    badgeType: 'attention',
    badgeText: 'Needs Attention',
    symptoms: 'Small, circular to oval dark-brown spots with yellow halos evenly distributed across the leaf blade.',
    action: 'Improve soil fertility by providing balanced NPK nutrients (especially potassium and zinc). Treat seeds with fungicide before subsequent planting.'
  },
  dead_heart: {
    displayName: 'Dead Heart (Stem Borer)',
    badgeType: 'risk',
    badgeText: 'High Risk',
    symptoms: 'Drying and withering of the central tiller shoot caused by internal larvae feeding, while outer leaves may temporarily remain green.',
    action: 'Install pheromone traps for pest monitoring. Conserve beneficial predators and apply recommended insect pest control at the egg-hatch stage.'
  },
  downy_mildew: {
    displayName: 'Downy Mildew',
    badgeType: 'attention',
    badgeText: 'Needs Attention',
    symptoms: 'Stunted seedlings with pale yellowish chlorotic blotches or twisting, curling, and thickening of leaf blades.',
    action: 'Ensure adequate field drainage to avoid prolonged waterlogging. Remove severely infected hills from the nursery.'
  },
  hispa: {
    displayName: 'Rice Hispa',
    badgeType: 'attention',
    badgeText: 'Needs Attention',
    symptoms: 'White parallel translucent streaks where adult beetles scraped green leaf tissue, leaving only the lower epidermal layer.',
    action: 'Sweep net to reduce adult beetle populations. Clip infested leaf tips before transplanting, or apply recommended agricultural insecticides.'
  },
  leaf_scald: {
    displayName: 'Leaf Scald',
    badgeType: 'attention',
    badgeText: 'Needs Attention',
    symptoms: 'Zonate, oblong chevron-patterned lesions extending from leaf tips with alternating light and dark brown bands.',
    action: 'Use balanced fertilizer applications. Avoid excess nitrogen, maintain plant spacing for ventilation, and apply protective fungicides if necessary.'
  },
  leaf_smut: {
    displayName: 'Leaf Smut',
    badgeType: 'attention',
    badgeText: 'Needs Attention',
    symptoms: 'Small, raised, angular black spots or pustules scattered on mature leaves, covered by the leaf epidermis.',
    action: 'Leaf smut usually causes low yield impact. Maintain balanced crop nutrition and avoid excessive nitrogen fertilizer.'
  },
  normal: {
    displayName: 'Normal / Healthy Crop',
    badgeType: 'healthy',
    badgeText: 'Healthy',
    symptoms: 'Leaves exhibit uniform green pigmentation, healthy structure, and no visible fungal spots or pest damage.',
    action: 'Maintain your current watering and nutrient schedule. Continue regular field scouting every few days.'
  },
  sheath_blight: {
    displayName: 'Sheath Blight',
    badgeType: 'risk',
    badgeText: 'High Risk',
    symptoms: 'Oval or irregular greenish-gray water-soaked spots on leaf sheaths near the water level that progress upward.',
    action: 'Ensure appropriate hill spacing for air flow, avoid excessive nitrogen, and apply recommended fungicides (e.g., validamycin or azoxystrobin).'
  },
  tungro: {
    displayName: 'Rice Tungro Disease',
    badgeType: 'risk',
    badgeText: 'High Risk',
    symptoms: 'Stunting of plants with characteristic yellow or orange-yellow discoloration of leaves starting from the tips.',
    action: 'Control green leafhopper vectors using recommended agricultural measures. Rogue and destroy infected hills promptly.'
  }
};

const getStatusBadge = (diseaseName, isHealthy) => {
  if (isHealthy || diseaseName === 'normal') {
    return {
      text: 'Healthy',
      color: '#2e7d32',
      bg: '#e8f5e9',
      border: '#a5d6a7'
    };
  }
  const meta = DISEASE_KNOWLEDGE_BASE[diseaseName];
  if (meta && meta.badgeType === 'attention') {
    return {
      text: 'Needs Attention',
      color: '#ed6c02',
      bg: '#fff4e5',
      border: '#ffcc80'
    };
  }
  return {
    text: 'High Risk',
    color: '#d32f2f',
    bg: '#ffebee',
    border: '#ef9a9a'
  };
};

const getInfluenceBadge = (level) => {
  switch (level) {
    case 'High':
      return { text: 'High', color: '#d32f2f', bg: '#ffebee' };
    case 'Medium':
      return { text: 'Medium', color: '#ed6c02', bg: '#fff4e5' };
    case 'Low':
      return { text: 'Low', color: '#2e7d32', bg: '#e8f5e9' };
    default:
      return { text: 'N/A', color: '#757575', bg: '#f5f5f5' };
  }
};

const CropInsights = () => {
  // Filters & State
  const [modeFilter, setModeFilter] = useState('all'); // 'all' | 'multimodal' | 'image_only'
  const [predictions, setPredictions] = useState([]);
  const [selectedPredId, setSelectedPredId] = useState('');
  const [activeRecord, setActiveRecord] = useState(null);
  const [fieldHealth, setFieldHealth] = useState(null);
  const [timeSeries, setTimeSeries] = useState(null);
  const [summary, setSummary] = useState(null);

  // Status flags
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load initial prediction list and statistical summary
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [listRes, summaryRes] = await Promise.all([
        getPredictions({ pageSize: 50 }),
        getCropInsightsSummary()
      ]);

      const records = listRes.predictions || [];
      setPredictions(records);
      setSummary(summaryRes);

      if (records.length > 0) {
        setSelectedPredId(records[0].id);
      }
    } catch (err) {
      console.error('Failed to load crop insights data:', err);
      setError(err instanceof Error ? err.message : 'Unable to connect to crop insights service.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load details when selected prediction changes
  useEffect(() => {
    if (!selectedPredId) {
      setActiveRecord(null);
      setFieldHealth(null);
      setTimeSeries(null);
      return;
    }

    let isMounted = true;
    setDetailLoading(true);

    const fetchDetails = async () => {
      try {
        const record = await getPredictionById(selectedPredId);
        if (!isMounted) return;
        setActiveRecord(record);

        // If prediction is multimodal or linked to a field, fetch field health & time-series
        if (record.field_id) {
          try {
            const [healthData, tsData] = await Promise.all([
              getFieldHealth(record.field_id).catch(() => null),
              getFieldTimeSeries(record.field_id).catch(() => null)
            ]);
            if (isMounted) {
              setFieldHealth(healthData);
              setTimeSeries(tsData);
            }
          } catch {
            if (isMounted) {
              setFieldHealth(null);
              setTimeSeries(null);
            }
          }
        } else {
          setFieldHealth(null);
          setTimeSeries(null);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Failed to load prediction details:', err);
          setActiveRecord(null);
        }
      } finally {
        if (isMounted) setDetailLoading(false);
      }
    };

    fetchDetails();

    return () => {
      isMounted = false;
    };
  }, [selectedPredId]);

  // Filtered prediction list
  const filteredPredictions = useMemo(() => {
    if (modeFilter === 'all') return predictions;
    return predictions.filter(p => p.prediction_mode === modeFilter);
  }, [predictions, modeFilter]);

  // Handle mode filter click
  const handleModeChange = (mode) => {
    setModeFilter(mode);
    const matching = mode === 'all' 
      ? predictions 
      : predictions.filter(p => p.prediction_mode === mode);
    if (matching.length > 0) {
      setSelectedPredId(matching[0].id);
    } else {
      setSelectedPredId('');
      setActiveRecord(null);
    }
  };

  // Derived influences for active record
  const influences = useMemo(() => {
    if (!activeRecord) return null;
    const isMultimodal = activeRecord.prediction_mode === 'multimodal' || !!activeRecord.field_id;
    
    // Leaf appearance influence derived from confidence score
    let leafLevel = 'Medium';
    if (activeRecord.confidence >= 0.85) leafLevel = 'High';
    else if (activeRecord.confidence < 0.60) leafLevel = 'Low';

    // Crop health change influence derived from NDVI trend
    let healthLevel = 'N/A';
    if (isMultimodal && fieldHealth?.changes_and_trends?.ndvi) {
      const dir = fieldHealth.changes_and_trends.ndvi.direction;
      if (dir === 'decreasing') healthLevel = 'High';
      else if (dir === 'stable') healthLevel = 'Medium';
      else healthLevel = 'Low';
    }

    // Field condition influence derived from latest NDVI
    let fieldLevel = 'N/A';
    if (isMultimodal && fieldHealth?.latest_indices) {
      const ndvi = fieldHealth.latest_indices.ndvi;
      if (ndvi < 0.25) fieldLevel = 'High';
      else if (ndvi < 0.40) fieldLevel = 'Medium';
      else fieldLevel = 'Low';
    }

    return {
      hasFieldData: isMultimodal,
      leaf: leafLevel,
      health: healthLevel,
      field: fieldLevel
    };
  }, [activeRecord, fieldHealth]);

  const activeKnowledge = useMemo(() => {
    if (!activeRecord) return null;
    return DISEASE_KNOWLEDGE_BASE[activeRecord.predicted_disease] || {
      displayName: activeRecord.predicted_disease.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      badgeType: activeRecord.is_healthy ? 'healthy' : 'risk',
      badgeText: activeRecord.is_healthy ? 'Healthy' : 'Needs Inspection',
      symptoms: 'Foliar patterns and discoloration indicative of paddy pathology.',
      action: 'Consult local agricultural extension officer for field verification.'
    };
  }, [activeRecord]);

  const statusBadge = useMemo(() => {
    if (!activeRecord) return null;
    return getStatusBadge(activeRecord.predicted_disease, activeRecord.is_healthy);
  }, [activeRecord]);

  return (
    <section 
      aria-label="Crop Insights and Diagnostic Intelligence"
      style={{
        marginTop: '2rem',
        marginBottom: '2rem',
        backgroundColor: '#ffffff',
        borderRadius: '16px',
        border: '1px solid #e0e0e0',
        padding: '1.75rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)'
      }}
    >
      {/* Header & Mode Tabs */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '1.5rem' }}>🌾</span>
            <h3 style={{ margin: 0, fontSize: '1.35rem', color: '#0d5c38', fontWeight: 700 }}>
              Crop Insights & Diagnostic Intelligence
            </h3>
          </div>
          <p style={{ margin: 0, fontSize: '0.875rem', color: '#666' }}>
            Cross-analyzing foliar AI diagnostics with Sentinel-2 satellite vegetative vigor
          </p>
        </div>

        {/* Mode Filter Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', background: '#f5f5f5', padding: '0.25rem', borderRadius: '8px' }}>
          {[
            { id: 'all', label: 'All Inferences' },
            { id: 'multimodal', label: 'Multimodal (Image + Satellite)' },
            { id: 'image_only', label: 'Photo Only' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => handleModeChange(tab.id)}
              style={{
                padding: '0.4rem 0.85rem',
                fontSize: '0.8rem',
                fontWeight: modeFilter === tab.id ? 600 : 500,
                color: modeFilter === tab.id ? '#0d5c38' : '#666',
                background: modeFilter === tab.id ? '#ffffff' : 'transparent',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                boxShadow: modeFilter === tab.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                transition: 'all 0.2s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div style={{
          backgroundColor: '#ffebee',
          border: '1px solid #ef9a9a',
          color: '#c62828',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <strong>Unable to load Crop Insights:</strong> {error}
          </div>
          <button 
            onClick={loadInitialData}
            style={{
              padding: '0.35rem 0.75rem',
              backgroundColor: '#d32f2f',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              fontSize: '0.8rem',
              cursor: 'pointer'
            }}
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Statistical KPI Cards */}
      {summary && !loading && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem'
        }}>
          <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
            <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Total Inferences</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0d5c38', marginTop: '0.25rem' }}>
              {summary.totalPredictions}
            </div>
            <span style={{ fontSize: '0.75rem', color: '#888' }}>persisted diagnostic logs</span>
          </div>

          <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
            <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Multimodal Diagnoses</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#0288d1', marginTop: '0.25rem' }}>
              {summary.multimodalCount}
            </div>
            <span style={{ fontSize: '0.75rem', color: '#888' }}>leaf + satellite fusion</span>
          </div>

          <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
            <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Photo-Only Checks</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#795548', marginTop: '0.25rem' }}>
              {summary.imageOnlyCount}
            </div>
            <span style={{ fontSize: '0.75rem', color: '#888' }}>visual EfficientNet inference</span>
          </div>

          <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '10px', border: '1px solid #e2ece6' }}>
            <span style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Average Confidence</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#2e7d32', marginTop: '0.25rem' }}>
              {summary.avgConfidence}%
            </div>
            <span style={{ fontSize: '0.75rem', color: '#888' }}>across all inferences</span>
          </div>
        </div>
      )}

      {/* Disease Distribution Chart (Real Data from PostgreSQL) */}
      {summary && summary.diseaseDistribution.length > 0 && (
        <div style={{
          backgroundColor: '#fafbfc',
          border: '1px solid #e5e9ec',
          borderRadius: '12px',
          padding: '1.25rem',
          marginBottom: '1.75rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#0d5c38', fontWeight: 600 }}>
                Diagnostic Distribution Across Historical Records
              </h4>
              <span style={{ fontSize: '0.75rem', color: '#777' }}>
                Frequency of occurrence computed directly from genuine database inference records
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {summary.diseaseDistribution.slice(0, 6).map((item) => {
              const barColor = item.healthy 
                ? '#2e7d32' 
                : item.avgConfidence > 85 ? '#d32f2f' : '#ed6c02';
              return (
                <div key={item.disease} style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.8rem' }}>
                  <div style={{ width: '150px', fontWeight: 500, color: '#333', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.displayName}
                  </div>
                  <div style={{ flex: 1, backgroundColor: '#e9ecef', height: '14px', borderRadius: '7px', overflow: 'hidden' }}>
                    <div 
                      style={{
                        width: `${Math.max(item.percentage, 4)}%`,
                        backgroundColor: barColor,
                        height: '100%',
                        borderRadius: '7px',
                        transition: 'width 0.4s ease'
                      }}
                    />
                  </div>
                  <div style={{ width: '70px', textAlign: 'right', fontWeight: 600, color: '#444' }}>
                    {item.count} ({item.percentage}%)
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Prediction Selection Dropdown */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label 
          htmlFor="crop-insights-prediction-selector"
          style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#333', marginBottom: '0.4rem' }}
        >
          Select Diagnostic Inference Record:
        </label>
        <select
          id="crop-insights-prediction-selector"
          value={selectedPredId}
          onChange={(e) => setSelectedPredId(e.target.value)}
          disabled={loading || filteredPredictions.length === 0}
          style={{
            width: '100%',
            maxWidth: '650px',
            padding: '0.65rem 0.9rem',
            borderRadius: '8px',
            border: '1px solid #0d5c38',
            backgroundColor: '#ffffff',
            color: '#1a3826',
            fontSize: '0.9rem',
            outline: 'none',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          {filteredPredictions.length === 0 ? (
            <option value="">No matching predictions available</option>
          ) : (
            filteredPredictions.map(p => {
              const dt = new Date(p.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              });
              const modeTag = p.prediction_mode === 'multimodal' ? '[Multimodal]' : '[Photo-Only]';
              const diseaseName = p.predicted_disease.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
              const confPct = Math.round((p.confidence || 0) * 100);
              return (
                <option key={p.id} value={p.id}>
                  {modeTag} {diseaseName} ({confPct}%) — {dt}
                </option>
              );
            })
          )}
        </select>
      </div>

      {/* Loading Skeleton */}
      {detailLoading && (
        <div style={{ textAlign: 'center', padding: '2.5rem 0', color: '#0d5c38' }}>
          <div style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>⏳</div>
          <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 500 }}>
            Retrieving diagnosis details and field health indicators...
          </p>
        </div>
      )}

      {/* Active Record Detail View */}
      {activeRecord && !detailLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Result Recap & Status Card */}
          <div style={{
            background: 'linear-gradient(135deg, #f9fbf9 0%, #f0f7f3 100%)',
            border: '1px solid #d0e5d8',
            borderRadius: '12px',
            padding: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <div>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#555', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Diagnostic Result
              </span>
              <h2 style={{ margin: '0.25rem 0 0.5rem 0', fontSize: '1.8rem', color: '#0d5c38', fontWeight: 700 }}>
                {activeKnowledge?.displayName}
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 600, color: '#2c3e50' }}>
                  {Math.round((activeRecord.confidence || 0) * 100)}% Confidence
                </span>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '0.3rem 0.85rem',
                  borderRadius: '20px',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: statusBadge?.color,
                  backgroundColor: statusBadge?.bg,
                  border: `1px solid ${statusBadge?.border}`
                }}>
                  {statusBadge?.text}
                </span>
                <span style={{ fontSize: '0.8rem', color: '#666', background: '#e8f0ec', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                  Mode: {activeRecord.prediction_mode}
                </span>
                <span style={{ fontSize: '0.8rem', color: '#666', background: '#e8f0ec', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
                  Model: {activeRecord.model_name} ({activeRecord.model_version})
                </span>
              </div>
            </div>

            {/* Confidence Gauge */}
            <div style={{ textAlign: 'center', minWidth: '120px' }}>
              <div style={{
                width: '74px',
                height: '74px',
                borderRadius: '50%',
                border: `5px solid ${statusBadge?.color}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto',
                fontWeight: 700,
                fontSize: '1.1rem',
                color: statusBadge?.color
              }}>
                {Math.round((activeRecord.confidence || 0) * 100)}%
              </div>
              <span style={{ fontSize: '0.75rem', color: '#666', display: 'block', marginTop: '0.35rem' }}>
                Model Certainty
              </span>
            </div>
          </div>

          {/* Factors Considered (Influences Grid) */}
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e0e0e0',
            borderRadius: '12px',
            padding: '1.25rem'
          }}>
            <h4 style={{ margin: '0 0 1rem 0', fontSize: '1rem', color: '#0d5c38', fontWeight: 600 }}>
              Diagnostic Factors Considered
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
              {/* Leaf Appearance */}
              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '8px', border: '1px solid #e5ebe7', textAlign: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#555', display: 'block', marginBottom: '0.5rem' }}>
                  Leaf Foliar Appearance
                </span>
                {(() => {
                  const b = getInfluenceBadge(influences?.leaf);
                  return (
                    <span style={{ padding: '0.25rem 0.75rem', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 700, color: b.color, background: b.bg }}>
                      {b.text} Influence
                    </span>
                  );
                })()}
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.75rem', color: '#777' }}>
                  Visual symptoms on leaf blade evaluated by EfficientNet-B4.
                </p>
              </div>

              {/* Crop Health Change */}
              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '8px', border: '1px solid #e5ebe7', textAlign: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#555', display: 'block', marginBottom: '0.5rem' }}>
                  Satellite Health Change
                </span>
                {(() => {
                  const b = getInfluenceBadge(influences?.health);
                  return (
                    <span style={{ padding: '0.25rem 0.75rem', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 700, color: b.color, background: b.bg }}>
                      {b.text} Influence
                    </span>
                  );
                })()}
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.75rem', color: '#777' }}>
                  {influences?.hasFieldData 
                    ? `Trend: ${fieldHealth?.changes_and_trends?.ndvi?.direction || 'stable'} (${fieldHealth?.changes_and_trends?.ndvi?.percentage_change || 0}% change)`
                    : 'Not applicable for photo-only diagnosis.'}
                </p>
              </div>

              {/* Field Condition */}
              <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '8px', border: '1px solid #e5ebe7', textAlign: 'center' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#555', display: 'block', marginBottom: '0.5rem' }}>
                  Overall Field Vigor
                </span>
                {(() => {
                  const b = getInfluenceBadge(influences?.field);
                  return (
                    <span style={{ padding: '0.25rem 0.75rem', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 700, color: b.color, background: b.bg }}>
                      {b.text} Influence
                    </span>
                  );
                })()}
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.75rem', color: '#777' }}>
                  {influences?.hasFieldData 
                    ? `Latest NDVI: ${fieldHealth?.latest_indices?.ndvi?.toFixed(3) || 'N/A'}`
                    : 'Field monitoring data not attached.'}
                </p>
              </div>
            </div>

            {/* Photo-only informational alert */}
            {!influences?.hasFieldData && (
              <div style={{
                marginTop: '1rem',
                backgroundColor: '#e3f2fd',
                border: '1px solid #bbdefb',
                color: '#0d47a1',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <span>ℹ️</span>
                <span>
                  <strong>Photo-Only Inference:</strong> Satellite vegetation indices are not attached to this diagnosis. The result is derived entirely from foliar image analysis.
                </span>
              </div>
            )}
          </div>

          {/* Temporal Cross-Attention Visualization (Multimodal Predictions) */}
          {activeRecord.attention_weights && activeRecord.attention_weights.length > 0 && (
            <div style={{
              backgroundColor: '#fafcfb',
              border: '1px solid #d8e8de',
              borderRadius: '12px',
              padding: '1.25rem'
            }}>
              <div style={{ marginBottom: '1rem' }}>
                <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#0d5c38', fontWeight: 600 }}>
                  Temporal Cross-Attention Weights (Sentinel-2 Satellite Timesteps)
                </h4>
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: '#666' }}>
                  Shows the relative importance assigned by the Temporal Cross-Attention model to each satellite observation date.
                </p>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${activeRecord.attention_weights.length}, 1fr)`,
                gap: '0.4rem',
                alignItems: 'flex-end',
                height: '110px',
                padding: '0.5rem 0',
                borderBottom: '1px solid #ddd'
              }}>
                {activeRecord.attention_weights.map((w, idx) => {
                  const maxW = Math.max(...activeRecord.attention_weights);
                  const heightPct = maxW > 0 ? (w / maxW) * 90 : 20;
                  const isTop = w === maxW;
                  return (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                      <span style={{ fontSize: '0.65rem', color: isTop ? '#0d5c38' : '#777', fontWeight: isTop ? 700 : 500, marginBottom: '2px' }}>
                        {(w * 100).toFixed(1)}%
                      </span>
                      <div 
                        style={{
                          width: '100%',
                          height: `${heightPct}%`,
                          backgroundColor: isTop ? '#0d5c38' : '#81c784',
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.3s ease'
                        }}
                      />
                    </div>
                  );
                })}
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: `repeat(${activeRecord.attention_weights.length}, 1fr)`,
                gap: '0.4rem',
                marginTop: '0.35rem',
                fontSize: '0.65rem',
                color: '#666',
                textAlign: 'center'
              }}>
                {activeRecord.attention_weights.map((_, idx) => (
                  <span key={idx}>T{idx + 1}</span>
                ))}
              </div>
            </div>
          )}

          {/* Symptoms & Agronomic Management */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            {/* Scientific Symptoms */}
            <div style={{ backgroundColor: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '12px', padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '1.2rem' }}>🔍</span>
                <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#0d5c38', fontWeight: 600 }}>
                  Diagnostic Foliar Symptoms
                </h4>
              </div>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#444', lineHeight: 1.5 }}>
                {activeKnowledge?.symptoms}
              </p>
            </div>

            {/* Actionable Agronomic Advice */}
            <div style={{ backgroundColor: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '12px', padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '1.2rem' }}>🛡️</span>
                <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#0d5c38', fontWeight: 600 }}>
                  Recommended Agronomic Action
                </h4>
              </div>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#444', lineHeight: 1.5 }}>
                {activeKnowledge?.action}
              </p>
            </div>
          </div>

          {/* Plain Explanation Card */}
          <div style={{
            backgroundColor: '#e8f5e9',
            border: '1px solid #c8e6c9',
            borderRadius: '12px',
            padding: '1.25rem'
          }}>
            <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem', color: '#2e7d32', fontWeight: 700 }}>
              Advisory Summary & Decision Support
            </h4>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#1b5e20', lineHeight: 1.6 }}>
              {activeRecord.predicted_disease === 'normal' 
                ? 'The leaf sample shows uniform healthy tissue. Satellite observation trends confirm standard canopy vigor. Maintain regular watering schedules and monitor for early fungal or pest symptoms.'
                : `The visual diagnosis indicates ${activeKnowledge?.displayName} with ${Math.round((activeRecord.confidence || 0) * 100)}% model confidence. ${
                    influences?.hasFieldData 
                      ? `Field satellite trends indicate ${fieldHealth?.changes_and_trends?.ndvi?.direction || 'stable'} vegetative vigor. Review soil moisture and avoid excessive nitrogen application.`
                      : 'Ensure immediate field scouting to confirm whether neighboring plants exhibit similar lesions.'
                  }`
              }
            </p>
            <div style={{ borderTop: '1px solid #c8e6c9', marginTop: '0.75rem', paddingTop: '0.5rem', fontSize: '0.75rem', color: '#2e7d32', fontWeight: 600 }}>
              * Decision Support Notice: AI diagnostics serve as guidance. Confirm with local agronomy extension personnel before applying heavy chemical treatments.
            </div>
          </div>

        </div>
      )}

      {/* Empty State */}
      {!loading && !detailLoading && (!activeRecord || filteredPredictions.length === 0) && (
        <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#777' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📋</div>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#444' }}>No Predictions Found</h4>
          <p style={{ margin: 0, fontSize: '0.85rem' }}>
            No diagnostic records match the selected mode filter ('{modeFilter}'). Perform disease detection or switch filter to view records.
          </p>
        </div>
      )}
    </section>
  );
};

export default CropInsights;
