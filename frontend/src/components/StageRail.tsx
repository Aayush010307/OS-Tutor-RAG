import { Fragment } from "react";
import { LESSON_STAGES, MAX_EXPLAIN_ROUNDS, STAGE_INFO, type LessonStage } from "../lib/tutor";
import type { Conversation } from "../types";

const isLessonStage = (stage: string | undefined): stage is LessonStage =>
  (LESSON_STAGES as readonly string[]).includes(stage ?? "");

/** Stages the current topic has passed through, from the finished turns since the topic opened. */
function visitedStages(conv: Conversation): Set<LessonStage> {
  const seen = new Set<LessonStage>();
  for (const m of conv.messages) {
    if (m.role === "student" && m.opensTopic) seen.clear();
    if (m.role === "tutor" && m.status === "done" && isLessonStage(m.stage)) seen.add(m.stage);
  }
  return seen;
}

function Node({ stage, state }: { stage: LessonStage; state: "current" | "visited" | "idle" }) {
  const info = STAGE_INFO[stage];
  return (
    <li
      aria-current={state === "current" ? "step" : undefined}
      title={info.hint}
      className={`flex shrink-0 items-center gap-1.5 text-meta ${
        state === "current" ? "font-semibold text-accent" : state === "visited" ? "text-ink-2" : "text-ink-3"
      }`}
    >
      <span
        aria-hidden
        className={`size-2.5 rounded-full border transition-[background-color,border-color,box-shadow] duration-300 ${
          state === "current"
            ? "border-accent bg-accent shadow-[0_0_0_3px_var(--accent-soft)]"
            : state === "visited"
              ? "border-ink-3 bg-ink-3"
              : "border-line-strong bg-transparent"
        }`}
      />
      {info.name}
      <span className="sr-only">{state === "current" ? " (current stage)" : state === "visited" ? " (done)" : ""}</span>
    </li>
  );
}

/** A transition edge. The edge into the current state draws itself once when the lesson moves there. */
function Edge({ live, compact }: { live: boolean; compact: boolean }) {
  return (
    <li aria-hidden className={`relative h-px shrink-0 bg-line-strong ${compact ? "w-3" : "w-5"}`}>
      {live && <span className="edge-live absolute inset-0 bg-accent" />}
      <span className="absolute -right-px -top-[3px] size-[7px] rotate-45 border-r border-t border-line-strong" />
    </li>
  );
}

/**
 * The lesson drawn as the state diagram students know from the course: states joined by transitions, the current
 * one lit. A failed check sends the lesson back from Check to Explain, so that return edge is drawn as an arc and
 * carries the explanation round count. With no lesson (or before the first turn) every state is hollow.
 */
export function StageRail({ conv, compact = false }: { conv: Conversation | null; compact?: boolean }) {
  if (conv?.mode === "answer_first") return null; // the diagnose-explain-check diagram does not describe answer-first
  const current = conv?.stage ?? null;
  const visited = conv ? visitedStages(conv) : new Set<LessonStage>();
  const rounds = conv?.explainRounds ?? 0;
  const state = (s: LessonStage) => (s === current ? "current" : visited.has(s) ? "visited" : "idle");

  return (
    <nav aria-label="Lesson progress" className={compact ? "pt-3" : "pt-3.5"}>
      <ol className="flex items-center gap-2">
        {LESSON_STAGES.map((stage, i) => (
          <Fragment key={stage}>
            {i > 0 && stage !== "CHECK" && <Edge live={stage === current} compact={compact} />}
            {stage === "EXPLAIN" ? (
              // Explain -> Check, with the Check -> Explain return arc drawn above the pair.
              <li className="relative flex items-center gap-2">
                <span
                  aria-hidden
                  className={`pointer-events-none absolute -top-3 left-[5px] right-[5px] h-2.5 rounded-t-[8px] border border-b-0 ${
                    rounds > 0 ? "border-accent-line" : "border-line-strong"
                  }`}
                >
                  <span className="absolute -bottom-px -left-[4px] size-[7px] rotate-[135deg] border-r border-t border-inherit" />
                  {rounds > 0 && !compact && (
                    <span className="absolute -top-[7px] left-1/2 -translate-x-1/2 bg-bg px-1 font-mono text-[0.65rem] leading-3 tabular-nums text-accent">
                      {rounds}/{MAX_EXPLAIN_ROUNDS}
                    </span>
                  )}
                </span>
                <ol className="contents">
                  <Node stage="EXPLAIN" state={state("EXPLAIN")} />
                  <Edge live={current === "CHECK" && visited.has("EXPLAIN")} compact={compact} />
                  <Node stage="CHECK" state={state("CHECK")} />
                </ol>
              </li>
            ) : stage === "CHECK" ? null : (
              <Node stage={stage} state={state(stage)} />
            )}
          </Fragment>
        ))}
        {compact && rounds > 0 && (
          <li className="ml-1 shrink-0 font-mono text-meta tabular-nums text-accent" aria-hidden>
            {rounds}/{MAX_EXPLAIN_ROUNDS}
          </li>
        )}
      </ol>
      {current === "EXPLAIN" && (
        <p className="sr-only" aria-live="polite">
          Explanation round {rounds} of {MAX_EXPLAIN_ROUNDS}
        </p>
      )}
    </nav>
  );
}
