import { CircleCheck, MessageSquareText, Moon, SquarePen, Sun, Trash2, X } from "lucide-react";
import { useChat } from "../state/chat";
import { useSettings } from "../state/settings";

function ago(ts: number): string {
  const min = Math.round((Date.now() - ts) / 60000);
  if (min < 1) return "Just now";
  if (min < 60) return `${min} min ago`;
  const h = Math.round(min / 60);
  if (h < 24) return `${h} h ago`;
  return new Date(ts).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden
        className="grid size-7 place-items-center rounded-[7px] bg-accent-strong font-mono text-[0.7rem] font-bold tracking-tight text-on-accent"
      >
        OS
      </span>
      <span className="text-[0.95rem] font-bold tracking-[-0.01em] text-ink">OS-Tutor</span>
    </div>
  );
}

export function Sidebar({ onNavigate, onClose }: { onNavigate?: () => void; onClose?: () => void }) {
  const { state, newLesson, select, remove, busy } = useChat();
  const { teacher, setTeacher, theme, toggleTheme } = useSettings();

  return (
    <div className="flex h-full flex-col bg-rail">
      <div className="flex h-14 shrink-0 items-center justify-between px-4">
        <Brand />
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="-mr-2 grid size-10 place-items-center rounded-control text-ink-3 hover:bg-surface-2 hover:text-ink"
          >
            <X size={18} aria-hidden />
          </button>
        )}
      </div>

      <div className="px-3">
        <button
          type="button"
          onClick={() => {
            newLesson();
            onNavigate?.();
          }}
          className="flex h-10 w-full items-center gap-2.5 rounded-control border border-line-strong bg-surface px-3 text-ui font-semibold text-ink shadow-[0_1px_0_rgb(255_255_255/0.03)_inset] transition-colors hover:border-accent-line hover:bg-surface-2"
        >
          <SquarePen size={16} className="text-accent" aria-hidden />
          New lesson
        </button>
      </div>

      <nav aria-labelledby="history-title" className="mt-6 flex min-h-0 flex-1 flex-col">
        <div className="px-4">
          <h2 id="history-title" className="text-meta font-semibold text-ink-2">
            Lessons
          </h2>
          <p className="mt-0.5 text-meta text-ink-3">Kept in this browser only</p>
        </div>
        <ul className="mt-2 flex-1 overflow-y-auto px-2 pb-3">
          {state.conversations.length === 0 && (
            <li className="px-2 py-3 text-ui text-ink-3">Your lessons will be listed here.</li>
          )}
          {state.conversations.map((c) => {
            const active = c.id === state.activeId;
            const live = state.streaming?.convId === c.id;
            return (
              <li key={c.id} className="group relative">
                <button
                  type="button"
                  onClick={() => {
                    select(c.id);
                    onNavigate?.();
                  }}
                  aria-current={active ? "page" : undefined}
                  className={[
                    "flex w-full items-start gap-2.5 rounded-control px-2.5 py-2 pr-9 text-left transition-colors",
                    active ? "bg-surface-3 text-ink" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
                  ].join(" ")}
                >
                  {c.stage === "DONE" ? (
                    <CircleCheck size={15} className="mt-0.5 shrink-0 text-success" aria-label="Finished" />
                  ) : (
                    <MessageSquareText size={15} className="mt-0.5 shrink-0 text-ink-3" aria-hidden />
                  )}
                  <span className="min-w-0">
                    <span className="line-clamp-2 text-ui">{c.title}</span>
                    <span className="mt-0.5 block text-meta text-ink-3">{live ? "Tutor is replying…" : ago(c.updatedAt)}</span>
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => remove(c.id)}
                  disabled={live && busy}
                  aria-label={`Delete lesson: ${c.title}`}
                  className="absolute right-1.5 top-1.5 grid size-7 place-items-center rounded-[6px] text-ink-3 opacity-0 transition-opacity hover:bg-surface hover:text-danger focus-visible:opacity-100 disabled:hidden group-hover:opacity-100 max-md:opacity-100"
                >
                  <Trash2 size={14} aria-hidden />
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="flex flex-col gap-1 border-t border-line px-3 py-3">
        <label className="flex min-h-10 cursor-pointer items-center justify-between gap-3 rounded-control px-2 text-ui text-ink-2 hover:bg-surface-2">
          <span>
            Evaluator view
            <span className="block text-meta text-ink-3">Show how the tutor judged each answer</span>
          </span>
          <input
            type="checkbox"
            role="switch"
            checked={teacher}
            onChange={(e) => setTeacher(e.target.checked)}
            className="peer sr-only"
          />
          <span
            aria-hidden
            className="relative h-5 w-9 shrink-0 rounded-full bg-surface-3 ring-1 ring-line-strong transition-colors peer-checked:bg-accent-strong peer-checked:ring-accent-strong peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent after:absolute after:left-0.5 after:top-0.5 after:size-4 after:rounded-full after:bg-ink after:transition-transform peer-checked:after:translate-x-4 peer-checked:after:bg-on-accent"
          />
        </label>
        <button
          type="button"
          onClick={toggleTheme}
          className="flex min-h-10 items-center gap-2.5 rounded-control px-2 text-left text-ui text-ink-2 hover:bg-surface-2 hover:text-ink"
        >
          {theme === "dark" ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
          {theme === "dark" ? "Light theme" : "Dark theme"}
        </button>
      </div>
    </div>
  );
}
