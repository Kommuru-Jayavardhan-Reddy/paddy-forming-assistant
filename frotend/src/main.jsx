import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import MultimodalAnalysis from './components/MultimodalAnalysis'

const container = document.getElementById('root')
if (container) {
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

const multimodalContainer = document.getElementById('multimodal-analysis-root')
if (multimodalContainer) {
  createRoot(multimodalContainer).render(
    <StrictMode>
      <MultimodalAnalysis />
    </StrictMode>,
  )
}

