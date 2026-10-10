import { ArrowUpRight } from "lucide-react";
import { LESSON_STAGES, STAGE_INFO } from "../lib/tutor";

// Questions the course corpus covers well (the old chat page's starters, from the tutor evaluation scenarios).
const STARTERS = [
  "Why does pthread_cond_wait take a mutex?",
  "What is the difference between a mutex and a semaphore?",
  "Why can the dining philosophers deadlock?",
  "What happens if two threads increment a shared counter?",
];

const HOW: Record<(typeof LESSON_STAGES)[number], string> = {
  DIAGNOSE: "Asks what you already know",
  EXPLAIN: "Explains only the missing piece",
  CHECK: "Gives you a question to try",
  DONE: "Sums up the key idea",
};

export function Welcome({ onPick, disabled }: { onPick: (q: string) => void; disabled: boolean }) {
  return (
    <div className="pb-10 pt-[min(10vh,5rem)]">
      <h1 className="text-title font-bold tracking-[-0.015em] text-ink text-balance">
        Ask about threads and synchronization.
      </h1>
      <p className="mt-3 max-w-[60ch] text-lead text-ink-2">
        The tutor won't hand you the answer straight away. It works through the idea with you, and every explanation
        links to the lecture slide or textbook page it comes from.
      </p>

      <ol className="mt-8 grid gap-x-6 gap-y-3 border-y border-line py-5 sm:grid-cols-2" aria-label="How a lesson runs">
        {LESSON_STAGES.map((s) => (
          <li key={s} className="flex items-baseline gap-3 text-ui">
            <span className="w-16 shrink-0 font-semibold text-accent">{STAGE_INFO[s].name}</span>
            <span className="text-ink-2">{HOW[s]}</span>
          </li>
        ))}
      </ol>

      <h2 className="mt-8 text-ui font-semibold text-ink-2">Try one of these</h2>
      <ul className="mt-2 flex flex-col">
        {STARTERS.map((q) => (
          <li key={q}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(q)}
              className="group -mx-3 flex w-[calc(100%+1.5rem)] items-center justify-between gap-4 rounded-control px-3 py-3 text-left text-body text-ink transition-colors hover:bg-surface-2 disabled:opacity-50"
            >
              <span>{q}</span>
              <ArrowUpRight
                size={16}
                aria-hidden
                className="shrink-0 text-ink-3 transition-colors group-hover:text-accent"
              />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
