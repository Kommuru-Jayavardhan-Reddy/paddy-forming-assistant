import React, { useState, useEffect } from 'react';
import { getAdminSystemStatus } from '../services/auth';

const AdminDashboard = ({ user, onLogout }) => {
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const fetchAdminStatus = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await getAdminSystemStatus();
        if (isMounted) {
          setSystemStatus(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to retrieve administrative status.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchAdminStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="glass-panel screen-enter" style={{ width: '100%', maxWidth: '1000px', margin: '1rem auto' }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
          paddingBottom: '1.25rem',
          borderBottom: '1px solid var(--surface-border)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.5rem' }}>System Administration Portal</h2>
            <span
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                color: '#f87171',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                padding: '0.2rem 0.6rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
              }}
            >
              ADMINISTRATOR
            </span>
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Authenticated Principal: <strong>{user?.username || 'Admin'}</strong>
          </span>
        </div>

        <button
          className="btn"
          onClick={onLogout}
          style={{ padding: '0.5rem 1.25rem', fontSize: '0.875rem' }}
        >
          Sign Out
        </button>
      </header>

      {error ? (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#fca5a5',
            padding: '1rem',
            borderRadius: '12px',
            marginBottom: '1.5rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div>
            <strong>Access Error:</strong> {error}
          </div>
          <button
            className="btn"
            onClick={onLogout}
            style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
          >
            Sign Out
          </button>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* Status Card */}
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.2)',
            border: '1px solid var(--surface-border)',
            borderRadius: '16px',
            padding: '1.25rem',
          }}
        >
          <h3 style={{ fontSize: '1.1rem', marginTop: 0, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
            Backend Verification
          </h3>
          {loading ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Verifying server-side token privileges...</p>
          ) : systemStatus ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
                <span style={{ fontWeight: 600, color: '#34d399' }}>Status: {systemStatus.status}</span>
              </div>
              <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Server Verified Admin: <strong>{systemStatus.authenticated_admin}</strong>
              </p>
              <p style={{ margin: '0.25rem 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Access Granted: <strong>{systemStatus.access_granted ? 'Yes' : 'No'}</strong>
              </p>
            </div>
          ) : (
            <p style={{ color: '#f87171', fontSize: '0.875rem' }}>Unable to query admin endpoint.</p>
          )}
        </div>

        {/* Tenant Architecture Card */}
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.2)',
            border: '1px solid var(--surface-border)',
            borderRadius: '16px',
            padding: '1.25rem',
          }}
        >
          <h3 style={{ fontSize: '1.1rem', marginTop: 0, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
            Tenant Isolation Policy
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
            Per database constraint <code>chk_farmers_schema_format</code>, Administrator accounts do not possess a dedicated tenant schema (<code>schema_name=NULL</code>).
            Admin identity is derived directly from PostgreSQL <code>farmers.role='admin'</code>.
          </p>
        </div>

        {/* Role Security Card */}
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.2)',
            border: '1px solid var(--surface-border)',
            borderRadius: '16px',
            padding: '1.25rem',
          }}
        >
          <h3 style={{ fontSize: '1.1rem', marginTop: 0, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
            Privilege Separation
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
            Server-side authorization is the sole security boundary. Farmer accounts attempting to query administrative endpoints receive <code>HTTP 403 Forbidden</code> regardless of client parameters.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;

