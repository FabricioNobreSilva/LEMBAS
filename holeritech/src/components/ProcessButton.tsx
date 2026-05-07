import { Play, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProcessButtonProps {
  onClick: () => void;
  isProcessing: boolean;
  disabled?: boolean;
  fileCount: number;
}

export function ProcessButton({ onClick, isProcessing, disabled, fileCount }: ProcessButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || isProcessing}
      className={cn(
        "w-full flex items-center justify-center gap-2.5 rounded-xl px-6 py-3.5",
        "font-semibold text-sm transition-all duration-200",
        "bg-primary text-primary-foreground",
        "hover:bg-primary/90 active:scale-[0.98]",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100",
        "shadow-lg shadow-primary/20"
      )}
    >
      {isProcessing ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Processando...
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          Processar {fileCount > 0 ? `${fileCount} arquivo${fileCount !== 1 ? "s" : ""}` : "Arquivos"}
        </>
      )}
    </button>
  );
}
