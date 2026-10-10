import { lazy, memo, Suspense, useCallback } from "react";
import { AlertTriangle, BookOpen, CornerDownLeft, RotateCcw, Stethoscope } from "lucide-react";
import { CopyButton } from "./CopyButton";

// The markdown renderer and syntax highlighter are most of the bundle; load them with the first reply.
const Markdown = lazy(() => import("./Markdown"));
import { LEVEL_INFO, turnLabel } from "../lib/tutor";
import type { Message, StudentMessage, TutorMessage } from "../types";

const WAITING: Record<string, string> = {
  retrieving: "Searching the course material",
  analysing: "Reading your answer",
  composing: "Writing",
};

const TONE = {
  success: "text-success bg-success-soft",
  warning: "text-warning bg-warning-soft",
  danger: "text-danger bg-danger-soft",
  muted: "text-ink-2 bg-surface-2",
} as const;

const StudentBubble = memo(function StudentBubble({ msg, teacher }: { msg: StudentMessage; teacher: boolean }) {
  const level = msg.analysis ? LEVEL_INFO[msg.analysis.level] : null;
  return (
    <div className="flex flex-col items-end gap-2">
      <div className="max-w-[min(85%,36rem)] whitespace-pre-wrap rounded-panel border border-line bg-surface-2 px-4 py-2.5 text-body text-ink">
        <span className="sr-only">You: </span>
        {msg.text}
      </div>
      {teacher && msg.analysis && level && (
        <div className="flex max-w-[min(85%,36rem)] items-start gap-2 text-meta text-ink-2">
          <Stethoscope size={14} className="mt-0.5 shrink-0 text-ink-3" aria-hidden />
          <p>
            <span className="text-ink-3">Tutor's read: </span>
            <span className={`rounded px-1.5 py-0.5 font-semibold ${TONE[level.tone]}`}>{level.name}</span>
            {msg.analysis.gap && <span className="ml-1.5">{msg.analysis.gap}</span>}
          </p>
        </div>
      )}
    </div>
  );
});

interface TutorProps {
  msg: TutorMessage;
  onCite: (msgId: string, ref: string) => void;
  onShowSources: (msgId: string) => void;
  onRetry: (msgId: string) => void;
  onRestore: (text: string) => void;
  /** The student's message this replies to, so a failed reply can be put back in the composer. */
  prompt: string;
}

const TutorReply = memo(function TutorReply({ msg, onCite, onShowSources, onRetry, onRestore, prompt }: TutorProps) {
  const waiting = msg.status in WAITING && !msg.text;
  const streaming = msg.status === "streaming" || (msg.status === "composing" && !!msg.text);
  const cite = useCallback((ref: string) => onCite(msg.id, ref), [onCite, msg.id]);

  return (
    <article className="group" aria-busy={msg.status !== "done" && msg.status !== "error"}>
      <header className="mb-2 flex h-6 items-center gap-2 text-meta">
        <span className="font-semibold text-ink-2">Tutor</span>
        {msg.stage && (
          <span className="rounded-[5px] border border-line px-1.5 py-px font-semibold text-accent">
            {turnLabel(msg.stage, msg.analysis, msg.mode)}
          </span>
        )}
      </header>

      {waiting && (
        <p className="flex items-center gap-2.5 text-ui text-ink-2" role="status">
          <span className="wait-dots inline-flex gap-1" aria-hidden>
            <span />
            <span />
            <span />
          </span>
          {WAITING[msg.status]}…
        </p>
      )}

      {msg.text && (
        <div className={streaming ? "streaming" : undefined}>
          <Suspense fallback={<p className="whitespace-pre-wrap text-body text-ink">{msg.text}</p>}>
            <Markdown text={msg.text} sources={msg.sources} onCite={cite} />
          </Suspense>
        </div>
      )}

      {msg.status === "error" && (
        <div role="alert" className="mt-3 flex flex-col gap-3 rounded-panel border border-danger/30 bg-danger-soft px-4 py-3 text-ui">
          <p className="flex items-start gap-2 text-ink">
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-danger" aria-hidden />
            <span>{msg.error}</span>
          </p>
          <div className="flex flex-wrap gap-2 pl-6">
            {msg.retryQuestion ? (
              <button
                type="button"
                onClick={() => onRetry(msg.id)}
                className="inline-flex h-9 items-center gap-1.5 rounded-control border border-line-strong bg-surface px-3 font-semibold text-ink hover:bg-surface-3"
              >
                <RotateCcw size={14} aria-hidden /> Ask again
              </button>
            ) : (
              prompt && (
                <button
                  type="button"
                  onClick={() => onRestore(prompt)}
                  className="inline-flex h-9 items-center gap-1.5 rounded-control border border-line-strong bg-surface px-3 font-semibold text-ink hover:bg-surface-3"
                >
                  <CornerDownLeft size={14} aria-hidden /> Put my answer back
                </button>
              )
            )}
          </div>
        </div>
      )}

      {msg.status === "done" && (
        <footer className="-ml-2 mt-2 flex items-center gap-1">
          <CopyButton text={msg.text} label="Copy reply" />
          {msg.sources.length > 0 && (
            <button
              type="button"
              onClick={() => onShowSources(msg.id)}
              className="inline-flex h-8 items-center gap-1.5 rounded-control px-2 text-meta text-ink-3 transition-colors hover:bg-surface-3 hover:text-ink"
            >
              <BookOpen size={14} aria-hidden /> {msg.sources.length} sources
            </button>
          )}
        </footer>
      )}
    </article>
  );
});

interface ListProps extends Omit<TutorProps, "msg" | "prompt"> {
  messages: Message[];
  teacher: boolean;
}

export function MessageList({ messages, teacher, ...handlers }: ListProps) {
  return (
    <ol className="flex flex-col gap-8">
      {messages.map((m, i) => {
        const prev = messages[i - 1];
        return (
          <li key={m.id}>
            {m.role === "student" && m.opensTopic && i > 0 && (
              <div className="mb-8 flex items-center gap-3 text-meta text-ink-3" role="separator">
                <span className="h-px flex-1 bg-line" />
                New topic
                <span className="h-px flex-1 bg-line" />
              </div>
            )}
            {m.role === "student" ? (
              <StudentBubble msg={m} teacher={teacher} />
            ) : (
              <TutorReply msg={m} prompt={prev?.role === "student" ? prev.text : ""} {...handlers} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
