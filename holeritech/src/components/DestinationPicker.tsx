import { useCallback } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { FolderOpen, FolderCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface DestinationPickerProps {
  path: string;
  onPathChange: (path: string) => void;
  disabled?: boolean;
}

export function DestinationPicker({ path, onPathChange, disabled }: DestinationPickerProps) {
  const handleClick = useCallback(async () => {
    if (disabled) return;
    const selected = await open({
      directory: true,
      multiple: false,
      title: "Selecionar pasta de destino",
    });
    if (selected && typeof selected === "string") {
      onPathChange(selected);
    }
  }, [disabled, onPathChange]);

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        className={cn(
          "w-full flex items-center gap-3 rounded-xl border border-border",
          "px-4 py-3 text-left transition-all duration-200",
          "hover:border-primary/50 hover:bg-accent/30",
          path ? "bg-secondary/30" : "bg-transparent",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        {path ? (
          <FolderCheck className="h-5 w-5 text-primary shrink-0" />
        ) : (
          <FolderOpen className="h-5 w-5 text-muted-foreground shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          {path ? (
            <>
              <p className="text-xs text-muted-foreground mb-0.5">Pasta de destino</p>
              <p className="text-sm font-medium text-foreground truncate">{path}</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Clique para selecionar a pasta de destino
            </p>
          )}
        </div>
        <span className="text-xs text-muted-foreground shrink-0 border border-border rounded px-2 py-1 hover:border-primary/50">
          Alterar
        </span>
      </button>
    </div>
  );
}
