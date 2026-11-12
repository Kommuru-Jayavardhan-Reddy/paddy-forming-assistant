import React, { useState, useRef, useCallback } from 'react';
import { predict } from '../api/client';
import { API_BASE_URL } from '../api/config';

/**
 * Knowledge base for the 13 paddy leaf disease classes.
 * Provides scientifically accurate agricultural descriptions and recommended actions.
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

const formatClassName = (name) => {
  if (!name) return 'Unknown';
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const DiseaseDetection = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef(null);

  // Validate file format and size
  const validateFile = (file) => {
    if (!file) {
      return { valid: false, message: 'No file selected. Please choose a leaf image.' };
    }

    const validExtensions = /\.(jpe?g|png|webp)$/i;
    const validMimes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];

    if (!validMimes.includes(file.type) && !validExtensions.test(file.name)) {
      return {
        valid: false,
        message: `File format "${file.name.split('.').pop()}" is not supported. Please upload a JPG, JPEG, PNG, or WebP image.`
      };
    }

    if (file.size === 0) {
      return {
        valid: false,
        message: 'The selected image file is empty (0 bytes). Please select a valid photo.'
      };
    }

    // 10 MB limit
    if (file.size > 10 * 1024 * 1024) {
      return {
        valid: false,
        message: `Image file size (${formatFileSize(file.size)}) exceeds the maximum 10 MB limit.`
      };
    }

    return { valid: true };
  };

  const handleFileSelection = (file) => {
    setError(null);
    setPrediction(null);

    const validation = validateFile(file);
    if (!validation.valid) {
      setError({
        title: 'Invalid Image File',
        message: validation.message,
        isRetryable: false
      });
      return;
    }

    setSelectedFile(file);

    // Create object URL for instant preview
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const onFileInputChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      handleFileSelection(file);
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const onDragLeave = () => {
    setIsDragOver(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) {
      handleFileSelection(file);
    }
  };

  // Perform genuine inference via centralized API client
  const runInference = useCallback(async () => {
    if (isAnalyzing || !selectedFile) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const res = await predict({ image: selectedFile });
      setPrediction(res);
    } catch (err) {
      console.error('Disease prediction error:', err);
      const rawMessage = err instanceof Error ? err.message : 'Inference request failed.';
      
      // Sanitize against private file paths or secrets
      const sanitized = rawMessage
        .replace(/[A-Za-z]:\\[^"'\n\r\t<>]*/g, '[internal path]')
        .replace(/\/[\w.-]+(\/[\w.-]+)+/g, '[internal path]');

      setError({
        title: 'Prediction Failed',
        message: sanitized,
        isRetryable: true
      });
    } finally {
      setIsAnalyzing(false);
    }
  }, [isAnalyzing, selectedFile]);

  // Reset to initial state for new leaf
  const handleReset = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setPrediction(null);
    setError(null);
    setIsAnalyzing(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Get agricultural knowledge info for prediction
  const diseaseInfo = prediction ? (DISEASE_KNOWLEDGE_BASE[prediction.disease] || {
    displayName: formatClassName(prediction.disease),
    badgeType: prediction.disease === 'normal' ? 'healthy' : 'attention',
    badgeText: prediction.disease === 'normal' ? 'Healthy' : 'Needs Attention',
    symptoms: `Observed leaf abnormalities consistent with ${formatClassName(prediction.disease)}.`,
    action: 'Consult local agricultural extension specialists for tailored field intervention advice.'
  }) : null;

  const confidencePercent = prediction
    ? (prediction.confidence <= 1.0 ? prediction.confidence * 100 : prediction.confidence)
    : 0;

  const confidenceLabel = confidencePercent >= 80 ? 'High Confidence' : (confidencePercent >= 50 ? 'Moderate Confidence' : 'Low Confidence');

  return (
    <div className="glass-panel" style={{ width: '100%', marginBottom: '1.5rem', padding: '1.5rem', borderRadius: '16px' }}>
      {/* Component Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: 'var(--brand-primary, #0d5c38)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>🌿</span> Paddy Disease Detection
          </h3>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary, #64748b)' }}>
            Real-time EfficientNet-B4 AI visual diagnostic for rice leaf disorders
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.25rem 0.65rem',
            borderRadius: '9999px',
            fontSize: '0.725rem',
            fontWeight: 600,
            background: 'rgba(16, 185, 129, 0.1)',
            color: '#065f46',
            border: '1px solid rgba(16, 185, 129, 0.25)'
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
            Model: EfficientNet-B4 (CPU)
          </span>
        </div>
      </div>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={onFileInputChange}
        accept="image/jpeg,image/png,image/jpg,image/webp"
        style={{ display: 'none' }}
        id="react-leaf-file-input"
      />

      {/* 1. INITIAL UPLOAD / DROP ZONE (Visible when no image selected) */}
      {!selectedFile && (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
          style={{
            border: isDragOver ? '2px dashed var(--brand-primary, #0d5c38)' : '2px dashed rgba(13, 92, 56, 0.25)',
            background: isDragOver ? 'rgba(13, 92, 56, 0.05)' : 'rgba(255, 255, 255, 0.6)',
            borderRadius: '12px',
            padding: '2.5rem 1.5rem',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem'
          }}
        >
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'rgba(13, 92, 56, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.75rem'
          }}>
            📷
          </div>
          <div>
            <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '1.05rem', fontWeight: 600, color: 'var(--brand-primary, #0d5c38)' }}>
              Upload or Drag & Drop Paddy Leaf Photo
            </h4>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary, #64748b)' }}>
              Click anywhere to browse or drag an image here
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center', marginTop: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.04)', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#64748b' }}>
              JPG, PNG, WebP
            </span>
            <span style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.04)', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#64748b' }}>
              Max 10 MB
            </span>
            <span style={{ fontSize: '0.75rem', background: 'rgba(0,0,0,0.04)', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#64748b' }}>
              Clear closeup in daylight
            </span>
          </div>
        </div>
      )}

      {/* 2. IMAGE PREVIEW & INFERENCE CONTROLS */}
      {selectedFile && !prediction && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: '1.25rem',
            background: 'rgba(255, 255, 255, 0.8)',
            border: '1px solid rgba(13, 92, 56, 0.15)',
            borderRadius: '12px',
            padding: '1rem',
            flexWrap: 'wrap'
          }}>
            {previewUrl && (
              <img
                src={previewUrl}
                alt="Selected Leaf Preview"
                style={{
                  width: '120px',
                  height: '120px',
                  objectFit: 'cover',
                  borderRadius: '8px',
                  border: '1px solid rgba(0,0,0,0.1)',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
                }}
              />
            )}
            <div style={{ flex: '1 1 200px' }}>
              <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.975rem', fontWeight: 600, color: 'var(--text-primary, #0f172a)' }}>
                {selectedFile.name}
              </h4>
              <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.825rem', color: 'var(--text-secondary, #64748b)' }}>
                Size: {formatFileSize(selectedFile.size)} | Format: {selectedFile.type || 'Image'}
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={runInference}
                  disabled={isAnalyzing}
                  className="btn btn-primary"
                  style={{
                    padding: '0.5rem 1.25rem',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    opacity: isAnalyzing ? 0.7 : 1,
                    cursor: isAnalyzing ? 'not-allowed' : 'pointer'
                  }}
                  id="btn-react-predict"
                >
                  {isAnalyzing ? 'Running Inference...' : '✨ Run Disease Analysis'}
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={isAnalyzing}
                  className="btn"
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.875rem',
                    background: '#f1f5f9',
                    color: '#475569',
                    border: '1px solid #cbd5e1'
                  }}
                  id="btn-react-change-image"
                >
                  Change Image
                </button>
              </div>
            </div>
          </div>

          {/* Loading Indicator */}
          {isAnalyzing && (
            <div style={{
              padding: '1.5rem',
              textAlign: 'center',
              background: 'rgba(13, 92, 56, 0.04)',
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
                  Analyzing Paddy Leaf...
                </strong>
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-secondary, #64748b)' }}>
                  Running EfficientNet-B4 AI inference on CPU device...
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. ERROR ALERT STATE */}
      {error && (
        <div style={{
          marginTop: '1rem',
          padding: '1rem 1.25rem',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '10px',
          color: '#991b1b'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.25rem' }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <strong style={{ display: 'block', fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                {error.title}
              </strong>
              <p style={{ margin: 0, fontSize: '0.85rem', lineHeight: '1.4' }}>
                {error.message}
              </p>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                {error.isRetryable && selectedFile && (
                  <button
                    type="button"
                    onClick={runInference}
                    disabled={isAnalyzing}
                    className="btn"
                    style={{
                      padding: '0.35rem 0.85rem',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      background: '#991b1b',
                      color: '#ffffff'
                    }}
                    id="btn-react-error-retry"
                  >
                    Retry Analysis
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleReset}
                  className="btn"
                  style={{
                    padding: '0.35rem 0.85rem',
                    fontSize: '0.8rem',
                    background: '#ffffff',
                    color: '#991b1b',
                    border: '1px solid #fecaca'
                  }}
                  id="btn-react-error-select-another"
                >
                  Select Another Image
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. PREDICTION RESULT DISPLAY */}
      {prediction && diseaseInfo && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '0.5rem' }}>
          {/* Main Diagnostic Card */}
          <div style={{
            display: 'flex',
            gap: '1.25rem',
            background: '#ffffff',
            borderRadius: '12px',
            border: '1px solid rgba(13, 92, 56, 0.15)',
            padding: '1.25rem',
            flexWrap: 'wrap',
            boxShadow: '0 4px 12px rgba(0,0,0,0.03)'
          }}>
            {previewUrl && (
              <img
                src={previewUrl}
                alt="Analyzed Leaf"
                style={{
                  width: '140px',
                  height: '140px',
                  objectFit: 'cover',
                  borderRadius: '10px',
                  border: '1px solid #e2e8f0'
                }}
              />
            )}

            <div style={{ flex: '1 1 280px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary, #64748b)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Primary Detected Condition
                    </span>
                    <h3 style={{ margin: '0.15rem 0', fontSize: '1.45rem', fontWeight: 700, color: '#0f172a' }}>
                      {diseaseInfo.displayName}
                    </h3>
                  </div>

                  <span style={{
                    padding: '0.35rem 0.75rem',
                    borderRadius: '9999px',
                    fontSize: '0.775rem',
                    fontWeight: 700,
                    background: diseaseInfo.badgeType === 'healthy' ? '#dcfce7' : (diseaseInfo.badgeType === 'risk' ? '#fee2e2' : '#fef3c7'),
                    color: diseaseInfo.badgeType === 'healthy' ? '#166534' : (diseaseInfo.badgeType === 'risk' ? '#991b1b' : '#92400e'),
                    border: `1px solid ${diseaseInfo.badgeType === 'healthy' ? '#86efac' : (diseaseInfo.badgeType === 'risk' ? '#fca5a5' : '#fde68a')}`
                  }}>
                    {diseaseInfo.badgeText}
                  </span>
                </div>

                {/* Confidence Bar */}
                <div style={{ marginTop: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.825rem', marginBottom: '0.35rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--brand-primary, #0d5c38)' }}>
                      Confidence: {confidencePercent.toFixed(1)}%
                    </span>
                    <span style={{ color: '#64748b', fontSize: '0.775rem' }}>
                      {confidenceLabel}
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.min(100, Math.max(0, confidencePercent))}%`,
                      height: '100%',
                      background: diseaseInfo.badgeType === 'healthy' ? '#10b981' : (confidencePercent >= 80 ? 'var(--brand-primary, #0d5c38)' : '#f59e0b'),
                      borderRadius: '4px',
                      transition: 'width 0.6s ease'
                    }}></div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', fontSize: '0.75rem', color: '#64748b' }}>
                <span>Inference Device: <strong>{prediction.device || 'cpu'}</strong></span>
                <span>•</span>
                <span>DB ID: <code>{prediction.prediction_id ? prediction.prediction_id.slice(0, 8) + '...' : 'Persisted'}</code></span>
              </div>
            </div>
          </div>

          {/* Top 3 Predictions Breakdown */}
          {prediction.top3 && prediction.top3.length > 0 && (
            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '12px',
              padding: '1rem'
            }}>
              <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', color: '#475569', letterSpacing: '0.5px' }}>
                Top 3 Model Candidate Probabilities
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {prediction.top3.map((cand, idx) => {
                  const probVal = typeof cand.probability === 'number' ? cand.probability : 0;
                  const probPct = probVal <= 1.0 ? probVal * 100 : probVal;
                  const isTop = idx === 0;

                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.5rem 0.75rem',
                        background: isTop ? '#ecfdf5' : '#ffffff',
                        border: isTop ? '1px solid #a7f3d0' : '1px solid #e2e8f0',
                        borderRadius: '8px',
                        fontSize: '0.85rem'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: '150px' }}>
                        <span style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          background: isTop ? 'var(--brand-primary, #0d5c38)' : '#cbd5e1',
                          color: isTop ? '#ffffff' : '#334155',
                          fontSize: '0.725rem',
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          {idx + 1}
                        </span>
                        <span style={{ fontWeight: isTop ? 700 : 500, color: isTop ? 'var(--brand-primary, #0d5c38)' : '#334155' }}>
                          {formatClassName(cand.disease || cand.name)}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: '1', maxWidth: '240px' }}>
                        <div style={{ flex: 1, height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{
                            width: `${Math.min(100, Math.max(0, probPct))}%`,
                            height: '100%',
                            background: isTop ? 'var(--brand-primary, #0d5c38)' : '#94a3b8',
                            borderRadius: '3px'
                          }}></div>
                        </div>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isTop ? 'var(--brand-primary, #0d5c38)' : '#64748b', minWidth: '45px', textAlign: 'right' }}>
                          {probPct.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Agronomic Symptoms & Actions */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div style={{
              background: '#ffffff',
              borderRadius: '10px',
              border: '1px solid #e2e8f0',
              padding: '1rem'
            }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span>🔍</span> Diagnostic Symptoms
              </h4>
              <p style={{ margin: 0, fontSize: '0.825rem', color: '#475569', lineHeight: '1.5' }}>
                {diseaseInfo.symptoms}
              </p>
            </div>

            <div style={{
              background: 'rgba(13, 92, 56, 0.05)',
              borderRadius: '10px',
              border: '1px solid rgba(13, 92, 56, 0.15)',
              padding: '1rem'
            }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 700, color: 'var(--brand-primary, #0d5c38)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span>🌾</span> Agronomic Management Advice
              </h4>
              <p style={{ margin: 0, fontSize: '0.825rem', color: '#166534', lineHeight: '1.5' }}>
                {diseaseInfo.action}
              </p>
            </div>
          </div>

          {/* Action Button: Check Another Leaf */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button
              type="button"
              onClick={handleReset}
              className="btn btn-primary"
              style={{ padding: '0.6rem 1.5rem', fontSize: '0.875rem', fontWeight: 600 }}
              id="btn-react-check-another"
            >
              🔄 Check Another Leaf
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DiseaseDetection;
