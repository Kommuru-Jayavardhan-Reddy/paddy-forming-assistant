/// <reference types="vite/client" />
/**
 * Centralized configuration for the backend API.
 * 
 * IMPORTANT CORS REQUIREMENT:
 * The FastAPI backend MUST enable CORS for the frontend to communicate with it.
 * 
 * Architecture:
 * Frontend Browser -> HTTP request -> FastAPI Backend (CORS enabled) -> API Response
 * 
 * The frontend must NOT attempt to bypass CORS. 
 * The backend developer must configure FastAPI CORS middleware to allow the frontend origin.
 * (e.g. allowing http://localhost:5173 for local development).
 */

// Supports switching the backend URL centrally without modifying individual API functions.
// Local example: http://127.0.0.1:8000
// Colab/tunnel example: https://your-public-backend-url
export const API_BASE_URL: string = (
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE_URL) || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

