import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  adminService,
  type LLMStatus,
  type DeviceFlowStart,
  type ModelInfo,
} from '../services/adminService';
import {
  ArrowLeft,
  RefreshCw,
  Shield,
  Wifi,
  WifiOff,
  ExternalLink,
  Copy,
  Check,
  AlertTriangle,
  Loader2,
  Zap,
  Clock,
  Server,
  KeyRound,
  Activity,
  ChevronRight,
  Lock,
  Eye,
  EyeOff,
  Cpu,
  Sparkles,
  Brain,
  CircuitBoard,
  X,
} from 'lucide-react';

type AuthPhase = 'idle' | 'device_flow' | 'polling' | 'completed' | 'error';

// ═══════════════════════════════════════════════════════════════════════════════
//  PASSWORD GATE — Shown first, closes tab on wrong password
// ═══════════════════════════════════════════════════════════════════════════════

const PasswordGate = ({ onSuccess }: { onSuccess: (password: string) => void }) => {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [shake, setShake] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;

    setLoading(true);
    setError('');

    try {
      await adminService.verifyPassword(password);
      onSuccess(password);
    } catch {
      setError('Wrong password');
      setShake(true);
      setTimeout(() => setShake(false), 600);

      // Close the tab after showing the error briefly
      setTimeout(() => {
        window.close();
        // Fallback if window.close() is blocked by browser
        window.location.href = 'about:blank';
      }, 1200);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 flex items-center justify-center p-4">
      {/* Background effects */}
      <div className="fixed inset-0 opacity-[0.02]" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
      }} />
      <div className="fixed top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-orange-500/5 rounded-full blur-[150px] pointer-events-none" />

      <div className={`relative z-10 w-full max-w-md transition-transform ${shake ? 'animate-shake' : ''}`}>
        <style>{`
          @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-8px); }
            20%, 40%, 60%, 80% { transform: translateX(8px); }
          }
          .animate-shake { animation: shake 0.5s ease-in-out; }
        `}</style>

        {/* Lock icon */}
        <div className="flex justify-center mb-8">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-600/10 border border-orange-500/30 flex items-center justify-center backdrop-blur-sm">
            <Lock className="w-9 h-9 text-orange-400" />
          </div>
        </div>

        <h1 className="text-2xl font-bold text-center text-white mb-2">Admin Access</h1>
        <p className="text-gray-500 text-center mb-8 text-sm">Enter admin password to continue</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <input
              ref={inputRef}
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Admin password..."
              className="w-full px-5 py-4 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-600 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/30 transition-all text-lg pr-12"
              autoComplete="off"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm animate-in fade-in duration-200">
              <X className="w-4 h-4 flex-shrink-0" />
              <span>{error} — closing tab...</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !password.trim()}
            className="w-full flex items-center justify-center gap-2 px-5 py-4 rounded-xl font-semibold text-lg transition-all duration-300 bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 shadow-lg shadow-orange-500/20 hover:shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Shield className="w-5 h-5" />
                Verify & Enter
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════════════
//  PROVIDER ICONS — Visual badges for each model provider
// ═══════════════════════════════════════════════════════════════════════════════

const providerConfig: Record<string, { gradient: string; border: string; text: string; icon: React.ReactNode }> = {
  OpenAI: {
    gradient: 'from-emerald-500/15 to-green-500/5',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    icon: <Sparkles className="w-4 h-4" />,
  },
  Anthropic: {
    gradient: 'from-amber-500/15 to-orange-500/5',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    icon: <Brain className="w-4 h-4" />,
  },
  Google: {
    gradient: 'from-blue-500/15 to-cyan-500/5',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    icon: <Cpu className="w-4 h-4" />,
  },
  xAI: {
    gradient: 'from-purple-500/15 to-violet-500/5',
    border: 'border-purple-500/30',
    text: 'text-purple-400',
    icon: <CircuitBoard className="w-4 h-4" />,
  },
  Amazon: {
    gradient: 'from-teal-500/15 to-cyan-500/5',
    border: 'border-teal-500/30',
    text: 'text-teal-400',
    icon: <Server className="w-4 h-4" />,
  },
};

const tierBadge: Record<string, { bg: string; text: string }> = {
  flagship:  { bg: 'bg-yellow-500/10 border border-yellow-500/20', text: 'text-yellow-400' },
  premium:   { bg: 'bg-rose-500/10 border border-rose-500/20', text: 'text-rose-400' },
  efficient: { bg: 'bg-sky-500/10 border border-sky-500/20', text: 'text-sky-400' },
  nano:      { bg: 'bg-gray-500/10 border border-gray-500/20', text: 'text-gray-400' },
  reasoning: { bg: 'bg-violet-500/10 border border-violet-500/20', text: 'text-violet-400' },
};


// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN ADMIN PAGE
// ═══════════════════════════════════════════════════════════════════════════════

const AdminPanel = ({ adminPassword }: { adminPassword: string }) => {
  const navigate = useNavigate();

  // LLM Status
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState('');

  // Reconnect
  const [reconnecting, setReconnecting] = useState(false);

  // Models
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [currentModel, setCurrentModel] = useState('');
  const [changingModel, setChangingModel] = useState('');
  const [modelSuccess, setModelSuccess] = useState('');

  // Auth Flow
  const [authPhase, setAuthPhase] = useState<AuthPhase>('idle');
  const [deviceFlow, setDeviceFlow] = useState<DeviceFlowStart | null>(null);
  const [authMessage, setAuthMessage] = useState('');
  const [copied, setCopied] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [loadingElapsed, setLoadingElapsed] = useState(0);
  const loadingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ─── Fetch Status ──────────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      setStatusLoading(true);
      setStatusError('');
      setLoadingElapsed(0);
      // Track elapsed time so we can show a Render cold-start hint
      loadingTimerRef.current = setInterval(() => setLoadingElapsed(e => e + 1), 1000);
      const data = await adminService.getLLMStatus();
      setStatus(data);
    } catch (err: any) {
      setStatusError(err.message || 'Failed to fetch status');
    } finally {
      setStatusLoading(false);
      setLoadingElapsed(0);
      if (loadingTimerRef.current) clearInterval(loadingTimerRef.current);
    }
  }, []);

  // ─── Fetch Models ─────────────────────────────────────────────────────
  const fetchModels = useCallback(async () => {
    try {
      const data = await adminService.getModels();
      setModels(data.models);
      setCurrentModel(data.current_model);
    } catch (err: any) {
      console.error('Failed to fetch models:', err);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchModels();
  }, [fetchStatus, fetchModels]);

  // ─── Change Model ─────────────────────────────────────────────────────
  const handleModelChange = async (modelId: string) => {
    if (modelId === currentModel) return;
    setChangingModel(modelId);
    setModelSuccess('');

    try {
      await adminService.changeModel(adminPassword, modelId);
      setCurrentModel(modelId);
      setModelSuccess(modelId);
      // Also refresh status to show new model
      await fetchStatus();
      setTimeout(() => setModelSuccess(''), 3000);
    } catch (err: any) {
      setStatusError(err.message);
    } finally {
      setChangingModel('');
    }
  };

  // ─── Reconnect ─────────────────────────────────────────────────────────
  const handleReconnect = async () => {
    setReconnecting(true);
    try {
      await adminService.reconnectLLM();
      await fetchStatus();
    } catch (err: any) {
      setStatusError(err.message);
    } finally {
      setReconnecting(false);
    }
  };

  // ─── Auth Flow ─────────────────────────────────────────────────────────
  const startAuth = async () => {
    try {
      setAuthPhase('device_flow');
      setAuthMessage('');
      const flow = await adminService.startAuth();
      setDeviceFlow(flow);
      setCountdown(flow.expires_in);

      countdownRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            if (countdownRef.current) clearInterval(countdownRef.current);
            setAuthPhase('error');
            setAuthMessage('Authentication timed out. Please try again.');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      setAuthPhase('polling');
      pollIntervalRef.current = setInterval(async () => {
        try {
          const result = await adminService.pollAuth();
          setAuthMessage(result.message);

          if (result.status === 'completed') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (countdownRef.current) clearInterval(countdownRef.current);
            setAuthPhase('completed');
            setAuthMessage('Authentication successful! Initializing connection...');

            // Provider initializes in background — wait + retry status
            const waitAndRefresh = async (retries = 5) => {
              for (let i = 0; i < retries; i++) {
                await new Promise((r) => setTimeout(r, 2000));
                try {
                  const statusData = await adminService.getLLMStatus();
                  setStatus(statusData);
                  if (statusData.status === 'connected') return;
                } catch { /* ignore, retry */ }
              }
            };
            await waitAndRefresh();
          } else if (result.status === 'error' || result.status === 'expired') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (countdownRef.current) clearInterval(countdownRef.current);
            setAuthPhase('error');
          }
        } catch (err: any) {
          setAuthMessage(err.message);
        }
      }, 8000); // 8s — avoids GitHub device flow rate limiting
    } catch (err: any) {
      setAuthPhase('error');
      setAuthMessage(err.message || 'Failed to start authentication');
    }
  };

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
      if (loadingTimerRef.current) clearInterval(loadingTimerRef.current);
    };
  }, []);

  const copyCode = async () => {
    if (deviceFlow?.user_code) {
      await navigator.clipboard.writeText(deviceFlow.user_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'connected':     return 'text-emerald-400';
      case 'refreshing':    return 'text-amber-400';
      case 'auth_required': return 'text-orange-400';
      case 'disconnected':  return 'text-red-400';
      case 'error':         return 'text-red-500';
      default:              return 'text-gray-400';
    }
  };

  const getStatusBg = (s: string) => {
    switch (s) {
      case 'connected':     return 'bg-emerald-500/10 border-emerald-500/30';
      case 'refreshing':    return 'bg-amber-500/10 border-amber-500/30';
      case 'auth_required': return 'bg-orange-500/10 border-orange-500/30';
      case 'disconnected':  return 'bg-red-500/10 border-red-500/30';
      case 'error':         return 'bg-red-500/10 border-red-500/30';
      default:              return 'bg-gray-500/10 border-gray-500/30';
    }
  };

  const getStatusIcon = (s: string) => {
    switch (s) {
      case 'connected':     return <Wifi className="w-5 h-5 text-emerald-400" />;
      case 'refreshing':    return <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />;
      case 'auth_required': return <KeyRound className="w-5 h-5 text-orange-400" />;
      case 'disconnected':  return <WifiOff className="w-5 h-5 text-red-400" />;
      case 'error':         return <AlertTriangle className="w-5 h-5 text-red-500" />;
      default:              return <Activity className="w-5 h-5 text-gray-400" />;
    }
  };

  // Group models by provider
  const groupedModels = models.reduce<Record<string, ModelInfo[]>>((acc, model) => {
    if (!acc[model.provider]) acc[model.provider] = [];
    acc[model.provider].push(model);
    return acc;
  }, {});

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-white">
      {/* Background effects */}
      <div className="fixed inset-0 opacity-[0.03]" style={{
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
      }} />
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-orange-500/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-[400px] h-[400px] bg-blue-500/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-center gap-4 mb-10">
          <button onClick={() => navigate(-1)}
            className="group flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
            <span className="text-sm text-gray-400">Back</span>
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
            <Shield className="w-4 h-4 text-orange-400" />
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Admin Panel</span>
          </div>
        </div>

        {/* Title */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent mb-2">
            LLM Connection Manager
          </h1>
          <p className="text-gray-500 text-lg">
            Manage the AI provider, model selection, and connection status.
          </p>
        </div>

        {/* Status Card */}
        <div className="mb-8">
          <div className={`rounded-2xl border backdrop-blur-sm p-6 transition-all duration-500 ${
            status ? getStatusBg(status.status) : 'bg-white/5 border-white/10'
          }`}>
            {statusLoading ? (
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                  <span className="text-gray-400">Connecting to backend...</span>
                  {loadingElapsed > 0 && (
                    <span className="text-gray-600 text-sm font-mono">{loadingElapsed}s</span>
                  )}
                </div>
                {loadingElapsed >= 5 && (
                  <p className="text-xs text-amber-500/70 pl-8">
                    Server is waking up (Render cold start) — usually takes 20–60s on first request.
                  </p>
                )}
              </div>
            ) : statusError ? (
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                <span className="text-red-400">{statusError}</span>
              </div>
            ) : status ? (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(status.status)}
                    <div>
                      <h2 className="text-xl font-semibold">
                        <span className={getStatusColor(status.status)}>
                          {status.status === 'connected' ? 'Connected' :
                           status.status === 'refreshing' ? 'Refreshing...' :
                           status.status === 'auth_required' ? 'Authentication Required' :
                           status.status === 'disconnected' ? 'Disconnected' :
                           status.status === 'error' ? 'Error' : status.status}
                        </span>
                      </h2>
                      <p className="text-sm text-gray-500">{status.message}</p>
                    </div>
                  </div>
                  <button onClick={fetchStatus} disabled={statusLoading}
                    className="p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300 disabled:opacity-50"
                    title="Refresh status"
                  >
                    <RefreshCw className={`w-4 h-4 text-gray-400 ${statusLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <InfoTile icon={<Server className="w-4 h-4" />} label="Provider" value={status.provider} />
                  <InfoTile icon={<Zap className="w-4 h-4" />} label="Active Model" value={status.model} />
                  <InfoTile icon={<Clock className="w-4 h-4" />} label="Last Refresh"
                    value={status.last_refresh ? new Date(status.last_refresh).toLocaleTimeString() : 'Never'} />
                  <InfoTile icon={<KeyRound className="w-4 h-4" />} label="GitHub Token"
                    value={status.has_github_token ? 'Stored' : 'Missing'}
                    valueColor={status.has_github_token ? 'text-emerald-400' : 'text-red-400'} />
                </div>

                {status.token_expires_at && (
                  <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/5">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span className="text-sm text-gray-400">
                      Token expires at{' '}
                      <span className="text-gray-300 font-mono">{new Date(status.token_expires_at).toLocaleString()}</span>
                    </span>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════
            MODEL SELECTOR — The big feature
        ═══════════════════════════════════════════════════════════════════ */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-600/10 border border-violet-500/30">
              <Cpu className="w-5 h-5 text-violet-400" />
            </div>
            Model Selection
          </h2>

          {Object.entries(groupedModels).map(([provider, providerModels]) => {
            const config = providerConfig[provider] || providerConfig.OpenAI;
            return (
              <div key={provider} className="mb-6">
                {/* Provider header */}
                <div className="flex items-center gap-2 mb-3">
                  <div className={`p-1.5 rounded-lg bg-gradient-to-br ${config.gradient} border ${config.border}`}>
                    <span className={config.text}>{config.icon}</span>
                  </div>
                  <h3 className={`font-semibold text-sm uppercase tracking-wider ${config.text}`}>{provider}</h3>
                  <div className="flex-1 h-px bg-white/5 ml-2" />
                </div>

                {/* Model cards grid */}
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {providerModels.map((model) => {
                    const isActive = model.id === currentModel;
                    const isChanging = model.id === changingModel;
                    const justChanged = model.id === modelSuccess;
                    const tier = tierBadge[model.tier] || tierBadge.efficient;

                    return (
                      <button
                        key={model.id}
                        onClick={() => handleModelChange(model.id)}
                        disabled={isActive || !!changingModel}
                        className={`group relative text-left p-4 rounded-xl border transition-all duration-300 ${
                          isActive
                            ? `bg-gradient-to-br ${config.gradient} ${config.border} ring-1 ring-inset ring-white/10`
                            : 'bg-white/[0.02] border-white/10 hover:bg-white/[0.05] hover:border-white/20'
                        } ${changingModel && !isChanging ? 'opacity-50' : ''}`}
                      >
                        {/* Active indicator */}
                        {isActive && (
                          <div className="absolute top-3 right-3">
                            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
                              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              <span className="text-[10px] font-semibold text-emerald-400 uppercase">Active</span>
                            </div>
                          </div>
                        )}

                        {/* Just changed indicator */}
                        {justChanged && (
                          <div className="absolute top-3 right-3">
                            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span className="text-[10px] font-semibold text-emerald-400">Switched!</span>
                            </div>
                          </div>
                        )}

                        {/* Loading indicator */}
                        {isChanging && (
                          <div className="absolute top-3 right-3">
                            <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                          </div>
                        )}

                        <div className="flex items-start gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-sm text-white truncate">{model.name}</span>
                              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${tier.bg} ${tier.text}`}>
                                {model.tier}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 leading-relaxed">{model.description}</p>
                            <p className="text-[11px] text-gray-600 font-mono mt-1.5">{model.id}</p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Cards (Reconnect + Auth) */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Reconnect */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-sm p-6 hover:border-white/20 transition-all duration-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-blue-500/10">
                <RefreshCw className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Reconnect</h3>
                <p className="text-sm text-gray-500">Force-refresh the API token</p>
              </div>
            </div>
            <p className="text-sm text-gray-400 mb-5">
              If the LLM is unresponsive, refresh the Copilot API token. Won't require re-authentication.
            </p>
            <button onClick={handleReconnect}
              disabled={reconnecting || status?.status === 'auth_required'}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-300 bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 hover:border-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {reconnecting ? <><Loader2 className="w-4 h-4 animate-spin" /> Reconnecting...</>
                : <><RefreshCw className="w-4 h-4" /> Refresh Token</>}
            </button>
          </div>

          {/* Auth */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-sm p-6 hover:border-white/20 transition-all duration-300">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-orange-500/10">
                <KeyRound className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Authenticate</h3>
                <p className="text-sm text-gray-500">GitHub OAuth device flow</p>
              </div>
            </div>
            <p className="text-sm text-gray-400 mb-5">
              {status?.has_github_token
                ? 'Re-authenticate if your token was revoked.'
                : 'Connect your GitHub account to enable AI features.'}
            </p>
            <button onClick={startAuth} disabled={authPhase === 'polling'}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-300 bg-orange-500/10 border border-orange-500/30 text-orange-400 hover:bg-orange-500/20 hover:border-orange-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {authPhase === 'polling' ? <><Loader2 className="w-4 h-4 animate-spin" /> Waiting for auth...</>
                : <><KeyRound className="w-4 h-4" /> {status?.has_github_token ? 'Re-authenticate' : 'Start Authentication'} <ChevronRight className="w-4 h-4" /></>}
            </button>
          </div>
        </div>

        {/* Device Flow Panel */}
        {authPhase !== 'idle' && deviceFlow && (
          <div className="rounded-2xl border border-orange-500/20 bg-orange-500/5 backdrop-blur-sm p-6 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {authPhase === 'completed' ? (
              <div className="text-center py-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 mb-4">
                  <Check className="w-8 h-8 text-emerald-400" />
                </div>
                <h3 className="text-xl font-semibold text-emerald-400 mb-2">Authentication Successful!</h3>
                <p className="text-gray-400">GitHub Copilot API is now connected.</p>
              </div>
            ) : authPhase === 'error' ? (
              <div className="text-center py-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 mb-4">
                  <AlertTriangle className="w-8 h-8 text-red-400" />
                </div>
                <h3 className="text-xl font-semibold text-red-400 mb-2">Authentication Failed</h3>
                <p className="text-gray-400 mb-4">{authMessage}</p>
                <button onClick={() => { setAuthPhase('idle'); setDeviceFlow(null); }}
                  className="px-6 py-2.5 rounded-xl bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 transition-all"
                >Try Again</button>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold">GitHub Device Authorization</h3>
                  <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-white/5 border border-white/10">
                    <Clock className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-sm font-mono text-gray-400">{formatTime(countdown)}</span>
                  </div>
                </div>
                <div className="space-y-6">
                  <div className="flex gap-4">
                    <StepCircle n={1} />
                    <div className="flex-1">
                      <p className="text-gray-300 mb-3">Copy this code and enter it on GitHub:</p>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 px-5 py-4 rounded-xl bg-gray-900/80 border border-white/10 font-mono text-2xl font-bold text-center tracking-[0.3em] text-white">
                          {deviceFlow.user_code}
                        </div>
                        <button onClick={copyCode} className="p-3.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all" title="Copy code">
                          {copied ? <Check className="w-5 h-5 text-emerald-400" /> : <Copy className="w-5 h-5 text-gray-400" />}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <StepCircle n={2} />
                    <div className="flex-1">
                      <p className="text-gray-300 mb-3">Open the GitHub authorization page:</p>
                      <a href={deviceFlow.verification_uri} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gray-800/80 border border-white/10 text-orange-400 font-medium hover:bg-gray-800 hover:border-orange-500/30 transition-all"
                      ><ExternalLink className="w-4 h-4" />{deviceFlow.verification_uri}</a>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <StepCircle n={3} />
                    <div className="flex-1 flex items-center gap-3">
                      <Loader2 className="w-4 h-4 text-orange-400 animate-spin" />
                      <p className="text-gray-300">{authMessage || 'Waiting for you to authorize on GitHub...'}</p>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* How it works */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-sm p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-orange-400" />
            How It Works
          </h3>
          <div className="grid md:grid-cols-3 gap-6">
            <HowItWorksStep step={1} title="GitHub OAuth"
              description="Authenticate once via GitHub device flow. Your token is stored permanently." />
            <HowItWorksStep step={2} title="Copilot API Token"
              description="Short-lived Copilot API tokens are auto-refreshed silently in the background." />
            <HowItWorksStep step={3} title="Multi-Model Access"
              description="Access OpenAI, Anthropic, Google & Grok models — all through a single API." />
          </div>
        </div>
      </div>
    </div>
  );
};


// ═══════════════════════════════════════════════════════════════════════════════
//  SUB-COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

const InfoTile = ({ icon, label, value, valueColor = 'text-white' }: {
  icon: React.ReactNode; label: string; value: string; valueColor?: string;
}) => (
  <div className="px-4 py-3 rounded-xl bg-white/5 border border-white/5">
    <div className="flex items-center gap-1.5 mb-1">
      <span className="text-gray-500">{icon}</span>
      <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
    <p className={`text-sm font-medium truncate ${valueColor}`}>{value}</p>
  </div>
);

const StepCircle = ({ n }: { n: number }) => (
  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-sm font-bold text-orange-400">
    {n}
  </div>
);

const HowItWorksStep = ({ step, title, description }: { step: number; title: string; description: string }) => (
  <div className="space-y-3">
    <div className="flex items-center gap-3">
      <StepCircle n={step} />
      <h4 className="font-medium">{title}</h4>
    </div>
    <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
  </div>
);


// ═══════════════════════════════════════════════════════════════════════════════
//  MAIN EXPORT — Password gate wraps the admin panel
// ═══════════════════════════════════════════════════════════════════════════════

const Admin = () => {
  const [authenticated, setAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');

  const handleAuthSuccess = (password: string) => {
    setAdminPassword(password);
    setAuthenticated(true);
  };

  if (!authenticated) {
    return <PasswordGate onSuccess={handleAuthSuccess} />;
  }

  return <AdminPanel adminPassword={adminPassword} />;
};

export default Admin;
