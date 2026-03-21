import React from "react";
import { CheckCircle, Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ActionButtonsProps {
  onCheck: () => void;
  onSubmit: () => void;
  isChecking: boolean;
  isSubmitting: boolean;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  onCheck,
  onSubmit,
  isChecking,
  isSubmitting,
}) => {
  return (
    <div className="fixed bottom-6 right-6 z-[1000] flex flex-col gap-3">
      {/* Check Button */}
      <button
        onClick={onCheck}
        disabled={isChecking}
        className={cn(
          "group relative flex items-center gap-2.5 px-5 py-3 rounded-2xl font-medium text-sm transition-all duration-300",
          "bg-card/80 backdrop-blur-xl border border-border/50 shadow-lg shadow-black/5",
          "hover:shadow-xl hover:shadow-primary/10 hover:border-primary/30 hover:-translate-y-0.5",
          isChecking && "opacity-70 cursor-not-allowed"
        )}
      >
        {isChecking ? (
          <Loader2 className="w-4.5 h-4.5 animate-spin text-primary" />
        ) : (
          <CheckCircle className="w-4.5 h-4.5 text-primary" />
        )}
        <span className="text-foreground">
          {isChecking ? "Checking..." : "Check"}
        </span>
        {/* Tooltip */}
        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg bg-popover border border-border text-xs text-popover-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-md">
          Get instant AI feedback
        </div>
      </button>

      {/* Submit Button */}
      <button
        onClick={onSubmit}
        disabled={isSubmitting}
        className={cn(
          "group relative flex items-center gap-2.5 px-5 py-3 rounded-2xl font-medium text-sm transition-all duration-300",
          "bg-primary text-primary-foreground shadow-lg shadow-primary/20",
          "hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 hover:bg-primary/90",
          isSubmitting && "opacity-70 cursor-not-allowed"
        )}
      >
        {isSubmitting ? (
          <Loader2 className="w-4.5 h-4.5 animate-spin" />
        ) : (
          <Send className="w-4.5 h-4.5" />
        )}
        <span>
          {isSubmitting ? "Submitting..." : "Submit"}
        </span>
        {/* Tooltip */}
        <div className="absolute right-full mr-3 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg bg-popover border border-border text-xs text-popover-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-md">
          Get your final score
        </div>
      </button>
    </div>
  );
};

export default ActionButtons;
