import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, BookOpen, Menu, RefreshCw } from "lucide-react";
import { Composer, type ComposerHandle } from "./components/Composer";
import { MessageList } from "./components/Messages";
import { Sidebar } from "./components/Sidebar";
import { SourcesPanel, type SourceFocus } from "./components/SourcesPanel";
import { StageRail } from "./components/StageRail";
import { Welcome } from "./components/Welcome";
import { turnLabel } from "./lib/tutor";
import { useChat } from "./state/chat";
import { useSettings } from "./state/settings";
import type { Conversation, TutorMessage } from "./types";

const XL = "(min-width: 80rem)";

function useMedia(query: string) {
  const [match, setMatch] = useState(() => matchMedia(query).matches);
  useEffect(() => {
    const mq = matchMedia(query);
    const on = () => setMatch(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return match;
}

/** A native modal <dialog>: focus trap, Escape and an inert page come from the browser. */
function Drawer({ open, onClose, side, label, children }: { open: boolean; onClose: () => void; side: "left" | "right"; label: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      aria-label={label}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      className={`drawer ${side}`}
    >
      <div className={`h-full overflow-hidden bg-surface ${side === "left" ? "border-r" : "border-l"} border-line`}>{children}</div>
    </dialog>
  );
}

function sourceTarget(conv: Conversation | null, msgId: string | null): TutorMessage | null {
  const tutors = (conv?.messages ?? []).filter((m): m is TutorMessage => m.role === "tutor" && m.sources.length > 0);
  return tutors.find((m) => m.id === msgId) ?? tutors.at(-1) ?? null;
}

export default function App() {
  const chat = useChat();
  const { active, busy } = chat;
  const { teacher, model, modelsStatus, reloadModels } = useSettings();
  const xl = useMedia(XL);

  const [draft, setDraft] = useState("");
  const [navOpen, setNavOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(true); // inline column at xl
  const [sourcesDrawer, setSourcesDrawer] = useState(false); // drawer below xl
  const [sourceMsg, setSourceMsg] = useState<string | null>(null);
  const [focus, setFocus] = useState<SourceFocus | null>(null);
  const composer = useRef<ComposerHandle>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);

  const activeId = active?.id ?? null;
  const replying = !!active?.sessionId && active.stage !== null && active.stage !== "DONE";
  const target = sourceTarget(active, sourceMsg);
  // answer_first has no side answers: its ANSWER is the main answer and each question brings its own sources
  const isSide = target && active && target.mode !== "answer_first"
    ? target.stage === "ANSWER" || target.sources[0]?.chunk_id !== active.topicSources[0]?.chunk_id
    : false;


  // Follow the reply as it streams, unless the student scrolled up to reread.
  useEffect(() => {
    const el = bottom.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => (pinned.current = !!e?.isIntersecting), { root: scroller.current, rootMargin: "0px 0px 80px 0px" });
    pinned.current = true;
    // A lesson opens at its latest message; the welcome opens at the top.
    if (activeId) el.scrollIntoView({ block: "end" });
    else scroller.current?.scrollTo({ top: 0 });
    io.observe(el);
    return () => io.disconnect();
  }, [activeId]);
  const lastText = active?.messages.at(-1);
  useEffect(() => {
    if (pinned.current && lastText) bottom.current?.scrollIntoView({ block: "end" });
  }, [lastText]);

  // Announce finished replies to screen readers once, not token by token.
  const announce =
    lastText?.role !== "tutor"
      ? ""
      : lastText.status === "done" && lastText.stage
        ? `Tutor replied. ${turnLabel(lastText.stage, lastText.analysis)}.`
        : lastText.status === "error"
          ? `Tutor reply failed. ${lastText.error ?? ""}`
          : "";

  const send = useCallback(
    (text: string) => {
      if (!text.trim() || busy) return;
      chat.send(text, model ?? "");
      setDraft("");
      setSourceMsg(null);
      pinned.current = true;
    },
    [chat, busy, model],
  );

  const onCite = useCallback(
    (msgId: string, ref: string) => {
      setSourceMsg(msgId);
      setFocus({ msgId, ref, nonce: Date.now() });
      if (xl) setSourcesOpen(true);
      else setSourcesDrawer(true);
    },
    [xl],
  );
  const onShowSources = useCallback(
    (msgId: string) => {
      setSourceMsg(msgId);
      setFocus(null);
      if (xl) setSourcesOpen(true);
      else setSourcesDrawer(true);
    },
    [xl],
  );
  const onRetry = useCallback((msgId: string) => chat.retry(msgId, model ?? ""), [chat, model]);
  const onRestore = useCallback((text: string) => {
    setDraft(text);
    composer.current?.focus();
  }, []);

  const panel = useMemo(
    () => ({
      sources: target?.sources ?? [],
      focused: focus && focus.msgId === target?.id ? focus : null,
      label: !target ? "Course material for your question" : isSide ? "Retrieved for your side question" : "Retrieved for this lesson's question",
    }),
    [target, focus, isSide],
  );
  const showInlineSources = xl && sourcesOpen && !!active;

  return (
    <div className="flex h-dvh overflow-hidden bg-bg text-ink">
      <a href="#composer" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-30 focus:rounded-control focus:bg-surface focus:px-3 focus:py-2">
        Skip to message box
      </a>

      <aside className="hidden w-[264px] shrink-0 border-r border-line lg:block" aria-label="Lessons and settings">
        <Sidebar />
      </aside>
      <Drawer open={navOpen} onClose={() => setNavOpen(false)} side="left" label="Lessons and settings">
        <Sidebar onNavigate={() => setNavOpen(false)} onClose={() => setNavOpen(false)} />
      </Drawer>

      <main className="relative flex min-w-0 flex-1 flex-col">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-80 bg-[radial-gradient(60%_100%_at_50%_0%,var(--ambient),transparent)]"
        />

        <header className="relative z-10 border-b border-line bg-bg">
          <div className="flex h-14 items-center gap-3 px-3 md:px-5">
            <button
              type="button"
              onClick={() => setNavOpen(true)}
              aria-label="Open lessons and settings"
              className="grid size-10 place-items-center rounded-control text-ink-2 hover:bg-surface-2 hover:text-ink lg:hidden"
            >
              <Menu size={20} aria-hidden />
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-ui font-semibold text-ink">{active?.title ?? "New lesson"}</p>
              <p className="truncate text-meta text-ink-3">
                {active?.model ? (
                  <>
                    Lesson model <span className="font-mono text-ink-2">{active.model}</span>
                  </>
                ) : (
                  "Threads and synchronization"
                )}
              </p>
            </div>
            <div className="hidden md:block">
              <StageRail conv={active} />
            </div>
            <button
              type="button"
              onClick={() => (xl ? setSourcesOpen((o) => !o) : setSourcesDrawer(true))}
              aria-expanded={xl ? sourcesOpen : sourcesDrawer}
              aria-controls={xl ? "sources-column" : undefined}
              className={[
                "flex h-9 items-center gap-1.5 rounded-control border px-2.5 text-meta font-semibold transition-colors",
                showInlineSources ? "border-accent-line bg-accent-soft text-accent" : "border-line text-ink-2 hover:bg-surface-2 hover:text-ink",
              ].join(" ")}
            >
              <BookOpen size={15} aria-hidden />
              <span className="max-sm:sr-only">Sources</span>
              {panel.sources.length > 0 && <span className="font-mono tabular-nums">{panel.sources.length}</span>}
            </button>
          </div>
          <div className="overflow-x-auto px-4 pb-2.5 md:hidden">
            <StageRail conv={active} compact />
          </div>
        </header>

        {(modelsStatus === "unreachable" || modelsStatus === "no-models") && (
          <div role="alert" className="relative z-10 border-b border-warning/25 bg-warning-soft px-4 py-2.5 md:px-6">
            <div className="mx-auto flex max-w-[46rem] flex-wrap items-center gap-x-3 gap-y-2 text-ui">
              <AlertTriangle size={16} className="shrink-0 text-warning" aria-hidden />
              <p className="min-w-0 flex-1 text-ink">
                {modelsStatus === "unreachable" ? (
                  <>
                    Can't reach the tutor server. Start it with <code className="font-mono text-meta">python3 -m src.tutor.server</code>.
                  </>
                ) : (
                  <>
                    The server can't list any Ollama models. Start Ollama and run <code className="font-mono text-meta">ollama pull qwen3:8b</code>.
                  </>
                )}
              </p>
              <button
                type="button"
                onClick={reloadModels}
                className="inline-flex h-8 items-center gap-1.5 rounded-control border border-line-strong bg-surface px-2.5 text-meta font-semibold text-ink hover:bg-surface-3"
              >
                <RefreshCw size={13} aria-hidden /> Check again
              </button>
            </div>
          </div>
        )}

        <div ref={scroller} className="relative flex-1 overflow-y-auto overscroll-contain">
          <div className="mx-auto max-w-[46rem] px-4 pb-6 pt-8 md:px-8">
            {active ? (
              <MessageList
                messages={active.messages}
                teacher={teacher}
                onCite={onCite}
                onShowSources={onShowSources}
                onRetry={onRetry}
                onRestore={onRestore}
              />
            ) : (
              <Welcome onPick={send} disabled={busy} />
            )}
            <div ref={bottom} className="h-px" />
          </div>
        </div>

        <div className="relative px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-1 md:px-8">
          <div className="mx-auto max-w-[46rem]">
            <Composer
              ref={composer}
              draft={draft}
              setDraft={setDraft}
              onSend={() => send(draft)}
              busy={busy}
              replying={replying}
              lessonModel={active?.model ?? null}
            />
            {busy && (
              <p className="mt-1.5 px-1 text-meta text-ink-3" aria-hidden>
                The tutor runs on a local model, so replies take a few seconds.
              </p>
            )}
          </div>
        </div>
      </main>

      {showInlineSources && (
        <aside id="sources-column" className="w-[360px] shrink-0 border-l border-line bg-rail" aria-label="Sources">
          <SourcesPanel {...panel} />
        </aside>
      )}
      <Drawer open={!xl && sourcesDrawer} onClose={() => setSourcesDrawer(false)} side="right" label="Sources">
        <SourcesPanel {...panel} onClose={() => setSourcesDrawer(false)} />
      </Drawer>

      <p className="sr-only" aria-live="polite">
        {announce}
      </p>
    </div>
  );
}
