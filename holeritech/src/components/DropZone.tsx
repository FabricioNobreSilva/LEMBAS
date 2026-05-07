import { useCallback, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { Upload, FolderOpen, X, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface DropZoneProps {
  selectedPaths: string[];
  onPathsChange: (paths: string[]) => void;
  disabled?: boolean;
}

export function DropZone({ selectedPaths, onPathsChange, disabled }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleClick = useCallback(async () => {
    if (disabled) return;
    const selected = await open({
      multiple: true,
      filters: [{ name: "PDF", extensions: ["pdf"] }],
      title: "Selecionar PDFs de holerites",
    });
    if (selected) {
      const paths = Array.isArray(selected) ? selected : [selected];
      onPathsChange(paths);
    }
  }, [disabled, onPathsChange]);

  const handleFolderClick = useCallback(async () => {
    if (disabled) return;
    const selected = await open({
      directory: true,
      multiple: false,
      title: "Selecionar pasta com holerites",
    });
    if (selected && typeof selected === "string") {
      onPathsChange([selected]);
    }
  }, [disabled, onPathsChange]);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      if (disabled) return;
      e.preventDefault();
      setIsDragging(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      if (disabled) return;
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files)
        .filter((f) => f.name.toLowerCase().endsWith(".pdf"))
        .map((f) => f.path ?? (f as unknown as { path: string }).path);
      if (files.length > 0) {
        onPathsChange(files.filter(Boolean));
      }
    },
    [disabled, onPathsChange]
  );

  const removeItem = useCallback(
    (idx: number) => {
      onPathsChange(selectedPaths.filter((_, i) => i !== idx));
    },
    [selectedPaths, onPathsChange]
  );

  const isEmpty = selectedPaths.length === 0;

  return (
    <div className="space-y-3">
      <div
        className={cn(
          "relative rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer select-none",
          "flex flex-col items-center justify-center gap-3 min-h-[180px] p-6",
          isDragging
            ? "border-primary bg-primary/10 scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-accent/30",
          disabled && "opacity-50 cursor-not-allowed",
          !isEmpty && "min-h-[100px]"
        )}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && handleClick()}
        aria-label="Área de seleção de PDFs"
      >
        {isEmpty ? (
          <>
            <div className="p-3 rounded-full bg-primary/10">
              <Upload className="h-7 w-7 text-primary" />
            </div>
            <div className="text-center">
              <p className="font-medium text-foreground">Arraste PDFs aqui</p>
              <p className="text-sm text-muted-foreground mt-1">
                ou clique para selecionar arquivo(s)
              </p>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <FileText className="h-4 w-4 text-primary" />
            <span>
              {selectedPaths.length === 1 && selectedPaths[0].includes("/") === false && !selectedPaths[0].endsWith(".pdf")
                ? "1 pasta selecionada"
                : `${selectedPaths.length} ${selectedPaths.length === 1 ? "arquivo selecionado" : "arquivos selecionados"}`}
            </span>
            <span className="text-xs">(clique para trocar)</span>
          </div>
        )}
      </div>

      {/* Botão de pasta */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          handleFolderClick();
        }}
        disabled={disabled}
        className={cn(
          "w-full flex items-center justify-center gap-2 rounded-lg border border-border",
          "px-4 py-2.5 text-sm font-medium text-muted-foreground",
          "hover:text-foreground hover:border-primary/50 hover:bg-accent/30",
          "transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        <FolderOpen className="h-4 w-4" />
        Selecionar pasta inteira
      </button>

      {/* Lista de arquivos selecionados */}
      {selectedPaths.length > 0 && (
        <ul className="space-y-1 max-h-40 overflow-y-auto">
          {selectedPaths.map((p, idx) => {
            const name = p.split(/[/\\]/).pop() ?? p;
            return (
              <li
                key={idx}
                className="flex items-center justify-between rounded-md px-3 py-1.5 bg-secondary/50 text-sm group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="h-3.5 w-3.5 text-primary shrink-0" />
                  <span className="truncate text-muted-foreground">{name}</span>
                </div>
                {!disabled && (
                  <button
                    type="button"
                    onClick={() => removeItem(idx)}
                    className="ml-2 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                    aria-label={`Remover ${name}`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
