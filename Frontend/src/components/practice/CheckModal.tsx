import React from "react";
import { X, CheckCircle, XCircle, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";

interface CheckModalProps {
  isOpen: boolean;
  onClose: () => void;
  feedbackContent: {
    implemented?: string[];
    missing?: string[];
    nextSteps?: string[];
    cached?: boolean;
  } | null;
}

export const CheckModal: React.FC<CheckModalProps> = ({ isOpen, onClose, feedbackContent }) => {
  if (!isOpen || !feedbackContent) return null;

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-card border border-border/50 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <ClipboardList className="w-4 h-4 text-primary" />
            </div>
            <h2 className="text-lg font-bold text-foreground">AI Design Feedback</h2>
            {feedbackContent.cached && (
              <span className="text-[10px] bg-blue-500/10 text-blue-500 px-2 py-0.5 rounded-full border border-blue-500/20 font-medium">
                Cached
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* Implemented */}
          {feedbackContent.implemented && feedbackContent.implemented.length > 0 && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <h3 className="text-sm font-semibold text-emerald-500 mb-3 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                What's Implemented
              </h3>
              <ul className="space-y-2">
                {feedbackContent.implemented.map((point, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 flex-shrink-0" />
                    <span className="leading-relaxed">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing */}
          {feedbackContent.missing && feedbackContent.missing.length > 0 && (
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4">
              <h3 className="text-sm font-semibold text-rose-500 mb-3 flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                What's Missing
              </h3>
              <ul className="space-y-2">
                {feedbackContent.missing.map((point, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-2 flex-shrink-0" />
                    <span className="leading-relaxed">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Next Steps */}
          {feedbackContent.nextSteps && feedbackContent.nextSteps.length > 0 && (
            <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
              <h3 className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
                <ClipboardList className="w-4 h-4" />
                Next Steps
              </h3>
              <ol className="space-y-2">
                {feedbackContent.nextSteps.map((step, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border/50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm"
          >
            Got it, back to drawing!
          </button>
        </div>
      </div>
    </div>
  );
};

export default CheckModal;
