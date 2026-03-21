import React from "react";
import { X, CheckCircle, XCircle, Lightbulb, ExternalLink, Play, FileText, Loader2, Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

interface SubmitModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Current step: 'scoring' | 'tips' | 'resources' | 'done' */
  currentStep: string;
  statusMessage: string;
  scoreResult: { score: number; max_score: number; breakdown: any[]; implemented: string[]; missing: string[] } | null;
  tipsResult: string[] | null;
  resourcesResult: { videos: any[]; docs: any[] } | null;
  onViewFullResults: () => void;
}

export const SubmitModal: React.FC<SubmitModalProps> = ({
  isOpen,
  onClose,
  currentStep,
  statusMessage,
  scoreResult,
  tipsResult,
  resourcesResult,
  onViewFullResults,
}) => {
  if (!isOpen) return null;

  const steps = ["scoring", "tips", "resources", "done"];
  const currentStepIndex = steps.indexOf(currentStep);
  const isDone = currentStep === "done";

  const scorePercent = scoreResult ? Math.round((scoreResult.score / scoreResult.max_score) * 100) : 0;
  const scoreColor = scorePercent >= 80 ? "text-emerald-500" : scorePercent >= 50 ? "text-amber-500" : "text-rose-500";
  const scoreRing = scorePercent >= 80 ? "stroke-emerald-500" : scorePercent >= 50 ? "stroke-amber-500" : "stroke-rose-500";

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={isDone ? onClose : undefined} />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-card border border-border/50 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-card">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Trophy className="w-4 h-4 text-primary" />
            </div>
            <h2 className="text-lg font-bold text-foreground">Evaluation Results</h2>
          </div>
          {isDone && (
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-3 border-b border-border/30 bg-muted/30">
          <div className="flex items-center gap-2">
            {[
              { label: "Scoring", step: "scoring" },
              { label: "Tips", step: "tips" },
              { label: "Resources", step: "resources" },
              { label: "Done", step: "done" },
            ].map((s, i) => {
              const isActive = steps.indexOf(s.step) === currentStepIndex;
              const isComplete = steps.indexOf(s.step) < currentStepIndex;
              return (
                <React.Fragment key={s.step}>
                  {i > 0 && (
                    <div className={cn("flex-1 h-0.5 rounded-full transition-colors duration-500", isComplete ? "bg-primary" : "bg-border")} />
                  )}
                  <div className={cn(
                    "flex items-center gap-1.5 text-xs font-medium transition-colors duration-300",
                    isActive ? "text-primary" : isComplete ? "text-primary" : "text-muted-foreground"
                  )}>
                    <div className={cn(
                      "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all duration-300",
                      isActive ? "bg-primary text-primary-foreground scale-110" :
                      isComplete ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                    )}>
                      {isComplete ? "✓" : i + 1}
                    </div>
                    <span className="hidden sm:inline">{s.label}</span>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Status Message */}
          {!isDone && (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span>{statusMessage}</span>
            </div>
          )}

          {/* Score Result */}
          {scoreResult && (
            <div className="bg-card border border-border/50 rounded-xl p-5 shadow-sm">
              <div className="flex items-center gap-6">
                {/* Score Circle */}
                <div className="relative w-20 h-20 flex-shrink-0">
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 72 72">
                    <circle cx="36" cy="36" r="30" fill="none" className="stroke-muted" strokeWidth="6" />
                    <circle
                      cx="36" cy="36" r="30" fill="none"
                      className={cn(scoreRing, "transition-all duration-1000 ease-out")}
                      strokeWidth="6" strokeLinecap="round"
                      strokeDasharray={`${(scorePercent / 100) * 188.5} 188.5`}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className={cn("text-lg font-bold", scoreColor)}>{scoreResult.score}</span>
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground mb-1">
                    {scorePercent >= 80 ? "Excellent work! 🎉" : scorePercent >= 50 ? "Good progress! 💪" : "Keep improving! 📈"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Score: {scoreResult.score}/{scoreResult.max_score} ({scorePercent}%)
                  </p>
                </div>
              </div>

              {/* Implemented / Missing */}
              {scoreResult.implemented.length > 0 && (
                <div className="mt-4 space-y-1.5">
                  <p className="text-xs font-semibold text-emerald-500 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" /> Implemented
                  </p>
                  {scoreResult.implemented.map((item, i) => (
                    <p key={i} className="text-xs text-muted-foreground pl-5">• {item}</p>
                  ))}
                </div>
              )}
              {scoreResult.missing.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  <p className="text-xs font-semibold text-rose-500 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5" /> Missing
                  </p>
                  {scoreResult.missing.map((item, i) => (
                    <p key={i} className="text-xs text-muted-foreground pl-5">• {item}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tips */}
          {tipsResult && tipsResult.length > 0 && (
            <div className="bg-card border border-border/50 rounded-xl p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                Improvement Tips
              </h3>
              <ul className="space-y-2.5">
                {tipsResult.map((tip, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-xs text-muted-foreground">
                    <span className="w-5 h-5 rounded-md bg-amber-500/10 text-amber-500 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed">{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Resources */}
          {resourcesResult && (
            <div className="space-y-3">
              {/* Videos */}
              {resourcesResult.videos.length > 0 && (
                <div className="bg-card border border-border/50 rounded-xl p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Play className="w-4 h-4 text-red-500" />
                    Video Resources
                  </h3>
                  <div className="space-y-2">
                    {resourcesResult.videos.map((video, i) => (
                      <a
                        key={i}
                        href={video.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/50 transition-colors group"
                      >
                        <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
                          <Play className="w-3.5 h-3.5 text-red-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate group-hover:text-primary transition-colors">
                            {video.title}
                          </p>
                          <p className="text-[10px] text-muted-foreground truncate">{video.channel || video.reason || ""}</p>
                        </div>
                        <ExternalLink className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Docs */}
              {resourcesResult.docs.length > 0 && (
                <div className="bg-card border border-border/50 rounded-xl p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-500" />
                    Documentation
                  </h3>
                  <div className="space-y-2">
                    {resourcesResult.docs.map((doc, i) => (
                      <a
                        key={i}
                        href={doc.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/50 transition-colors group"
                      >
                        <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-3.5 h-3.5 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate group-hover:text-primary transition-colors">
                            {doc.title}
                          </p>
                          <p className="text-[10px] text-muted-foreground truncate">{doc.source || doc.reason || ""}</p>
                        </div>
                        <ExternalLink className="w-3.5 h-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {isDone && (
          <div className="px-6 py-4 border-t border-border/50 bg-card flex items-center gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors"
            >
              Continue Editing
            </button>
            <button
              onClick={onViewFullResults}
              className="flex-1 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm"
            >
              View Full Results
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SubmitModal;
