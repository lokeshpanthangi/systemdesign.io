import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// ── Backend keep-alive ping (every 4 minutes) ────────────────────────────────
const BACKEND_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const PING_INTERVAL_MS = 4 * 60 * 1000;

const pingBackend = () => {
  fetch(`${BACKEND_URL}/health`, { method: "GET" })
    .then(() => console.debug("[ping] backend alive"))
    .catch(() => console.debug("[ping] backend unreachable"));
};

if (BACKEND_URL) {
  setInterval(pingBackend, PING_INTERVAL_MS);
}
// ─────────────────────────────────────────────────────────────────────────────

createRoot(document.getElementById("root")!).render(<App />);

