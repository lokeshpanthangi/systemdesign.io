const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface LLMStatus {
  status: 'connected' | 'disconnected' | 'auth_required' | 'refreshing' | 'error';
  model: string;
  provider: string;
  message: string;
  has_github_token: boolean;
  last_refresh: string | null;
  token_expires_at: string | null;
}

export interface DeviceFlowStart {
  user_code: string;
  verification_uri: string;
  expires_in: number;
}

export interface DeviceFlowPoll {
  status: 'pending' | 'completed' | 'expired' | 'error';
  message: string;
}

export interface GenericResponse {
  success: boolean;
  message: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  tier: string;
  description: string;
}

export interface ModelsResponse {
  models: ModelInfo[];
  current_model: string;
}

// ─── Service ─────────────────────────────────────────────────────────────────

export const adminService = {
  /** Verify admin password */
  async verifyPassword(password: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/admin/verify-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Invalid password');
    }
    return response.json();
  },

  /** Get current LLM connection status */
  async getLLMStatus(): Promise<LLMStatus> {
    const response = await fetch(`${API_BASE}/admin/llm/status`);
    if (!response.ok) throw new Error('Failed to fetch LLM status');
    return response.json();
  },

  /** Force reconnect the LLM provider */
  async reconnectLLM(): Promise<GenericResponse> {
    const response = await fetch(`${API_BASE}/admin/llm/reconnect`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Reconnect failed');
    }
    return response.json();
  },

  /** Start GitHub device flow authentication */
  async startAuth(): Promise<DeviceFlowStart> {
    const response = await fetch(`${API_BASE}/admin/llm/auth/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start auth');
    }
    return response.json();
  },

  /** Poll for device flow completion */
  async pollAuth(): Promise<DeviceFlowPoll> {
    const response = await fetch(`${API_BASE}/admin/llm/auth/poll`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Poll failed');
    }
    return response.json();
  },

  /** Get all available models + current model */
  async getModels(): Promise<ModelsResponse> {
    const response = await fetch(`${API_BASE}/admin/models`);
    if (!response.ok) throw new Error('Failed to fetch models');
    return response.json();
  },

  /** Change the active model (requires password) */
  async changeModel(password: string, modelId: string): Promise<GenericResponse> {
    const response = await fetch(`${API_BASE}/admin/models/change`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password, model_id: modelId }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to change model');
    }
    return response.json();
  },
};
