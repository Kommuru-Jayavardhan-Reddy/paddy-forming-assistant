import React, { useEffect } from 'react';

const Welcome = ({ onNext }) => {
  // Automatically move to dashboard after a delay
  useEffect(() => {
    const timer = setTimeout(() => {
      onNext();
    }, 4000); // 4 seconds delay for the welcome screen
    return () => clearTimeout(timer);
  }, [onNext]);

  return (
    <div className="glass-panel screen-enter welcome-container" style={{ maxWidth: '600px', width: '100%' }}>
      {/* Structural Placeholders for Animations */}
      <div className="flower-placeholder">🌸 🌺 🌾</div>
      <div className="confetti-placeholder">🎉 ✨ 🎊</div>

      <div style={{ position: 'relative', zIndex: 1, padding: '2rem 0' }}>
        <h1 style={{ fontSize: '3rem', marginBottom: '1.5rem' }}>Welcome to Paddy Farming Assistant</h1>
        <p style={{ fontSize: '1.25rem', maxWidth: '80%', margin: '0 auto' }}>
          Initializing your intelligent agricultural assistant...
        </p>
        
        <div style={{ marginTop: '2.5rem' }}>
          <button onClick={onNext} className="btn">
            Skip to Dashboard ➔
          </button>
        </div>
      </div>
    </div>
  );
};

export default Welcome;
