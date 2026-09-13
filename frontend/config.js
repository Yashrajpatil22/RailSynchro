/**
 * RailSynchro Frontend Configuration
 * ==================================
 * The backend API URL is automatically resolved based on the environment:
 * - Localhost / 127.0.0.1 / file:// -> connects to LOCAL_API_URL (http://localhost:8000)
 * - Cloud / Vercel deployment      -> connects to PROD_API_URL
 *
 * To connect to your own deployed Render backend, update PROD_API_URL below.
 */
window.RAILSYNCHRO_CONFIG = {
  // Cloud Production Backend (e.g. Render / Railway / Cloud Run)
  PROD_API_URL: "https://railsynchro-backend.onrender.com",

  // Local Development Backend
  LOCAL_API_URL: "http://localhost:8000",

  // Manual Override (leave empty "" to enable automatic environment detection)
  API_URL_OVERRIDE: ""
};
