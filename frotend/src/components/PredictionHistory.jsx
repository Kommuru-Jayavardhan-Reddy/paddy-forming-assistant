import React, { useState, useEffect, useCallback } from 'react';
import { getPredictions, getPredictionById, generateReport } from '../api/client';

const PredictionHistory = ({ onReportGenerated }) => {
  const [predictions, setPredictions] = useState([]);
  const [totalPredictions, setTotalPredictions] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Filters
  const [modeFilter, setModeFilter] = useState('all'); // 'all' | 'image_only' | 'multimodal'
  const [diseaseFilter, setDiseaseFilter] = useState('all');

  // Loading & Error states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Detail Modal State
  const [selectedPrediction, setSelectedPrediction] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // Quick Report Generation State inside detail view
  const [generatingReport, setGeneratingReport] = useState(false);
  const [generationFeedback, setGenerationFeedback] = useState(null);

  const loadPredictions = useCallback(async (page, mode, disease) => {
    setLoading(true);
    setError(null);
    try {
      const filters = {
        page,
        pageSize,
      };
      if (mode !== 'all') filters.predictionMode = mode;
      if (disease !== 'all') filters.disease = disease;

      const data = await getPredictions(filters);
      setPredictions(data.predictions || []);
      setTotalPredictions(data.total_predictions || 0);
    } catch (err) {
      console.error('Failed to load predictions:', err);
      setError(err instanceof Error ? err.message : 'Unable to connect to prediction history service.');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    loadPredictions(currentPage, modeFilter, diseaseFilter);
  }, [currentPage, modeFilter, diseaseFilter, loadPredictions]);

  const handleOpenDetail = async (id) => {
    setDetailLoading(true);
    setDetailError(null);
    setGenerationFeedback(null);
    try {
      const detail = await getPredictionById(id);
      setSelectedPrediction(detail);
    } catch (err) {
      console.error('Failed to load prediction detail:', err);
      setDetailError(err instanceof Error ? err.message : 'Failed to retrieve detailed prediction log.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedPrediction(null);
    setDetailError(null);
    setGenerationFeedback(null);
  };

  const handleGenerateReportFromDetail = async (predictionId) => {
    if (generatingReport) return;
    setGeneratingReport(true);
    setGenerationFeedback(null);
    try {
      const report = await generateReport(predictionId, { fileFormat: 'pdf', forceRegenerate: false });
      setGenerationFeedback({
        type: 'success',
        message: `Diagnostic report #${report.id.slice(0, 8)} compiled successfully (${report.file_format.toUpperCase()}, ${Math.round((report.file_size_bytes || 0) / 1024)} KB).`
      });
      if (onReportGenerated) {
        onReportGenerated(report);
      }
    } catch (err) {
      console.error('Report generation failed:', err);
      setGenerationFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Report compilation failed.'
      });
    } finally {
      setGeneratingReport(false);
    }
  };

  const totalPages = Math.ceil(totalPredictions / pageSize) || 1;

  const formatDisease = (d) => {
    if (!d) return '--';
    return d.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '--';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoStr;
    }
  };

  return (
    <section className="dashboard-section" style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.35rem', color: 'var(--text-primary)' }}>
            Diagnosis History & Inference Logs
          </h3>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Immutable classification records persisted in PostgreSQL ({totalPredictions} total inferences)
          </span>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Mode Selector */}
          <select
            value={modeFilter}
            onChange={(e) => { setModeFilter(e.target.value); setCurrentPage(1); }}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontSize: '0.85rem',
              backgroundColor: '#fff',
              color: '#333'
            }}
          >
            <option value="all">All Modes</option>
            <option value="image_only">Image-Only (EfficientNet-B4)</option>
            <option value="multimodal">Multimodal (Cross-Attention)</option>
          </select>

          {/* Disease Selector */}
          <select
            value={diseaseFilter}
            onChange={(e) => { setDiseaseFilter(e.target.value); setCurrentPage(1); }}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontSize: '0.85rem',
              backgroundColor: '#fff',
              color: '#333'
            }}
          >
            <option value="all">All Diagnoses</option>
            <option value="normal">Normal (Healthy)</option>
            <option value="tungro">Tungro</option>
            <option value="blast">Blast</option>
            <option value="bacterial_leaf_blight">Bacterial Leaf Blight</option>
            <option value="sheath_blight">Sheath Blight</option>
            <option value="brown_spot">Brown Spot</option>
          </select>

          <button
            onClick={() => loadPredictions(currentPage, modeFilter, diseaseFilter)}
            className="btn"
            style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
            title="Refresh history"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div style={{ padding: '2.5rem', textAlign: 'center', color: '#666' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem auto' }}></div>
          <span>Loading historical predictions from PostgreSQL database...</span>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div style={{ padding: '1.5rem', backgroundColor: '#fde8e8', color: '#9b1c1c', borderRadius: '8px', marginBottom: '1.5rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Error Loading History</div>
          <div style={{ fontSize: '0.85rem' }}>{error}</div>
          <button
            onClick={() => loadPredictions(currentPage, modeFilter, diseaseFilter)}
            style={{ marginTop: '0.75rem', padding: '0.4rem 0.8rem', backgroundColor: '#9b1c1c', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && predictions.length === 0 && (
        <div style={{ padding: '3rem 1.5rem', textAlign: 'center', backgroundColor: '#fafafa', borderRadius: '12px', border: '1px dashed #ccc' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📋</div>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#444' }}>No Prediction Records Found</h4>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
            No inferences match the selected filters. Use the Disease Detection module above to diagnose a paddy leaf.
          </p>
        </div>
      )}

      {/* Predictions Table / Cards List */}
      {!loading && !error && predictions.length > 0 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e0e0e0', overflow: 'hidden', boxShadow: '0 2px 6px rgba(0,0,0,0.03)' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#f7f9f8', borderBottom: '1px solid #e2ece6', color: '#4a5568' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>Prediction ID</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Timestamp</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Diagnosis</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Confidence</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Mode</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Health Status</th>
                  <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => {
                  const isHealthy = p.is_healthy || p.predicted_disease === 'normal';
                  return (
                    <tr
                      key={p.id}
                      style={{ borderBottom: '1px solid #edf2f7', transition: 'background-color 0.15s ease' }}
                      onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#fbfdfc'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#ffffff'; }}
                    >
                      {/* Prediction ID */}
                      <td style={{ padding: '0.75rem 1rem', fontFamily: 'monospace', fontSize: '0.8rem', color: '#4a5568' }}>
                        {p.id.slice(0, 8)}...
                      </td>

                      {/* Date */}
                      <td style={{ padding: '0.75rem 1rem', color: '#2d3748', whiteSpace: 'nowrap' }}>
                        {formatDate(p.created_at)}
                      </td>

                      {/* Disease */}
                      <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: isHealthy ? '#0d5c38' : '#b91c1c' }}>
                        {formatDisease(p.predicted_disease)}
                      </td>

                      {/* Confidence */}
                      <td style={{ padding: '0.75rem 1rem', color: '#2d3748', fontWeight: 600 }}>
                        {p.confidence !== null && p.confidence !== undefined ? `${(p.confidence * 100).toFixed(1)}%` : '--'}
                      </td>

                      {/* Mode Badge */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '12px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          backgroundColor: p.prediction_mode === 'multimodal' ? '#e0f2fe' : '#ede9fe',
                          color: p.prediction_mode === 'multimodal' ? '#0369a1' : '#6d28d9'
                        }}>
                          {p.prediction_mode === 'multimodal' ? 'Multimodal' : 'Image-Only'}
                        </span>
                      </td>

                      {/* Health Status */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '12px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          backgroundColor: isHealthy ? '#d1fae5' : '#fee2e2',
                          color: isHealthy ? '#065f46' : '#991b1b'
                        }}>
                          {isHealthy ? 'Healthy' : 'Diseased'}
                        </span>
                      </td>

                      {/* Details Button */}
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                        <button
                          onClick={() => handleOpenDetail(p.id)}
                          style={{
                            padding: '0.3rem 0.6rem',
                            backgroundColor: '#f0fdf4',
                            border: '1px solid #bbf7d0',
                            borderRadius: '6px',
                            color: '#166534',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          View Details →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1.25rem', backgroundColor: '#fbfcfb', borderTop: '1px solid #e2ece6' }}>
            <span style={{ fontSize: '0.8rem', color: '#718096' }}>
              Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalPredictions)} of {totalPredictions} records
            </span>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                style={{
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  backgroundColor: currentPage === 1 ? '#f1f5f9' : '#ffffff',
                  color: currentPage === 1 ? '#94a3b8' : '#334155',
                  fontSize: '0.8rem',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                }}
              >
                ← Previous
              </button>
              <span style={{ fontSize: '0.8rem', color: '#475569', fontWeight: 600, padding: '0 0.5rem' }}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage >= totalPages}
                style={{
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  backgroundColor: currentPage >= totalPages ? '#f1f5f9' : '#ffffff',
                  color: currentPage >= totalPages ? '#94a3b8' : '#334155',
                  fontSize: '0.8rem',
                  cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer'
                }}
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DETAIL VIEW MODAL */}
      {(selectedPrediction || detailLoading) && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '1rem'
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '650px',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '1.75rem',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)',
            border: '1px solid #e2ece6'
          }}>
            {detailLoading && (
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div className="spinner" style={{ margin: '0 auto 1rem auto' }}></div>
                <span>Fetching authentic inference log from PostgreSQL...</span>
              </div>
            )}

            {detailError && (
              <div>
                <h4 style={{ color: '#b91c1c' }}>Error Loading Details</h4>
                <p style={{ fontSize: '0.85rem', color: '#666' }}>{detailError}</p>
                <button onClick={handleCloseDetail} className="btn" style={{ marginTop: '1rem' }}>Close</button>
              </div>
            )}

            {selectedPrediction && !detailLoading && (
              <div>
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', borderBottom: '1px solid #edf2f7', paddingBottom: '1rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#718096', fontWeight: 600 }}>Diagnostic Log</span>
                    <h3 style={{ margin: '0.2rem 0', color: '#1a3826', fontSize: '1.3rem' }}>
                      {formatDisease(selectedPrediction.predicted_disease)}
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                      UUID: {selectedPrediction.id}
                    </span>
                  </div>
                  <button
                    onClick={handleCloseDetail}
                    style={{ background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#94a3b8' }}
                  >
                    ×
                  </button>
                </div>

                {/* Key Metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
                  <div style={{ background: '#f8faf9', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2ece6' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Confidence</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0d5c38' }}>
                      {(selectedPrediction.confidence * 100).toFixed(1)}%
                    </div>
                  </div>

                  <div style={{ background: '#f8faf9', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2ece6' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Mode</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#2d3748', marginTop: '0.25rem' }}>
                      {selectedPrediction.prediction_mode === 'multimodal' ? 'Multimodal' : 'Image Only'}
                    </div>
                  </div>

                  <div style={{ background: '#f8faf9', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2ece6' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Model</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#2d3748', marginTop: '0.25rem' }}>
                      {selectedPrediction.model_name || 'EfficientNet-B4'}
                    </div>
                  </div>

                  <div style={{ background: '#f8faf9', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2ece6' }}>
                    <div style={{ fontSize: '0.7rem', color: '#666', textTransform: 'uppercase', fontWeight: 600 }}>Latency</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#4a5568', marginTop: '0.25rem' }}>
                      {selectedPrediction.inference_latency_ms !== null ? `${Math.round(selectedPrediction.inference_latency_ms)} ms` : '--'}
                    </div>
                  </div>
                </div>

                {/* Top-3 Candidates */}
                {selectedPrediction.top_k_predictions && selectedPrediction.top_k_predictions.length > 0 && (
                  <div style={{ marginBottom: '1.25rem' }}>
                    <h5 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#4a5568' }}>Top Ranking Disease Candidates:</h5>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {selectedPrediction.top_k_predictions.map((cand, idx) => {
                        const prob = cand.probability || 0;
                        return (
                          <div key={idx} style={{ background: '#fbfcfb', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid #e2ece6' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                              <span>{formatDisease(cand.disease)}</span>
                              <span>{(prob * 100).toFixed(1)}%</span>
                            </div>
                            <div style={{ width: '100%', height: '6px', backgroundColor: '#e2ece6', borderRadius: '3px', overflow: 'hidden' }}>
                              <div style={{ width: `${prob * 100}%`, height: '100%', backgroundColor: idx === 0 ? '#0d5c38' : '#a0aec0', borderRadius: '3px' }}></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Multimodal Attention Weights (if available) */}
                {selectedPrediction.attention_weights && selectedPrediction.attention_weights.length > 0 && (
                  <div style={{ marginBottom: '1.25rem' }}>
                    <h5 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: '#0369a1' }}>
                      Cross-Attention Satellite Weights (10 Timesteps):
                    </h5>
                    <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '60px', padding: '0.5rem', backgroundColor: '#f0f9ff', borderRadius: '6px', border: '1px solid #bae6fd' }}>
                      {selectedPrediction.attention_weights.map((w, idx) => {
                        const maxW = Math.max(...selectedPrediction.attention_weights);
                        const heightPct = maxW > 0 ? (w / maxW) * 100 : 10;
                        return (
                          <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            <div
                              style={{ width: '100%', height: `${Math.max(heightPct, 8)}%`, backgroundColor: '#0284c7', borderRadius: '2px' }}
                              title={`T${idx + 1}: ${(w * 100).toFixed(1)}% weight`}
                            ></div>
                            <span style={{ fontSize: '0.6rem', color: '#0369a1', marginTop: '2px' }}>T{idx + 1}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Additional Info */}
                <div style={{ fontSize: '0.75rem', color: '#718096', marginBottom: '1.25rem', backgroundColor: '#f8fafc', padding: '0.75rem', borderRadius: '8px' }}>
                  <div><strong>Device:</strong> {selectedPrediction.device || 'CPU'}</div>
                  {selectedPrediction.field_id && <div><strong>Associated Field:</strong> {selectedPrediction.field_id}</div>}
                  {selectedPrediction.image_sha256 && <div><strong>Image SHA-256:</strong> {selectedPrediction.image_sha256.slice(0, 16)}...</div>}
                </div>

                {/* Feedback Banner */}
                {generationFeedback && (
                  <div style={{
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    marginBottom: '1rem',
                    backgroundColor: generationFeedback.type === 'success' ? '#f0fdf4' : '#fef2f2',
                    color: generationFeedback.type === 'success' ? '#166534' : '#991b1b',
                    border: `1px solid ${generationFeedback.type === 'success' ? '#bbf7d0' : '#fecaca'}`
                  }}>
                    {generationFeedback.message}
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid #edf2f7', paddingTop: '1rem' }}>
                  <button
                    onClick={handleCloseDetail}
                    className="btn"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                  >
                    Close
                  </button>
                  <button
                    onClick={() => handleGenerateReportFromDetail(selectedPrediction.id)}
                    disabled={generatingReport}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: generatingReport ? '#6b7280' : '#0d5c38',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      cursor: generatingReport ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {generatingReport ? 'Generating PDF...' : '📄 Generate Official Report'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default PredictionHistory;
