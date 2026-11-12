import React, { useState, useEffect, useCallback } from 'react';
import { getReports, getReportById, generateReport, downloadReportPdf, getPredictions } from '../api/client';

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [totalReports, setTotalReports] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Filters
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  // Loading & Error States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Report Generation Form State
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [selectedPredictionId, setSelectedPredictionId] = useState('');
  const [customPredictionInput, setCustomPredictionInput] = useState('');
  const [generationFormat, setGenerationFormat] = useState('pdf');
  const [forceRegenerate, setForceRegenerate] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);
  const [generationSuccess, setGenerationSuccess] = useState(null);

  // Report Download State
  const [downloadingReportId, setDownloadingReportId] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  // Report Detail Modal
  const [selectedReport, setSelectedReport] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Load Reports
  const loadReports = useCallback(async (page, type, status) => {
    setLoading(true);
    setError(null);
    try {
      const filters = {
        page,
        pageSize,
      };
      if (type !== 'all') filters.reportType = type;
      if (status !== 'all') filters.status = status;

      const data = await getReports(filters);
      setReports(data.reports || []);
      setTotalReports(data.total_reports || 0);
    } catch (err) {
      console.error('Failed to load reports:', err);
      setError(err instanceof Error ? err.message : 'Unable to retrieve reports from backend.');
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    loadReports(currentPage, typeFilter, statusFilter);
  }, [currentPage, typeFilter, statusFilter, loadReports]);

  // Load Recent Predictions for Generator dropdown
  useEffect(() => {
    let isMounted = true;
    getPredictions({ pageSize: 20 })
      .then(res => {
        if (!isMounted) return;
        const list = res.predictions || [];
        setRecentPredictions(list);
        if (list.length > 0) {
          setSelectedPredictionId(list[0].id);
        }
      })
      .catch(err => {
        console.warn('Could not load predictions for generator dropdown:', err);
      });
    return () => { isMounted = false; };
  }, []);

  // Handle PDF Download
  const handleDownloadPdf = async (report) => {
    if (downloadingReportId) return; // Prevent concurrent downloads
    setDownloadingReportId(report.id);
    setDownloadError(null);

    try {
      const { blob, filename } = await downloadReportPdf(report.id, false);
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename || `paddy_report_${report.id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      // Revoke temporary browser object URL
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Failed to download report PDF:', err);
      setDownloadError(err instanceof Error ? err.message : 'Failed to download report PDF.');
    } finally {
      setDownloadingReportId(null);
    }
  };

  // Handle Generate New Report
  const handleGenerate = async (e) => {
    e.preventDefault();
    const targetPredictionId = (customPredictionInput.trim() || selectedPredictionId || '').trim();
    if (!targetPredictionId) {
      setGenerationError('Please select or enter a valid prediction ID.');
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);
    setGenerationSuccess(null);

    try {
      const result = await generateReport(targetPredictionId, {
        fileFormat: generationFormat,
        forceRegenerate: forceRegenerate,
      });

      setGenerationSuccess(`Report compiled successfully: "${result.title}" (#${result.id.slice(0, 8)}).`);
      // Refresh reports list
      loadReports(currentPage, typeFilter, statusFilter);
      setTimeout(() => {
        setShowGenerateModal(false);
        setGenerationSuccess(null);
      }, 2000);
    } catch (err) {
      console.error('Report compilation error:', err);
      setGenerationError(err instanceof Error ? err.message : 'Report generation failed.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Handle View Detail
  const handleViewDetail = async (reportId) => {
    setDetailLoading(true);
    try {
      const detail = await getReportById(reportId);
      setSelectedReport(detail);
    } catch (err) {
      console.error('Failed to load report detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const totalPages = Math.ceil(totalReports / pageSize) || 1;

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

  const formatReportType = (t) => {
    switch (t) {
      case 'disease_diagnostic': return 'Disease Diagnostic';
      case 'field_health_summary': return 'Field Health Summary';
      case 'seasonal_advisory': return 'Seasonal Advisory';
      case 'market_intelligence': return 'Market Intelligence';
      default: return t ? t.replace(/_/g, ' ') : 'Report';
    }
  };

  return (
    <section className="dashboard-section" style={{ marginTop: '2.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.35rem', color: 'var(--text-primary)' }}>
            Official Farming Advisory Reports & PDFs
          </h3>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Archived diagnostic documents, agronomic advisories, and certified PDF downloads ({totalReports} total reports)
          </span>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setCurrentPage(1); }}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontSize: '0.85rem',
              backgroundColor: '#fff',
              color: '#333'
            }}
          >
            <option value="all">All Report Types</option>
            <option value="disease_diagnostic">Disease Diagnostic</option>
            <option value="field_health_summary">Field Health Summary</option>
            <option value="seasonal_advisory">Seasonal Advisory</option>
            <option value="market_intelligence">Market Intelligence</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontSize: '0.85rem',
              backgroundColor: '#fff',
              color: '#333'
            }}
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="generating">Generating</option>
            <option value="failed">Failed</option>
          </select>

          {/* Generate Report Button */}
          <button
            onClick={() => { setShowGenerateModal(true); setGenerationError(null); setGenerationSuccess(null); }}
            style={{
              padding: '0.4rem 0.9rem',
              backgroundColor: '#0d5c38',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}
          >
            + Generate Report
          </button>

          <button
            onClick={() => loadReports(currentPage, typeFilter, statusFilter)}
            className="btn"
            style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
            title="Refresh reports list"
          >
            ↻
          </button>
        </div>
      </div>

      {/* Global Download Error Banner */}
      {downloadError && (
        <div style={{ padding: '0.75rem 1rem', backgroundColor: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem' }}>
          <strong>Download Error:</strong> {downloadError}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ padding: '2.5rem', textAlign: 'center', color: '#666' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem auto' }}></div>
          <span>Loading official report archives from PostgreSQL database...</span>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div style={{ padding: '1.5rem', backgroundColor: '#fde8e8', color: '#9b1c1c', borderRadius: '8px', marginBottom: '1.5rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Failed to Load Reports</div>
          <div style={{ fontSize: '0.85rem' }}>{error}</div>
          <button
            onClick={() => loadReports(currentPage, typeFilter, statusFilter)}
            style={{ marginTop: '0.75rem', padding: '0.4rem 0.8rem', backgroundColor: '#9b1c1c', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && reports.length === 0 && (
        <div style={{ padding: '3rem 1.5rem', textAlign: 'center', backgroundColor: '#fafafa', borderRadius: '12px', border: '1px dashed #ccc' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📄</div>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#444' }}>No Reports Found</h4>
          <p style={{ margin: '0 0 1rem 0', fontSize: '0.85rem', color: '#666' }}>
            No diagnostic or agronomic reports have been compiled yet for the selected criteria.
          </p>
          <button
            onClick={() => setShowGenerateModal(true)}
            style={{ padding: '0.5rem 1rem', backgroundColor: '#0d5c38', color: '#ffffff', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}
          >
            Generate First Report
          </button>
        </div>
      )}

      {/* Reports Table */}
      {!loading && !error && reports.length > 0 && (
        <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #e0e0e0', overflow: 'hidden', boxShadow: '0 2px 6px rgba(0,0,0,0.03)' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#f7f9f8', borderBottom: '1px solid #e2ece6', color: '#4a5568' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>Report Title & ID</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Category</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Created At</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Format</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Size</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Status</th>
                  <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => {
                  const isPdf = r.file_format === 'pdf';
                  const isCompleted = r.status === 'completed';
                  const isDownloading = downloadingReportId === r.id;

                  return (
                    <tr
                      key={r.id}
                      style={{ borderBottom: '1px solid #edf2f7', transition: 'background-color 0.15s ease' }}
                      onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#fbfdfc'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#ffffff'; }}
                    >
                      {/* Title & ID */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ fontWeight: 600, color: '#1a3826' }}>{r.title}</div>
                        <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#94a3b8' }}>
                          ID: {r.id.slice(0, 8)}... | Pred: {r.prediction_id ? r.prediction_id.slice(0, 8) + '...' : 'N/A'}
                        </div>
                      </td>

                      {/* Category */}
                      <td style={{ padding: '0.75rem 1rem', color: '#4a5568' }}>
                        {formatReportType(r.report_type)}
                      </td>

                      {/* Created At */}
                      <td style={{ padding: '0.75rem 1rem', color: '#4a5568', whiteSpace: 'nowrap' }}>
                        {formatDate(r.created_at)}
                      </td>

                      {/* Format */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '0.15rem 0.5rem',
                          borderRadius: '6px',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          backgroundColor: isPdf ? '#fee2e2' : '#e0e7ff',
                          color: isPdf ? '#b91c1c' : '#4338ca'
                        }}>
                          {r.file_format.toUpperCase()}
                        </span>
                      </td>

                      {/* Size */}
                      <td style={{ padding: '0.75rem 1rem', color: '#64748b', fontSize: '0.8rem' }}>
                        {r.file_size_bytes !== null && r.file_size_bytes !== undefined
                          ? `${Math.round(r.file_size_bytes / 1024)} KB`
                          : '--'}
                      </td>

                      {/* Status */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <span style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '12px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          backgroundColor: isCompleted ? '#d1fae5' : '#fef3c7',
                          color: isCompleted ? '#065f46' : '#92400e'
                        }}>
                          {r.status}
                        </span>
                      </td>

                      {/* Action Buttons */}
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                          <button
                            onClick={() => handleViewDetail(r.id)}
                            style={{
                              padding: '0.3rem 0.6rem',
                              backgroundColor: '#f1f5f9',
                              border: '1px solid #cbd5e1',
                              borderRadius: '6px',
                              color: '#334155',
                              fontSize: '0.75rem',
                              cursor: 'pointer'
                            }}
                            title="View Summary & Metadata"
                          >
                            Details
                          </button>

                          {isPdf && isCompleted ? (
                            <button
                              onClick={() => handleDownloadPdf(r)}
                              disabled={isDownloading}
                              style={{
                                padding: '0.3rem 0.6rem',
                                backgroundColor: isDownloading ? '#9ca3af' : '#0d5c38',
                                border: 'none',
                                borderRadius: '6px',
                                color: '#ffffff',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                cursor: isDownloading ? 'not-allowed' : 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.3rem'
                              }}
                              title="Download PDF Artifact"
                            >
                              {isDownloading ? 'Downloading...' : '⬇ PDF'}
                            </button>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic', alignSelf: 'center' }}>
                              No file
                            </span>
                          )}
                        </div>
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
              Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalReports)} of {totalReports} reports
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

      {/* GENERATE NEW REPORT MODAL */}
      {showGenerateModal && (
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
            maxWidth: '550px',
            padding: '1.75rem',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)',
            border: '1px solid #e2ece6'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid #edf2f7', paddingBottom: '0.75rem' }}>
              <h3 style={{ margin: 0, color: '#1a3826', fontSize: '1.2rem' }}>
                Generate Diagnostic Report
              </h3>
              <button
                onClick={() => setShowGenerateModal(false)}
                style={{ background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#94a3b8' }}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleGenerate}>
              {/* Prediction Selection */}
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
                  Select Existing Diagnostic Prediction:
                </label>
                <select
                  value={selectedPredictionId}
                  onChange={(e) => { setSelectedPredictionId(e.target.value); setCustomPredictionInput(''); }}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
                >
                  {recentPredictions.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.predicted_disease.toUpperCase()} ({(p.confidence * 100).toFixed(0)}%) - {p.id.slice(0, 8)}... - {formatDate(p.created_at)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Or Manual UUID input */}
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>
                  Or enter specific Prediction UUID:
                </label>
                <input
                  type="text"
                  placeholder="e.g. 04dd0f48-859a-4a9d-8cc0-f58385b07ef0"
                  value={customPredictionInput}
                  onChange={(e) => setCustomPredictionInput(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.8rem', fontFamily: 'monospace' }}
                />
              </div>

              {/* Format Selection */}
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '0.35rem' }}>
                  Target Document Format:
                </label>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="format"
                      value="pdf"
                      checked={generationFormat === 'pdf'}
                      onChange={() => setGenerationFormat('pdf')}
                    />
                    Official Printable PDF
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="format"
                      value="json"
                      checked={generationFormat === 'json'}
                      onChange={() => setGenerationFormat('json')}
                    />
                    Structured JSON Record
                  </label>
                </div>
              </div>

              {/* Force Regenerate Toggle */}
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: '#475569', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={forceRegenerate}
                    onChange={(e) => setForceRegenerate(e.target.checked)}
                  />
                  Force compilation of fresh report artifact if one already exists
                </label>
              </div>

              {/* Error feedback */}
              {generationError && (
                <div style={{ padding: '0.6rem 0.8rem', backgroundColor: '#fef2f2', color: '#991b1b', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {generationError}
                </div>
              )}

              {/* Success feedback */}
              {generationSuccess && (
                <div style={{ padding: '0.6rem 0.8rem', backgroundColor: '#f0fdf4', color: '#166534', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '1rem' }}>
                  {generationSuccess}
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="btn"
                  style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  style={{
                    padding: '0.5rem 1.25rem',
                    backgroundColor: isGenerating ? '#9ca3af' : '#0d5c38',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: isGenerating ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem'
                  }}
                >
                  {isGenerating ? 'Compiling Report...' : 'Compile Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REPORT DETAIL MODAL */}
      {(selectedReport || detailLoading) && (
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
            maxWidth: '600px',
            maxHeight: '90vh',
            overflowY: 'auto',
            padding: '1.75rem',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)',
            border: '1px solid #e2ece6'
          }}>
            {detailLoading && (
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div className="spinner" style={{ margin: '0 auto 1rem auto' }}></div>
                <span>Loading report details from PostgreSQL...</span>
              </div>
            )}

            {selectedReport && !detailLoading && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', borderBottom: '1px solid #edf2f7', paddingBottom: '1rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#718096', fontWeight: 600 }}>
                      {formatReportType(selectedReport.report_type)}
                    </span>
                    <h3 style={{ margin: '0.2rem 0', color: '#1a3826', fontSize: '1.3rem' }}>
                      {selectedReport.title}
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace' }}>
                      Report UUID: {selectedReport.id}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedReport(null)}
                    style={{ background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#94a3b8' }}
                  >
                    ×
                  </button>
                </div>

                {/* Summary Box */}
                {selectedReport.summary && (
                  <div style={{ background: '#f8faf9', padding: '1rem', borderRadius: '8px', border: '1px solid #e2ece6', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0d5c38', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                      Executive Summary & Findings
                    </div>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: '#334155', lineHeight: 1.5 }}>
                      {selectedReport.summary}
                    </p>
                  </div>
                )}

                {/* Document Metadata */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', fontSize: '0.8rem', color: '#475569', marginBottom: '1rem' }}>
                  <div><strong>Status:</strong> {selectedReport.status}</div>
                  <div><strong>Format:</strong> {selectedReport.file_format.toUpperCase()}</div>
                  <div><strong>Generated By:</strong> {selectedReport.generated_by}</div>
                  <div><strong>Date:</strong> {formatDate(selectedReport.created_at)}</div>
                  {selectedReport.prediction_id && <div><strong>Prediction ID:</strong> {selectedReport.prediction_id.slice(0, 8)}...</div>}
                  {selectedReport.file_size_bytes && <div><strong>Artifact Size:</strong> {Math.round(selectedReport.file_size_bytes / 1024)} KB</div>}
                </div>

                {/* Report Metadata Details if available */}
                {selectedReport.report_metadata && (
                  <div style={{ background: '#fafafa', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '0.75rem', color: '#6b7280', maxHeight: '180px', overflowY: 'auto', marginBottom: '1.25rem' }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: '#374151' }}>Metadata & Agronomic Parameters:</div>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                      {JSON.stringify(selectedReport.report_metadata, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid #edf2f7', paddingTop: '1rem' }}>
                  <button
                    onClick={() => setSelectedReport(null)}
                    className="btn"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                  >
                    Close
                  </button>
                  {selectedReport.file_format === 'pdf' && selectedReport.status === 'completed' && (
                    <button
                      onClick={() => handleDownloadPdf(selectedReport)}
                      disabled={downloadingReportId === selectedReport.id}
                      style={{
                        padding: '0.5rem 1.25rem',
                        backgroundColor: downloadingReportId === selectedReport.id ? '#9ca3af' : '#0d5c38',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '8px',
                        fontWeight: 600,
                        fontSize: '0.85rem',
                        cursor: downloadingReportId === selectedReport.id ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {downloadingReportId === selectedReport.id ? 'Downloading...' : '⬇ Download Official PDF'}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default Reports;
