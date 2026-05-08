import { useEffect, useState, useCallback } from "react";
import { open } from "@tauri-apps/plugin-shell";
import {
  FileText,
  Settings,
  Sun,
  Moon,
  ExternalLink,
  FolderOpen,
  ScrollText,
  AlertCircle,
  X,
} from "lucide-react";
import { useProcessor } from "@/hooks/useProcessor";
import { DropZone } from "@/components/DropZone";
import { DestinationPicker } from "@/components/DestinationPicker";
import { ProcessButton } from "@/components/ProcessButton";
import { ProgressBar } from "@/components/ProgressBar";
import { ResultTable } from "@/components/ResultTable";
import { LogViewer } from "@/components/LogViewer";
import { SettingsModal, loadSettings, type AppSettings } from "@/components/SettingsModal";

const APP_VERSION = "1.0.3";
const LAST_FOLDER_KEY = "holeritech_last_folder";

export default function App() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [inputPaths, setInputPaths] = useState<string[]>([]);
  const [outputDir, setOutputDir] = useState<string>(() => {
    const s = loadSettings();
    return s.rememberLastFolder ? (localStorage.getItem(LAST_FOLDER_KEY) ?? "") : "";
  });
  const [showLog, setShowLog] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [dismissedUpdate, setDismissedUpdate] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(loadSettings);

  const { state, processFiles, checkForUpdates, fetchLog, reset, performUpdate } = useProcessor();

  // Verifica atualizações ao iniciar (silenciosamente)
  useEffect(() => {
    checkForUpdates();
  }, []);

  // Aplica tema ao html
  useEffect(() => {
    document.documentElement.className = theme === "light" ? "light" : "";
  }, [theme]);

  // Abre pasta automaticamente ao terminar (se configurado)
  useEffect(() => {
    if (settings.autoOpenFolder && state.summary && !state.isProcessing && outputDir) {
      open(outputDir).catch(() => { /* ignorar */ });
    }
  }, [state.summary]);

  const handleProcess = useCallback(async () => {
    if (inputPaths.length === 0 || !outputDir) return;
    if (settings.rememberLastFolder) {
      localStorage.setItem(LAST_FOLDER_KEY, outputDir);
    }
    await processFiles(inputPaths, outputDir, settings.extractionMode, settings.onConflict);
  }, [inputPaths, outputDir, processFiles, settings]);

  const handleOpenOutputDir = useCallback(async () => {
    if (outputDir) {
      try { await open(outputDir); } catch { /* ignorar */ }
    }
  }, [outputDir]);

  const handleUpdateClick = useCallback(async () => {
    if (state.updateInfo?.download_url && !state.isUpdating) {
      await performUpdate(state.updateInfo.download_url);
    }
  }, [state.updateInfo, state.isUpdating, performUpdate]);

  const canProcess = inputPaths.length > 0 && outputDir.length > 0 && !state.isProcessing;
  const showProgress = state.isProcessing && state.progress !== null;
  const showResults = state.results.length > 0;
  const showSummaryDone = !!state.summary && !state.isProcessing;

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
      {/* Barra de atualização */}
      {state.updateInfo && !dismissedUpdate && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-primary/10 border-b border-primary/20 text-sm shrink-0">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-primary" />
            {state.updateStarted ? (
              <span className="text-foreground">
                Instalando v<span className="font-semibold text-primary">{state.updateInfo.new_version}</span>... O app será reiniciado automaticamente.
              </span>
            ) : state.isUpdating ? (
              <span className="text-foreground">
                <span className="font-semibold text-primary">{state.updateProgress || "Preparando..."}</span>
              </span>
            ) : (
              <span className="text-foreground">
                Nova versão disponível:{" "}
                <span className="font-semibold text-primary">v{state.updateInfo.new_version}</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {!state.updateStarted && (
              <button
                type="button"
                onClick={handleUpdateClick}
                disabled={state.isUpdating}
                className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                {state.isUpdating ? "Atualizando..." : "Atualizar agora"}
              </button>
            )}
            {!state.isUpdating && !state.updateStarted && (
              <button
                type="button"
                onClick={() => setDismissedUpdate(true)}
                className="p-1 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Header */}
      <header
        className="flex items-center justify-between px-5 py-3.5 border-b border-border shrink-0"
        data-tauri-drag-region
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-primary/15">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight tracking-tight">HoleriTech</h1>
            <p className="text-[10px] text-muted-foreground leading-none">v{APP_VERSION}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title={theme === "dark" ? "Modo claro" : "Modo escuro"}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={() => setShowSettings(true)}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            title="Configurações"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Conteúdo principal */}
      <main className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Seção de entrada e destino */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Entrada */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Entrada — PDFs
            </label>
            <DropZone
              selectedPaths={inputPaths}
              onPathsChange={setInputPaths}
              disabled={state.isProcessing}
            />
          </div>

          {/* Destino + Botão */}
          <div className="space-y-3 flex flex-col">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Destino
              </label>
              <DestinationPicker
                path={outputDir}
                onPathChange={setOutputDir}
                disabled={state.isProcessing}
              />
            </div>

            <div className="mt-auto pt-2">
              <ProcessButton
                onClick={handleProcess}
                isProcessing={state.isProcessing}
                disabled={!canProcess}
                fileCount={inputPaths.length}
              />
            </div>

            {/* Erro global */}
            {state.error && (
              <div className="flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2.5 text-sm">
                <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
                <p className="text-red-400">{state.error}</p>
              </div>
            )}
          </div>
        </div>

        {/* Progresso */}
        {(showProgress || (state.isProcessing && !state.progress)) && (
          <div className="rounded-xl border border-border bg-card/50 p-4 space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Progresso
            </p>
            <ProgressBar
              current={state.progress?.current ?? 0}
              total={state.progress?.total ?? inputPaths.length}
              filename={state.progress?.filename}
            />
          </div>
        )}

        {/* Resultados */}
        {showResults && (
          <div className="rounded-xl border border-border bg-card/50 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Resultados
              </p>
              <div className="flex items-center gap-2">
                {showSummaryDone && (
                  <button
                    type="button"
                    onClick={handleOpenOutputDir}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2.5 py-1.5 rounded-md hover:bg-accent border border-border"
                  >
                    <FolderOpen className="h-3.5 w-3.5" />
                    Abrir destino
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowLog(true)}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2.5 py-1.5 rounded-md hover:bg-accent border border-border"
                >
                  <ScrollText className="h-3.5 w-3.5" />
                  Ver log
                </button>
                {showSummaryDone && (
                  <button
                    type="button"
                    onClick={reset}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors px-2.5 py-1.5 rounded-md hover:bg-accent border border-border"
                  >
                    Novo lote
                  </button>
                )}
              </div>
            </div>

            <ResultTable results={state.results} summary={state.summary} />
          </div>
        )}
      </main>

      {/* Visualizador de log */}
      <LogViewer
        isOpen={showLog}
        onClose={() => setShowLog(false)}
        content={state.logContent}
        logPath={state.logPath}
        logDir={state.logDir}
        onRefresh={fetchLog}
      />

      {/* Modal de configurações */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={settings}
        onChange={setSettings}
      />
    </div>
  );
}
