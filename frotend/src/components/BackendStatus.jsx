import React, { useState, useEffect, useCallback } from 'react';
import { checkHealth } from '../api/client';
import { API_BASE_URL } from '../api/config';

/**
 * BackendStatus Component
 * Displays live backend health status, API version, response latency,
 * and provides interactive testing for valid and invalid URLs.
 */
const BackendStatus = () => {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [customUrl, setCustomUrl] = useState('');
  const [showTester, setShowTester] = useState(false);

  const performHealthCheck = useCallback(async (urlToTest) => {
    setLoading(true);
    try {
      const res = await checkHealth(urlToTest);
      setResult(res);
    } catch (err) {
      setResult({
        connected: false,
        url: urlToTest || API_BASE_URL,
        error: err instanceof Error ? err.message : 'Unexpected connection error',
        latencyMs: 0
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    checkHealth().then((res) => {
      if (isMounted) {
        setResult(res);
        setLoading(false);
      }
    }).catch((err) => {
      if (isMounted) {
        setResult({
          connected: false,
          url: API_BASE_URL,
          error: err instanceof Error ? err.message : 'Unexpected connection error',
          latencyMs: 0
        });
        setLoading(false);
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleRecheckDefault = () => {
    setCustomUrl('');
    performHealthCheck();
  };

  const handleTestCustomUrl = (e) => {
    e.preventDefault();
    if (customUrl.trim()) {
      performHealthCheck(customUrl.trim());
    }
  };

  const handleSetSampleInvalidUrl = () => {
    const invalidUrl = 'http://127.0.0.1:9999';
    setCustomUrl(invalidUrl);
    performHealthCheck(invalidUrl);
  };

  return (
    <div 
      id="backend-connection-panel"
      className="glass-panel" 
      style={{ 
        width: '100%', 
        marginBottom: '2rem',
        padding: '1.5rem',
        border: result?.connected 
          ? '1px solid rgba(16, 185, 129, 0.4)' 
          : (loading ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid rgba(239, 68, 68, 0.4)'),
        boxShadow: result?.connected 
          ? '0 4px 20px -2px rgba(16, 185, 129, 0.15)' 
          : (loading ? '0 4px 20px -2px rgba(245, 158, 11, 0.15)' : '0 4px 20px -2px rgba(239, 68, 68, 0.15)')
      }}
    >
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div 
            style={{
              width: '14px',
              height: '14px',
              borderRadius: '50%',
              backgroundColor: loading ? '#f59e0b' : (result?.connected ? '#10b981' : '#ef4444'),
              boxShadow: loading 
                ? '0 0 10px #f59e0b' 
                : (result?.connected ? '0 0 12px #10b981' : '0 0 12px #ef4444'),
              animation: loading ? 'pulse 1.5s infinite' : 'none'
            }} 
          />
          <div>
            <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Backend Connection Status
            </h3>
            <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Target URL: <code style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>{result?.url || API_BASE_URL}</code>
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button 
            id="recheck-connection-btn"
            className="btn"
            onClick={handleRecheckDefault}
            disabled={loading}
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            {loading ? 'Testing...' : '🔄 Recheck'}
          </button>
          <button
            id="toggle-tester-btn"
            onClick={() => setShowTester(prev => !prev)}
            style={{ 
              padding: '0.4rem 0.85rem', 
              fontSize: '0.8125rem', 
              background: 'transparent', 
              border: '1px solid var(--surface-border)', 
              borderRadius: '8px',
              color: 'var(--text-secondary)',
              cursor: 'pointer'
            }}
          >
            {showTester ? 'Hide URL Tester' : '⚙️ Test Other URLs'}
          </button>
        </div>
      </div>

      {/* Connection State Details */}
      <div style={{ marginTop: '1.25rem' }}>
        {loading && (
          <div style={{ padding: '1rem', background: 'rgba(245, 158, 11, 0.08)', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.25rem' }}>⏳</span>
            <span style={{ fontSize: '0.875rem', color: '#f59e0b', fontWeight: 500 }}>
              Checking connection to FastAPI backend at {customUrl || API_BASE_URL}...
            </span>
          </div>
        )}

        {!loading && result?.connected && (
          <div 
            id="backend-status-connected"
            style={{ 
              padding: '1rem', 
              background: 'rgba(16, 185, 129, 0.08)', 
              borderRadius: '10px', 
              border: '1px solid rgba(16, 185, 129, 0.25)' 
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, color: '#10b981', fontSize: '0.95rem' }}>
                <span>✅</span> Connected Successfully (HTTP {result.statusCode})
              </span>
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', background: 'rgba(16, 185, 129, 0.15)', padding: '0.2rem 0.6rem', borderRadius: '6px' }}>
                Latency: <strong style={{ color: '#10b981' }}>{result.latencyMs} ms</strong>
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', fontSize: '0.8125rem' }}>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Service: </span>
                <strong style={{ color: 'var(--text-primary)' }}>{result.service || 'Paddy Assistant'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>Status: </span>
                <strong style={{ color: '#10b981', textTransform: 'uppercase' }}>{result.status}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)' }}>API Version: </span>
                <strong style={{ color: 'var(--text-primary)' }}>{result.version || 'v1'}</strong>
              </div>
            </div>
          </div>
        )}

        {!loading && !result?.connected && (
          <div 
            id="backend-status-error"
            style={{ 
              padding: '1rem', 
              background: 'rgba(239, 68, 68, 0.08)', 
              borderRadius: '10px', 
              border: '1px solid rgba(239, 68, 68, 0.3)' 
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem' }}>⚠️</span>
              <span style={{ fontWeight: 700, color: '#ef4444', fontSize: '0.95rem' }}>
                Connection Failed
              </span>
              {result?.statusCode && (
                <span style={{ fontSize: '0.8125rem', color: '#ef4444', fontWeight: 600 }}>
                  (HTTP {result.statusCode})
                </span>
              )}
            </div>
            <p id="backend-error-message" style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', color: '#fca5a5' }}>
              {result?.error || 'Unable to reach backend server.'}
            </p>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Tip: Verify that the FastAPI backend is running on <code>http://127.0.0.1:8000</code> or check your network/CORS configuration.
            </p>
          </div>
        )}
      </div>

      {/* Collapsible Custom URL Tester */}
      {showTester && (
        <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px dashed var(--surface-border)' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.875rem', color: 'var(--text-primary)' }}>
            URL Verification & Error Handling Probe
          </h4>
          <p style={{ margin: '0 0 0.75rem 0', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Test live responses or verify that invalid endpoints produce human-readable errors gracefully.
          </p>

          <form onSubmit={handleTestCustomUrl} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input 
              id="custom-backend-url-input"
              type="text" 
              placeholder="e.g. http://127.0.0.1:9999"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              style={{ 
                flex: '1 1 250px',
                padding: '0.45rem 0.75rem', 
                fontSize: '0.8125rem',
                borderRadius: '8px', 
                border: '1px solid var(--surface-border)',
                background: 'var(--surface-color)',
                color: 'var(--text-primary)'
              }} 
            />
            <button 
              id="test-custom-url-btn"
              type="submit" 
              className="btn"
              disabled={loading || !customUrl.trim()}
              style={{ padding: '0.45rem 0.9rem', fontSize: '0.8125rem' }}
            >
              Test Custom URL
            </button>
            <button 
              id="test-invalid-url-btn"
              type="button" 
              onClick={handleSetSampleInvalidUrl}
              disabled={loading}
              style={{ 
                padding: '0.45rem 0.9rem', 
                fontSize: '0.8125rem', 
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '8px',
                color: '#fca5a5',
                cursor: 'pointer'
              }}
            >
              Simulate Invalid URL
            </button>
            <button 
              id="reset-default-url-btn"
              type="button" 
              onClick={handleRecheckDefault}
              disabled={loading}
              style={{ 
                padding: '0.45rem 0.9rem', 
                fontSize: '0.8125rem', 
                background: 'transparent',
                border: '1px solid var(--surface-border)',
                borderRadius: '8px',
                color: 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              Reset to Default
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default BackendStatus;
