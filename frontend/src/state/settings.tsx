import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchModels } from "../lib/api";

type Theme = "dark" | "light";

/** What /api/models told us. `unreachable` = the tutor server itself did not answer. */
export type ModelsStatus = "loading" | "ready" | "no-models" | "unreachable";

interface Settings {
  theme: Theme;
  toggleTheme: () => void;
  /** Evaluator view: shows the tutor's analysis of each student answer. */
  teacher: boolean;
  setTeacher: (on: boolean) => void;
  models: string[];
  defaultModel: string | null;
  model: string | null;
  setModel: (m: string) => void;
  modelsStatus: ModelsStatus;
  reloadModels: () => void;
}

const SettingsContext = createContext<Settings | null>(null);

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // blocked storage: the setting lasts for this visit only
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => (read("os-tutor:theme") === "light" ? "light" : "dark"));
  const [teacher, setTeacherState] = useState(() => read("teacher") === "1"); // same key as the old page
  const [models, setModels] = useState<string[]>([]);
  const [defaultModel, setDefaultModel] = useState<string | null>(null);
  const [model, setModelState] = useState<string | null>(null);
  const [modelsStatus, setModelsStatus] = useState<ModelsStatus>("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    write("os-tutor:theme", theme);
  }, [theme]);

  useEffect(() => {
    const controller = new AbortController();
    fetchModels(controller.signal)
      .then(({ models, default: def }) => {
        setModels(models);
        setDefaultModel(def);
        const saved = read("os-tutor:model");
        setModelState(saved && models.includes(saved) ? saved : def);
        // The server lists models from Ollama and returns [] when Ollama cannot be reached.
        setModelsStatus(models.length ? "ready" : "no-models");
      })
      .catch((e: Error) => {
        if (e.name !== "AbortError") setModelsStatus("unreachable");
      });
    return () => controller.abort();
  }, [attempt]);

  const setTeacher = useCallback((on: boolean) => {
    setTeacherState(on);
    write("teacher", on ? "1" : "0");
  }, []);
  const reloadModels = useCallback(() => {
    setModelsStatus("loading");
    setAttempt((n) => n + 1);
  }, []);
  const setModel = useCallback((m: string) => {
    setModelState(m);
    write("os-tutor:model", m);
  }, []);

  const value = useMemo<Settings>(
    () => ({
      theme,
      toggleTheme: () => setTheme((t) => (t === "dark" ? "light" : "dark")),
      teacher,
      setTeacher,
      models,
      defaultModel,
      model,
      setModel,
      modelsStatus,
      reloadModels,
    }),
    [theme, teacher, setTeacher, models, defaultModel, model, setModel, modelsStatus, reloadModels],
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Settings {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings outside SettingsProvider");
  return ctx;
}
