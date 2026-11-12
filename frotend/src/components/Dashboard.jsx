import React from 'react';
import { getAuthUser } from '../services/auth';
import BackendStatus from './BackendStatus';
import DiseaseDetection from './DiseaseDetection';
import FieldHealth from './FieldHealth';
import MultimodalAnalysis from './MultimodalAnalysis';
import CropInsights from './CropInsights';
import WeatherMarket from './WeatherMarket';
import Reports from './Reports';
import PredictionHistory from './PredictionHistory';

const Dashboard = ({ user, onLogout }) => {
  const currentUser = user || getAuthUser();

  return (
    <div className="glass-panel screen-enter" style={{ width: '100%', maxWidth: '1200px', display: 'flex', flexDirection: 'column' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--surface-border)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h2 style={{ margin: 0 }}>Paddy Farming Assistant Dashboard</h2>
            <span
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                color: '#34d399',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                padding: '0.15rem 0.5rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              FARMER
            </span>
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Logged in as <strong>{currentUser?.username || 'Farmer'}</strong>
            {currentUser?.schema_name && (
              <span style={{ marginLeft: '0.5rem', opacity: 0.85 }}>
                • Dedicated Workspace: <code>{currentUser.schema_name}</code>
              </span>
            )}
          </span>
        </div>
        <button className="btn" onClick={onLogout} style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          Logout
        </button>
      </header>

      {/* STEP 11J.1: Live Backend Connection Verification Widget */}
      <BackendStatus />

      {/* STEP 11J.2: Live Paddy Disease Detection Module */}
      <DiseaseDetection />

      {/* STEP 11J.3: Live Field Health & Satellite Monitoring Module */}
      <FieldHealth />

      {/* Multimodal Disease Analysis Module */}
      <MultimodalAnalysis />

      {/* STEP 11J.4: Live Crop Insights & Field Intelligence Module */}
      <CropInsights />

      {/* STEP 11J.5: Live Weather, Mandi Prices & Buyers Module */}
      <WeatherMarket />

      {/* STEP 11J.6: Live Reports & Official PDF Archive Module */}
      <Reports />

      {/* STEP 11J.6: Live Prediction History & Inference Logs Module */}
      <PredictionHistory />

      <div className="dashboard-grid">
        {/* Upload Card */}
        <div className="dashboard-card">
          <h3>Image Upload</h3>
          <div className="placeholder-content">
            Paddy leaf photo upload & validation active above
          </div>
        </div>

        {/* Farm Location */}
        <div className="dashboard-card">
          <h3>Farm Location</h3>
          <div className="placeholder-content">
            Farm Location & Map View
          </div>
        </div>

        {/* Question Input Placeholder */}
        <div className="dashboard-card" style={{ gridColumn: '1 / -1' }}>
          <h3>Question Input</h3>
          <div className="placeholder-content" style={{ minHeight: '80px' }}>
            Ask a question about the crop...
          </div>
        </div>

        {/* Disease Prediction Card */}
        <div className="dashboard-card">
          <h3>Disease Prediction</h3>
          <div className="placeholder-content">
            EfficientNet-B4 AI inference & top-3 rankings active above
          </div>
        </div>

        {/* Satellite Chart Placeholder */}
        <div className="dashboard-card">
          <h3>Satellite Time-Series</h3>
          <div className="placeholder-content">
            NDVI & Time-Series Chart Placeholder
          </div>
        </div>

        {/* Report Placeholder */}
        <div className="dashboard-card" style={{ gridColumn: '1 / -1' }}>
          <h3>Generation Report</h3>
          <div className="placeholder-content">
            Comprehensive Farming Assistant Report Summary Placeholder
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
