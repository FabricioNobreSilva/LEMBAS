/**
 * useProcessor.ts — Hook para comunicação com o backend Python via Tauri sidecar.
 */

import { useState, useCallback, useRef } from "react";
import { Command } from "@tauri-apps/plugin-shell";

export type FileStatus = "success" | "warning" | "error" | "processing";
export type ExtractionMethod = "digital" | "ocr" | "none";

export interface FileResult {
  original_name: string;
  new_name: string | null;
  status: FileStatus;
  method: ExtractionMethod;
  ocr_confidence: number | null;
  error_message: string | null;
}

export interface ProcessSummary {
  total: number;
  success: number;
  warnings: number;
  errors: number;
  log_path: string;
  log_dir: string;
}

export interface UpdateInfo {
  current_version: string;
  new_version: string;
  download_url: string;
  release_notes: string;
  release_page_url: string;
}

export interface ProcessorState {
  isProcessing: boolean;
  progress: { current: number; total: number; filename: string } | null;
  results: FileResult[];
  summary: ProcessSummary | null;
  error: string | null;
  updateInfo: UpdateInfo | null;
  logContent: string;
  logPath: string;
  logDir: string;
}

const INITIAL_STATE: ProcessorState = {
  isProcessing: false,
  progress: null,
  results: [],
  summary: null,
  error: null,
  updateInfo: null,
  logContent: "",
  logPath: "",
  logDir: "",
};

export function useProcessor() {
  const [state, setState] = useState<ProcessorState>(INITIAL_STATE);
  const abortRef = useRef<boolean>(false);

  const updateState = useCallback((patch: Partial<ProcessorState>) => {
    setState((prev) => ({ ...prev, ...patch }));
  }, []);

  const processFiles = useCallback(
    async (inputPaths: string[], outputDir: string) => {
      abortRef.current = false;
      updateState({
        isProcessing: true,
        progress: null,
        results: [],
        summary: null,
        error: null,
      });

      try {
        const command = Command.sidecar("binaries/holeritech-backend", [
          "--mode",
          "process",
          "--inputs",
          JSON.stringify(inputPaths),
          "--output",
          outputDir,
        ]);

        command.stdout.on("data", (line: string) => {
          if (!line.trim()) return;
          try {
            const event = JSON.parse(line) as { type: string; data: Record<string, unknown> };

            if (event.type === "progress") {
              updateState({
                progress: {
                  current: event.data.current as number,
                  total: event.data.total as number,
                  filename: event.data.filename as string,
                },
              });
            } else if (event.type === "result") {
              setState((prev) => ({
                ...prev,
                results: [...prev.results, event.data as unknown as FileResult],
              }));
            } else if (event.type === "summary") {
              updateState({
                summary: event.data as unknown as ProcessSummary,
                isProcessing: false,
                progress: null,
                logPath: event.data.log_path as string,
                logDir: event.data.log_dir as string,
              });
            } else if (event.type === "error") {
              updateState({
                error: event.data.message as string,
                isProcessing: false,
              });
            }
          } catch {
            // Linha não-JSON — ignorar
          }
        });

        command.stderr.on("data", (line: string) => {
          console.warn("[backend stderr]", line);
        });

        await command.spawn();
      } catch (err) {
        updateState({
          error: `Erro ao iniciar o processamento: ${String(err)}`,
          isProcessing: false,
        });
      }
    },
    [updateState]
  );

  const checkForUpdates = useCallback(async () => {
    try {
      const command = Command.sidecar("binaries/holeritech-backend", [
        "--mode",
        "check_update",
      ]);

      command.stdout.on("data", (line: string) => {
        if (!line.trim()) return;
        try {
          const event = JSON.parse(line) as { type: string; data: Record<string, unknown> };
          if (event.type === "update_available") {
            updateState({ updateInfo: event.data as unknown as UpdateInfo });
          }
        } catch {
          // ignorar
        }
      });

      await command.spawn();
    } catch {
      // Verificação silenciosa — não exibir erro
    }
  }, [updateState]);

  const fetchLog = useCallback(async () => {
    try {
      const command = Command.sidecar("binaries/holeritech-backend", [
        "--mode",
        "get_log",
      ]);

      command.stdout.on("data", (line: string) => {
        if (!line.trim()) return;
        try {
          const event = JSON.parse(line) as { type: string; data: Record<string, unknown> };
          if (event.type === "log_content") {
            updateState({
              logContent: event.data.content as string,
              logPath: event.data.path as string,
              logDir: event.data.log_dir as string,
            });
          }
        } catch {
          // ignorar
        }
      });

      await command.spawn();
    } catch {
      // ignorar
    }
  }, [updateState]);

  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  return { state, processFiles, checkForUpdates, fetchLog, reset };
}
