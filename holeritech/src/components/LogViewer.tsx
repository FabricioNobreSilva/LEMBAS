import { useEffect, useRef } from "react";
import { X, FolderOpen, FileText } from "lucide-react";
import { open } from "@tauri-apps/plugin-shell";

interface LogViewerProps {
  isOpen: boolean;
  onClose: () => void;
  content: string;
  logPath: string;
  logDir: string;
  onRefresh: () => void;
}

export function LogViewer({ isOpen, onClose, content, logPath, logDir, onRefresh }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      onRefresh();
    }
  }, [isOpen]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [content]);

  if (!isOpen) return null;

  const handleOpenDir = async () => {
    if (logDir) {
      try {
        await open(logDir);
      } catch {
        // ignorar
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer lateral */}
      <div className="relative ml-auto w-full max-w-2xl h-full bg-slate-950 border-l border-border flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2.5">
            <FileText className="h-4 w-4 text-primary" />
            <h2 className="font-semibold text-sm text-foreground">Log de Operações</h2>
            {logPath && (
              <span className="text-xs text-muted-foreground truncate max-w-xs">
                {logPath.split(/[/\\]/).pop()}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleOpenDir}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2.5 py-1.5 rounded-md hover:bg-accent"
            >
              <FolderOpen className="h-3.5 w-3.5" />
              Abrir pasta
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Conteúdo */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4"
        >
          {content ? (
            <pre className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap break-all">
              {content}
            </pre>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
              <FileText className="h-10 w-10 opacity-30" />
              <p className="text-sm">Nenhum log disponível para hoje.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
