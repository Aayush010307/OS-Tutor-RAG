import { lazy, Suspense, useEffect, useRef } from "react";
import { ChevronRight, FileText, Presentation, X } from "lucide-react";
import { formatLocation } from "../lib/tutor";
import type { Source } from "../types";

const Markdown = lazy(() => import("./Markdown"));
const noCite = () => {};

export interface SourceFocus {
  msgId: string;
  ref: string;
  /** Bumped on every click so the same citation clicked twice still scrolls and flashes. */
  nonce: number;
}

function SourceCard({ source, focused }: { source: Source; focused: SourceFocus | null }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const where = formatLocation(source.location);
  const isFocused = focused?.ref === source.ref;

  useEffect(() => {
    const el = ref.current;
    if (!isFocused || !el) return;
    el.open = true;
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    el.classList.remove("flash");
    void el.offsetWidth; // restart the animation
    el.classList.add("flash");
    el.querySelector("summary")?.focus({ preventScroll: true });
  }, [isFocused, focused?.nonce]);

  const Icon = /^slide/.test(source.location) ? Presentation : FileText;
  return (
    <details ref={ref} id={`source-${source.ref}`} className="group rounded-panel border border-line bg-surface open:border-line-strong">
      <summary className="flex cursor-pointer list-none gap-3 rounded-panel px-3.5 py-3 [&::-webkit-details-marker]:hidden">
        <span className="mt-px font-mono text-meta font-semibold text-accent">{source.ref}</span>
        <span className="min-w-0 flex-1">
          <span className="line-clamp-2 break-all text-ui text-ink" title={source.filename}>{source.filename}</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-meta text-ink-3">
            <span className="inline-flex items-center gap-1">
              <Icon size={13} aria-hidden />
              {where ?? "Page or slide not recorded"}
            </span>
            {source.section && <span className="break-words text-ink-2">{source.section}</span>}
          </span>
          {source.text && (
            // a glimpse of the passage while closed; the full passage is below when opened
            <span className="mt-1.5 line-clamp-2 text-meta text-ink-2 group-open:hidden">{source.text.replace(/\s+/g, " ")}</span>
          )}
        </span>
        <ChevronRight
          size={16}
          aria-hidden
          className="mt-0.5 shrink-0 text-ink-3 transition-transform duration-200 group-open:rotate-90"
        />
      </summary>
      <div className="border-t border-line px-3.5 pb-3.5 pt-3">
        <p className="mb-2 text-meta text-ink-3">Passage the tutor was given</p>
        <div className="passage max-h-80 overflow-y-auto pr-1">
          {source.text ? (
            <Suspense fallback={<p className="whitespace-pre-wrap text-ui text-ink-2">{source.text}</p>}>
              <Markdown text={source.text} sources={[]} onCite={noCite} />
            </Suspense>
          ) : (
            <p className="text-ui text-ink-3">The passage text was not returned for this source.</p>
          )}
        </div>
      </div>
    </details>
  );
}

interface Props {
  sources: Source[];
  focused: SourceFocus | null;
  onClose?: () => void;
  /** Whether these belong to a side answer rather than the lesson's own question. */
  label: string;
  /** True when the panel shows a reply (which may have used no passage), false before the first question. */
  forReply?: boolean;
}

export function SourcesPanel({ sources, focused, onClose, label, forReply = false }: Props) {
  return (
    <section aria-labelledby="sources-title" className="flex h-full flex-col">
      <header className="flex items-start justify-between gap-3 px-5 pb-3 pt-5">
        <div>
          <h2 id="sources-title" className="text-ui font-semibold text-ink">
            Sources
          </h2>
          <p className="mt-0.5 text-meta text-ink-3">{label}</p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sources"
            className="grid size-9 place-items-center rounded-control text-ink-3 hover:bg-surface-3 hover:text-ink"
          >
            <X size={18} aria-hidden />
          </button>
        )}
      </header>
      <div className="flex-1 overflow-y-auto px-5 pb-6">
        {sources.length ? (
          <ul className="flex flex-col gap-2.5">
            {sources.map((s) => (
              <li key={s.ref}>
                <SourceCard source={s} focused={focused} />
              </li>
            ))}
          </ul>
        ) : forReply ? (
          <p className="rounded-panel border border-dashed border-line px-4 py-5 text-ui text-ink-3">
            The tutor wrote this reply without course passages, so it cites none.
          </p>
        ) : (
          <p className="rounded-panel border border-dashed border-line px-4 py-5 text-ui text-ink-3">
            When you ask a question, the slides and textbook pages the tutor reads appear here. Select a citation such as{" "}
            <span className="font-mono text-accent">S1</span> in a reply to jump to its passage.
          </p>
        )}
      </div>
    </section>
  );
}
