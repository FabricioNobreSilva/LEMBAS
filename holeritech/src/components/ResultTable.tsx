import { CheckCircle2, XCircle, AlertTriangle, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FileResult } from "@/hooks/useProcessor";

interface ResultTableProps {
  results: FileResult[];
  summary: { success: number; warnings: number; errors: number } | null;
}

const StatusIcon = ({ status }: { status: FileResult["status"] }) => {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />;
    case "warning":
      return <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />;
    case "error":
      return <XCircle className="h-4 w-4 text-red-400 shrink-0" />;
    default:
      return null;
  }
};

const MethodBadge = ({ method, confidence }: { method: FileResult["method"]; confidence: number | null }) => {
  if (method === "none") return null;
  return (
    <span
      className={cn(
        "text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0",
        method === "digital"
          ? "bg-primary/15 text-primary"
          : "bg-amber-400/15 text-amber-400"
      )}
    >
      {method === "digital" ? "digital" : `OCR${confidence ? ` ${confidence}%` : ""}`}
    </span>
  );
};

export function ResultTable({ results, summary }: ResultTableProps) {
  if (results.length === 0) return null;

  return (
    <div className="space-y-3">
      {/* Lista de resultados */}
      <div className="rounded-xl border border-border overflow-hidden">
        <div className="max-h-[300px] overflow-y-auto">
          {results.map((r, idx) => (
            <div
              key={idx}
              className={cn(
                "flex items-center gap-3 px-4 py-3 text-sm",
                idx !== results.length - 1 && "border-b border-border/50",
                r.status === "error" ? "bg-red-500/5" : "hover:bg-accent/20"
              )}
            >
              <StatusIcon status={r.status} />

              <div className="flex-1 min-w-0 flex items-center gap-2">
                <span className="text-muted-foreground truncate">{r.original_name}</span>

                {r.new_name && (
                  <>
                    <ArrowRight className="h-3 w-3 text-muted-foreground/50 shrink-0" />
                    <span className="text-foreground truncate font-medium">{r.new_name}</span>
                  </>
                )}

                {r.status === "error" && r.error_message && (
                  <>
                    <ArrowRight className="h-3 w-3 text-muted-foreground/50 shrink-0" />
                    <span className="text-red-400 truncate">{r.error_message}</span>
                  </>
                )}
              </div>

              <MethodBadge method={r.method} confidence={r.ocr_confidence} />
            </div>
          ))}
        </div>
      </div>

      {/* Sumário */}
      {summary && (
        <div className="flex items-center gap-3 text-sm">
          {summary.success > 0 && (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {summary.success} renomeado{summary.success !== 1 ? "s" : ""}
            </span>
          )}
          {summary.warnings > 0 && (
            <span className="flex items-center gap-1.5 text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5" />
              {summary.warnings} via OCR
            </span>
          )}
          {summary.errors > 0 && (
            <span className="flex items-center gap-1.5 text-red-400">
              <XCircle className="h-3.5 w-3.5" />
              {summary.errors} com erro{summary.errors !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
