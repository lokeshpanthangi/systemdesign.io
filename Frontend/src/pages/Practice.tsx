import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTheme } from "next-themes";
import { Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";
import { ArrowLeft, PanelLeftClose, PanelLeft, Sun, Moon, Trash2, Download, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

// Sub-components
import { AIChat } from "../components/AIChat";
import { QuestionPanel } from "../components/practice/QuestionPanel";
import { ActionButtons } from "../components/practice/ActionButtons";
import { SubmitModal } from "../components/practice/SubmitModal";
import { CheckModal } from "../components/practice/CheckModal";

// API
import {
  createSession, autosaveSession, checkSession,
  getProblem, getProblemSubmissions, streamChat, streamSubmit
} from "../lib/api";
import type { SessionCheckResponse, Problem } from "../types/api";

export default function Practice() {
  const navigate = useNavigate();
  const { id: problemId } = useParams<{ id: string }>();
  const { theme, systemTheme, setTheme } = useTheme();
  const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);

  // Layout
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(38);
  const [isResizing, setIsResizing] = useState(false);
  const [activeTab, setActiveTab] = useState("question");

  // Session
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStartTime, setSessionStartTime] = useState<number>(Date.now());
  const [timeSpent, setTimeSpent] = useState<number>(0);

  // Problem
  const [problem, setProblem] = useState<Problem | null>(null);
  const [isLoadingProblem, setIsLoadingProblem] = useState(true);

  // Feedback / Check
  const [isCheckingFeedback, setIsCheckingFeedback] = useState(false);
  const [showCheckModal, setShowCheckModal] = useState(false);
  const [checkFeedback, setCheckFeedback] = useState<any>(null);

  // Submit (streaming)
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitStep, setSubmitStep] = useState("scoring");
  const [submitStatus, setSubmitStatus] = useState("Evaluating your solution...");
  const [submitScoreResult, setSubmitScoreResult] = useState<any>(null);
  const [submitTipsResult, setSubmitTipsResult] = useState<string[] | null>(null);
  const [submitResourcesResult, setSubmitResourcesResult] = useState<any>(null);

  // Submissions history
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);

  // Hash tracking
  const [lastSavedHash, setLastSavedHash] = useState("");
  const [lastCheckHash, setLastCheckHash] = useState("");
  const [lastCheckFeedback, setLastCheckFeedback] = useState<any>(null);

  // Chat
  const [chatMessages, setChatMessages] = useState<Array<{ id: string; type: "user" | "ai"; content: string; timestamp: Date }>>([
    { id: "1", type: "ai", content: "Hello! I'm your System Design Mentor. Ask me anything about system design, or ask me to review your diagram! 🚀", timestamp: new Date() },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // Theme
  const currentTheme = theme === "system" ? systemTheme : theme;
  const excalidrawTheme = currentTheme === "dark" ? "dark" : "light";
  // Use "transparent" so Excalidraw uses its own default backgrounds
  const excalidrawBackground = "transparent";

  // --- Helpers ---
  const calculateDiagramHash = (elements: any) => {
    const dataStr = JSON.stringify(elements);
    let hash = 0;
    for (let i = 0; i < dataStr.length; i++) {
      const char = dataStr.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return hash.toString(16);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  // --- Effects ---

  // Load problem
  useEffect(() => {
    const loadProblem = async () => {
      if (!problemId) { navigate("/dashboard"); return; }
      try {
        setIsLoadingProblem(true);
        setProblem(await getProblem(problemId));
      } catch { navigate("/dashboard"); }
      finally { setIsLoadingProblem(false); }
    };
    loadProblem();
  }, [problemId, navigate]);

  // Initialize session
  useEffect(() => {
    const init = async () => {
      if (!problemId) return;
      try {
        const response = await createSession({ problem_id: problemId, diagram_data: {} });
        if (response.id) {
          setSessionId(response.id);
          setSessionStartTime(Date.now());
          if (response.diagram_data?.elements && excalidrawAPI) {
            const st = excalidrawAPI.getAppState();
            excalidrawAPI.updateScene({
              elements: response.diagram_data.elements,
              appState: { ...st, ...(response.diagram_data.appState || {}), collaborators: st.collaborators || new Map() },
            });
          }
        }
      } catch (e) { console.error("Failed to create session:", e); }
    };
    if (problemId && !isLoadingProblem) init();
  }, [problemId, isLoadingProblem, excalidrawAPI]);

  // Auto-save every 10s
  useEffect(() => {
    if (!sessionId || !excalidrawAPI) return;
    const interval = setInterval(async () => {
      try {
        const elements = excalidrawAPI.getSceneElements();
        const appState = excalidrawAPI.getAppState();
        const currentTime = Math.floor((Date.now() - sessionStartTime) / 1000);
        const currentHash = calculateDiagramHash(elements);
        if (currentHash !== lastSavedHash || !lastSavedHash) {
          await autosaveSession(sessionId, { diagram_data: { elements, appState }, time_spent: currentTime });
          setLastSavedHash(currentHash);
          setTimeSpent(currentTime);
        }
      } catch (e) { console.error("Auto-save failed:", e); }
    }, 10000);
    return () => clearInterval(interval);
  }, [sessionId, excalidrawAPI, sessionStartTime, lastSavedHash]);

  // Load submissions when Solutions tab is active
  useEffect(() => {
    if (activeTab === "solutions" && problemId && !loadingSubmissions) {
      setLoadingSubmissions(true);
      getProblemSubmissions(problemId)
        .then(setSubmissions)
        .catch(console.error)
        .finally(() => setLoadingSubmissions(false));
    }
  }, [activeTab, problemId]);


  // Excalidraw theme is handled via the `theme` prop directly

  // Resize
  useEffect(() => {
    if (!isResizing) return;
    const onMove = (e: MouseEvent) => {
      const w = (e.clientX / window.innerWidth) * 100;
      if (w >= 20 && w <= 55) setSidebarWidth(w);
    };
    const onUp = () => setIsResizing(false);
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
  }, [isResizing]);

  // Timer tick
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeSpent(Math.floor((Date.now() - sessionStartTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [sessionStartTime]);

  // --- Handlers ---
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !sessionId) return;
    const userMessage = { id: Date.now().toString(), type: "user" as const, content: chatInput.trim(), timestamp: new Date() };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setIsTyping(true);

    const aiMessageId = (Date.now() + 1).toString();
    setChatMessages((prev) => [...prev, { id: aiMessageId, type: "ai" as const, content: "", timestamp: new Date() }]);

    try {
      const diagramData = excalidrawAPI ? { elements: excalidrawAPI.getSceneElements() } : { elements: [] };
      const response = await streamChat(sessionId, userMessage.content, diagramData);
      if (!response.ok) throw new Error("Failed to get AI response");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (reader) {
        let acc = "";
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              try {
                const event = JSON.parse(jsonStr);
                if (event.type === "token" && event.content) {
                  acc += event.content;
                  setChatMessages((prev) => prev.map((m) => (m.id === aiMessageId ? { ...m, content: acc } : m)));
                } else if (event.type === "status" && event.content) {
                  setChatMessages((prev) => prev.map((m) => (m.id === aiMessageId ? { ...m, content: acc + "\n\n*" + event.content + "*" } : m)));
                } else if (event.type === "error") throw new Error(event.content);
              } catch (pe) {
                if (jsonStr && !jsonStr.startsWith("ERROR:")) {
                  acc += jsonStr;
                  setChatMessages((prev) => prev.map((m) => (m.id === aiMessageId ? { ...m, content: acc } : m)));
                }
              }
            }
          }
        }
      }
    } catch {
      setChatMessages((prev) => prev.map((m) => (m.id === aiMessageId ? { ...m, content: "Sorry, I encountered an error. Please try again." } : m)));
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  };

  const handleCheck = async () => {
    if (!sessionId || !excalidrawAPI) return;
    setIsCheckingFeedback(true);
    try {
      const elements = excalidrawAPI.getSceneElements();
      const appState = excalidrawAPI.getAppState();
      const currentTime = Math.floor((Date.now() - sessionStartTime) / 1000);
      const currentHash = calculateDiagramHash(elements);

      if (currentHash === lastCheckHash && lastCheckFeedback) {
        setCheckFeedback({ ...lastCheckFeedback, cached: true });
        setShowCheckModal(true);
        setIsCheckingFeedback(false);
        return;
      }

      await autosaveSession(sessionId, { diagram_data: { elements, appState }, time_spent: currentTime });
      const checkResponse: SessionCheckResponse = await checkSession(sessionId);
      const feedback = {
        cached: checkResponse.cached,
        implemented: checkResponse.feedback.implemented || [],
        missing: checkResponse.feedback.missing || [],
        nextSteps: checkResponse.feedback.next_steps || [],
      };

      setLastCheckHash(currentHash);
      setLastCheckFeedback(feedback);
      setLastSavedHash(currentHash);
      setCheckFeedback(feedback);
      setShowCheckModal(true);
    } catch (e) {
      setCheckFeedback({
        implemented: [],
        missing: [`Failed to get feedback: ${e instanceof Error ? e.message : "Unknown error"}`],
        nextSteps: ["Check your internet connection", "Make sure you have drawn something on the canvas"],
      });
      setShowCheckModal(true);
    } finally {
      setIsCheckingFeedback(false);
    }
  };

  const handleSubmit = async () => {
    if (!sessionId || !excalidrawAPI) return;
    const elements = excalidrawAPI.getSceneElements();
    if (!elements || elements.length === 0) { alert("Cannot submit empty diagram."); return; }

    setIsSubmitting(true);
    setShowSubmitModal(true);
    setSubmitStep("scoring");
    setSubmitStatus("Evaluating your solution...");
    setSubmitScoreResult(null);
    setSubmitTipsResult(null);
    setSubmitResourcesResult(null);

    try {
      const appState = excalidrawAPI.getAppState();
      const currentTime = Math.floor((Date.now() - sessionStartTime) / 1000);
      await autosaveSession(sessionId, { diagram_data: { elements, appState }, time_spent: currentTime });

      const response = await streamSubmit(sessionId);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: any = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              try {
                const event = JSON.parse(jsonStr);
                if (event.type === "status") {
                  setSubmitStep(event.step);
                  setSubmitStatus(event.message || "Processing...");
                } else if (event.type === "score_result") {
                  setSubmitScoreResult(event.data);
                  setSubmitStep("tips");
                } else if (event.type === "tips_result") {
                  setSubmitTipsResult(event.data);
                  setSubmitStep("resources");
                } else if (event.type === "resources_result") {
                  setSubmitResourcesResult(event.data);
                } else if (event.type === "done") {
                  finalResult = event.data;
                  setSubmitStep("done");
                }
              } catch { /* skip bad JSON */ }
            }
          }
        }
      }

      // Store final result for "View Full Results" navigation
      if (finalResult) {
        (window as any).__lastSubmitResult = finalResult;
      }
    } catch (e) {
      alert(`Submit failed: ${e instanceof Error ? e.message : "Unknown error"}`);
      setShowSubmitModal(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewFullResults = () => {
    const result = (window as any).__lastSubmitResult;
    if (result) {
      navigate("/results", {
        state: {
          feedbackContent: {
            score: result.score,
            maxScore: result.max_score,
            strengths: result.feedback?.implemented || [],
            weaknesses: result.feedback?.missing || [],
            learningResources: [
              ...(result.resources?.videos || []).map((v: any) => ({ title: v.title, url: v.url, description: v.reason || v.channel || "" })),
              ...(result.resources?.docs || []).map((d: any) => ({ title: d.title, url: d.url, description: d.reason || d.source || "" })),
            ],
            questions: result.tips || [],
          },
          submissionId: "stream-" + Date.now(),
        },
      });
    }
    setShowSubmitModal(false);
  };

  const loadSubmissionDiagram = (submission: any) => {
    if (!excalidrawAPI || !submission.diagram_data) return;
    try {
      const st = excalidrawAPI.getAppState();
      excalidrawAPI.updateScene({
        elements: [...excalidrawAPI.getSceneElements(), ...(submission.diagram_data.elements || [])],
        appState: st,
      });
    } catch { alert("Failed to load submission diagram"); }
  };

  // --- Tab config ---
  const tabs = [
    { key: "question", label: "Question" },
    { key: "ai-insights", label: "AI Chat" },
    { key: "solutions", label: "Solutions" },
  ];

  return (
    <div className="h-screen w-screen flex bg-background overflow-hidden">
      {/* ===== LEFT SIDEBAR ===== */}
      <div
        className={cn(
          "relative flex flex-col border-r border-border/50 bg-card/50",
          sidebarCollapsed && "w-0 overflow-hidden"
        )}
        style={{ width: sidebarCollapsed ? 0 : `${sidebarWidth}%` }}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
          {/* Back + Timer */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.history.back()}
              className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              title="Back"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono bg-muted/50 px-2.5 py-1 rounded-lg">
              <Clock className="w-3 h-3" />
              {formatTime(timeSpent)}
            </div>
          </div>

          {/* Theme + Collapse */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setTheme(currentTheme === "dark" ? "light" : "dark")}
              className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              title={`Switch to ${currentTheme === "dark" ? "Light" : "Dark"} Mode`}
            >
              {currentTheme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              title="Collapse sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border/50">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "flex-1 py-2.5 text-xs font-medium transition-all duration-200 relative",
                activeTab === tab.key
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
              )}
            >
              {tab.label}
              {activeTab === tab.key && (
                <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-primary rounded-full" />
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-hide">
          {activeTab === "question" && (
            <QuestionPanel problem={problem} isLoading={isLoadingProblem} />
          )}

          {activeTab === "ai-insights" && (
            <AIChat
              messages={chatMessages}
              isTyping={isTyping}
              chatInput={chatInput}
              onChatInputChange={setChatInput}
              onSendMessage={handleSendMessage}
              onKeyPress={handleKeyPress}
            />
          )}

          {activeTab === "solutions" && (
            <div className="space-y-4">
              <div className="text-center py-4">
                <h2 className="text-base font-bold text-foreground mb-1">Your Solutions</h2>
                <p className="text-xs text-muted-foreground">View and load previous submissions</p>
              </div>

              {loadingSubmissions ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : submissions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-4xl mb-3">📝</p>
                  <p className="text-sm text-muted-foreground">No submissions yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {submissions.map((sub, index) => (
                    <div
                      key={sub.submission_id}
                      onClick={() => loadSubmissionDiagram(sub)}
                      className="bg-card/50 border border-border/50 rounded-xl p-4 hover:border-primary/30 hover:shadow-md transition-all cursor-pointer group"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-foreground">
                          Submission #{submissions.length - index}
                        </span>
                        <span className={cn(
                          "text-sm font-bold",
                          sub.score >= 80 ? "text-emerald-500" : sub.score >= 60 ? "text-amber-500" : "text-rose-500"
                        )}>
                          {sub.score}/{sub.max_score}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                        <span>{new Date(sub.submitted_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>{Math.floor(sub.time_spent / 60)}m {sub.time_spent % 60}s</span>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); loadSubmissionDiagram(sub); }}
                        className="w-full mt-3 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-medium transition-colors"
                      >
                        Load Diagram
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Resize Handle */}
        <div
          onMouseDown={() => setIsResizing(true)}
          className={cn(
            "absolute right-0 top-0 bottom-0 w-1 cursor-col-resize transition-colors z-10 hover:bg-primary/30",
            isResizing ? "bg-primary" : "bg-transparent"
          )}
        />
      </div>

      {/* ===== Sidebar Expand Button (when collapsed) ===== */}
      {sidebarCollapsed && (
        <button
          onClick={() => setSidebarCollapsed(false)}
          className="fixed top-4 left-4 z-[1000] p-2.5 rounded-xl bg-card/80 backdrop-blur-xl border border-border/50 shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all text-muted-foreground hover:text-foreground"
          title="Show Sidebar"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
      )}

      {/* ===== RIGHT SIDE — EXCALIDRAW ===== */}
      <div
        className="relative flex-1 h-screen bg-background"
      >
        <Excalidraw
          excalidrawAPI={(api) => setExcalidrawAPI(api)}
          theme={excalidrawTheme}
          initialData={{
            elements: [],
            appState: { viewBackgroundColor: excalidrawBackground, collaborators: new Map() },
          }}
          langCode="en"
          renderTopRightUI={() => (
            <div className="flex gap-1 p-1">
              <button
                onClick={() => excalidrawAPI?.resetScene()}
                className="p-2 rounded-lg hover:bg-muted transition-all text-muted-foreground hover:text-foreground hover:scale-105"
                title="Clear Canvas"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => console.log("Export:", excalidrawAPI?.getSceneElements())}
                className="p-2 rounded-lg hover:bg-muted transition-all text-muted-foreground hover:text-foreground hover:scale-105"
                title="Export"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          )}
        />
      </div>

      {/* ===== FLOATING ACTION BUTTONS ===== */}
      <ActionButtons
        onCheck={handleCheck}
        onSubmit={handleSubmit}
        isChecking={isCheckingFeedback}
        isSubmitting={isSubmitting}
      />

      {/* ===== CHECK MODAL ===== */}
      <CheckModal
        isOpen={showCheckModal}
        onClose={() => setShowCheckModal(false)}
        feedbackContent={checkFeedback}
      />

      {/* ===== SUBMIT MODAL (Streaming) ===== */}
      <SubmitModal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        currentStep={submitStep}
        statusMessage={submitStatus}
        scoreResult={submitScoreResult}
        tipsResult={submitTipsResult}
        resourcesResult={submitResourcesResult}
        onViewFullResults={handleViewFullResults}
      />
    </div>
  );
}