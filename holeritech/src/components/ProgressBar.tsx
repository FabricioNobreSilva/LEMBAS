import { cn } from "@/lib/utils";

interface ProgressBarProps {
  current: number;
  total: number;
  filename?: string;
  className?: string;
}

export function ProgressBar({ current, total, filename, className }: ProgressBarProps) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {filename ? (
            <>
              Processando{" "}
              <span className="text-foreground font-medium truncate max-w-xs inline-block align-bottom">
                {filename}
              </span>
            </>
          ) : (
            "Aguardando..."
          )}
        </span>
        <span className="text-foreground font-medium tabular-nums">
          {current} / {total} — {percent}%
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
