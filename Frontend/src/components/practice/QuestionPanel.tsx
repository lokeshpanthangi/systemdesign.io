import React from "react";
import { CheckCircle, XCircle, Lightbulb, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface Problem {
  title: string;
  description: string;
  difficulty: string;
  requirements?: string[];
  constraints?: string[];
  hints?: string[];
  categories?: string[];
}

interface QuestionPanelProps {
  problem: Problem | null;
  isLoading: boolean;
}

export const QuestionPanel: React.FC<QuestionPanelProps> = ({ problem, isLoading }) => {
  const [expandedSections, setExpandedSections] = React.useState<Record<string, boolean>>({
    requirements: true,
    constraints: false,
    hints: false,
  });

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">Loading problem...</p>
        </div>
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Problem not found</p>
      </div>
    );
  }

  const difficultyConfig = {
    easy: { bg: "bg-emerald-500/10", text: "text-emerald-500", border: "border-emerald-500/20" },
    medium: { bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/20" },
    hard: { bg: "bg-rose-500/10", text: "text-rose-500", border: "border-rose-500/20" },
  };

  const diff = difficultyConfig[problem.difficulty as keyof typeof difficultyConfig] || difficultyConfig.medium;

  return (
    <div className="space-y-5 pb-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-xl font-bold text-foreground leading-tight">
            {problem.title}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-semibold border", diff.bg, diff.text, diff.border)}>
            {problem.difficulty.charAt(0).toUpperCase() + problem.difficulty.slice(1)}
          </span>
          {problem.categories?.map((cat, i) => (
            <span key={i} className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
              {cat}
            </span>
          ))}
        </div>
      </div>

      {/* Description */}
      <div className="bg-card/50 rounded-xl border border-border/50 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-primary" />
          Description
        </h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {problem.description}
        </p>
      </div>

      {/* Collapsible Sections */}
      {problem.requirements && problem.requirements.length > 0 && (
        <CollapsibleSection
          title="Requirements"
          icon={<CheckCircle className="w-4 h-4 text-emerald-500" />}
          isOpen={expandedSections.requirements}
          onToggle={() => toggleSection("requirements")}
          accentColor="emerald"
        >
          <ul className="space-y-2">
            {problem.requirements.map((req, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                <span className="w-5 h-5 rounded-md bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="leading-relaxed">{req}</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {problem.constraints && problem.constraints.length > 0 && (
        <CollapsibleSection
          title="Constraints"
          icon={<XCircle className="w-4 h-4 text-amber-500" />}
          isOpen={expandedSections.constraints}
          onToggle={() => toggleSection("constraints")}
          accentColor="amber"
        >
          <ul className="space-y-2">
            {problem.constraints.map((c, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-2 flex-shrink-0" />
                <span className="leading-relaxed">{c}</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {problem.hints && problem.hints.length > 0 && (
        <CollapsibleSection
          title="Hints"
          icon={<Lightbulb className="w-4 h-4 text-blue-500" />}
          isOpen={expandedSections.hints}
          onToggle={() => toggleSection("hints")}
          accentColor="blue"
        >
          <ul className="space-y-2">
            {problem.hints.map((hint, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                <span className="text-blue-400">💡</span>
                <span className="leading-relaxed">{hint}</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}
    </div>
  );
};

/* --- Collapsible Section --- */
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  accentColor: string;
  children: React.ReactNode;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title, icon, isOpen, onToggle, children,
}) => (
  <div className="rounded-xl border border-border/50 overflow-hidden shadow-sm transition-all">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between px-4 py-3 bg-card/50 hover:bg-card transition-colors"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-sm font-semibold text-foreground">{title}</span>
      </div>
      {isOpen ? (
        <ChevronUp className="w-4 h-4 text-muted-foreground" />
      ) : (
        <ChevronDown className="w-4 h-4 text-muted-foreground" />
      )}
    </button>
    {isOpen && (
      <div className="px-4 py-3 bg-card/30 border-t border-border/30">
        {children}
      </div>
    )}
  </div>
);

export default QuestionPanel;
