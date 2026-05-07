import { X, Cpu, FolderOpen, Copy } from "lucide-react";

export type ExtractionMode = "auto" | "digital" | "ocr";
export type OnConflict = "suffix" | "overwrite" | "skip";

export interface AppSettings {
  extractionMode: ExtractionMode;
  onConflict: OnConflict;
  autoOpenFolder: boolean;
  rememberLastFolder: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = {
  extractionMode: "auto",
  onConflict: "suffix",
  autoOpenFolder: false,
  rememberLastFolder: true,
};

const SETTINGS_KEY = "holeritech_settings";

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(s: AppSettings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onChange: (s: AppSettings) => void;
}

function RadioGroup<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string; description: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      <div className="space-y-1.5">
        {options.map((opt) => (
          <label
            key={opt.value}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
              value === opt.value
                ? "border-primary/50 bg-primary/5"
                : "border-border hover:border-border/80 hover:bg-accent/30"
            }`}
          >
            <input
              type="radio"
              className="mt-0.5 accent-primary"
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
            />
            <div>
              <p className="text-sm font-medium leading-tight">{opt.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{opt.description}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 p-3 rounded-lg border border-border hover:bg-accent/30 cursor-pointer transition-colors">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors ${
          checked ? "bg-primary" : "bg-muted"
        }`}
      >
        <span
          className={`pointer-events-none block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${
            checked ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
    </label>
  );
}

export function SettingsModal({ isOpen, onClose, settings, onChange }: SettingsModalProps) {
  if (!isOpen) return null;

  const update = (patch: Partial<AppSettings>) => {
    const next = { ...settings, ...patch };
    onChange(next);
    saveSettings(next);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-md mx-4 bg-background border border-border rounded-xl shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <h2 className="font-semibold text-sm">Configurações</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-5 space-y-6">
          {/* Modo de extração */}
          <div className="flex items-start gap-3">
            <Cpu className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <RadioGroup<ExtractionMode>
              label="Modo de extração"
              value={settings.extractionMode}
              onChange={(v) => update({ extractionMode: v })}
              options={[
                {
                  value: "auto",
                  label: "Automático",
                  description: "Tenta extração digital; se falhar, usa OCR automaticamente.",
                },
                {
                  value: "digital",
                  label: "Somente digital",
                  description: "Extrai apenas de PDFs com texto embutido. Mais rápido.",
                },
                {
                  value: "ocr",
                  label: "Somente OCR",
                  description: "Usa reconhecimento de imagem em todos os arquivos.",
                },
              ]}
            />
          </div>

          <div className="border-t border-border" />

          {/* Conflito de nomes */}
          <div className="flex items-start gap-3">
            <Copy className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <RadioGroup<OnConflict>
              label="Conflito de nomes"
              value={settings.onConflict}
              onChange={(v) => update({ onConflict: v })}
              options={[
                {
                  value: "suffix",
                  label: "Adicionar sufixo",
                  description: 'Renomeia com número: "Nome - CPF (2).pdf".',
                },
                {
                  value: "overwrite",
                  label: "Sobrescrever",
                  description: "Substitui o arquivo existente com o mesmo nome.",
                },
                {
                  value: "skip",
                  label: "Pular",
                  description: "Ignora o arquivo se já existir um com o mesmo nome.",
                },
              ]}
            />
          </div>

          <div className="border-t border-border" />

          {/* Toggles */}
          <div className="flex items-start gap-3">
            <FolderOpen className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <div className="flex-1 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Comportamento
              </p>
              <Toggle
                label="Abrir pasta ao terminar"
                description="Abre automaticamente a pasta de destino quando o processamento concluir."
                checked={settings.autoOpenFolder}
                onChange={(v) => update({ autoOpenFolder: v })}
              />
              <Toggle
                label="Lembrar última pasta de destino"
                description="Preenche automaticamente a pasta de destino com o último caminho usado."
                checked={settings.rememberLastFolder}
                onChange={(v) => update({ rememberLastFolder: v })}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border shrink-0">
          <p className="text-xs text-muted-foreground">
            As configurações são salvas automaticamente.
          </p>
        </div>
      </div>
    </div>
  );
}
