import { forwardRef, useImperativeHandle, useLayoutEffect, useRef } from "react";
import { ArrowUp, Cpu } from "lucide-react";
import { useSettings } from "../state/settings";

export interface ComposerHandle {
  focus: () => void;
}

interface Props {
  draft: string;
  setDraft: (v: string) => void;
  onSend: () => void;
  busy: boolean;
  /** An open lesson: the next message is a reply to the tutor's question. */
  replying: boolean;
  /** The tutor asked something and waits for the answer; false after an explanation that asked nothing. */
  awaitingAnswer: boolean;
  /** Model the open lesson runs on, when it differs from the selection. */
  lessonModel: string | null;
}

export const Composer = forwardRef<ComposerHandle, Props>(function Composer(
  { draft, setDraft, onSend, busy, replying, awaitingAnswer, lessonModel },
  handle,
) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const { models, model, setModel, modelsStatus } = useSettings();
  useImperativeHandle(handle, () => ({ focus: () => ref.current?.focus() }));

  // Grow with the text up to a cap, then scroll.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [draft]);

  const canSend = draft.trim().length > 0 && !busy;
  const pendingSwitch = replying && lessonModel && model && lessonModel !== model;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSend) onSend();
      }}
      className="rounded-composer border border-line-strong bg-surface shadow-float transition-colors focus-within:border-accent-line"
    >
      <label htmlFor="composer" className="sr-only">
        {awaitingAnswer ? "Your answer" : "Your question"}
      </label>
      <textarea
        id="composer"
        ref={ref}
        rows={1}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            if (canSend) onSend();
          }
        }}
        placeholder={
          awaitingAnswer
            ? "Your answer, or a new question"
            : replying
              ? "Ask a follow-up, or say “quiz me” to try a question"
              : "Ask about threads, locks or deadlock"
        }
        aria-describedby="composer-hint"
        className="block max-h-[220px] w-full resize-none bg-transparent px-4 pb-2 pt-3.5 text-body text-ink outline-none placeholder:text-ink-3 focus-visible:outline-none"
      />
      <div className="flex items-center gap-2 px-2.5 pb-2.5">
        <label className="relative flex h-8 min-w-0 items-center gap-1.5 rounded-control px-2 text-meta text-ink-2 hover:bg-surface-2 focus-within:outline-2 focus-within:outline-accent">
          <Cpu size={14} aria-hidden className="shrink-0 text-ink-3" />
          <span className="sr-only">Model for new questions</span>
          <select
            value={model ?? ""}
            onChange={(e) => setModel(e.target.value)}
            disabled={modelsStatus !== "ready"}
            className="min-w-0 cursor-pointer appearance-none truncate bg-transparent pr-1 font-mono text-meta text-ink-2 outline-none disabled:cursor-default"
          >
            {modelsStatus === "ready" ? (
              models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))
            ) : (
              <option value={model ?? ""}>
                {modelsStatus === "loading" ? "Loading models…" : (model ?? "Server default")}
              </option>
            )}
          </select>
        </label>
        <p id="composer-hint" className="min-w-0 flex-1 truncate text-meta text-ink-3">
          {pendingSwitch ? (
            <>This lesson stays on {lessonModel}; {model} starts with your next new question.</>
          ) : (
            <span className="max-sm:hidden">Enter to send, Shift+Enter for a new line</span>
          )}
        </p>
        <button
          type="submit"
          disabled={!canSend}
          aria-label={awaitingAnswer ? "Send answer" : "Ask"}
          className="grid size-9 shrink-0 place-items-center rounded-control bg-accent-strong text-on-accent transition-[background-color,transform,opacity] hover:brightness-110 active:scale-95 disabled:bg-surface-3 disabled:text-ink-3"
        >
          <ArrowUp size={18} strokeWidth={2.25} aria-hidden />
        </button>
      </div>
    </form>
  );
});
