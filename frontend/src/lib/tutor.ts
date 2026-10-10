import type { Analysis, Conversation, Level, Source, TurnStage, TutorMessage, TutorMode } from "../types";

/** Explanation rounds before the tutor gives the full answer (`max_rounds` in controller.py). */
export const MAX_EXPLAIN_ROUNDS = 2;

export const LESSON_STAGES = ["DIAGNOSE", "EXPLAIN", "CHECK", "DONE"] as const;
export type LessonStage = (typeof LESSON_STAGES)[number];

export const STAGE_INFO: Record<LessonStage, { name: string; hint: string }> = {
  DIAGNOSE: { name: "Diagnose", hint: "What do you already know?" },
  EXPLAIN: { name: "Explain", hint: "Filling the gap" },
  CHECK: { name: "Check", hint: "Try it yourself" },
  DONE: { name: "Done", hint: "Topic wrapped up" },
};

/**
 * Label for a finished tutor turn. DONE comes from two controller paths: WRAP_UP after a solid check answer, or
 * the full grounded ANSWER after the explanation rounds ran out (any non-solid analysis). In answer_first mode ANSWER
 * is the main answer, not a side answer. A stage this build does not know is shown as sent rather than crashing.
 */
export function turnLabel(stage: TurnStage, analysis: Analysis | null | undefined, mode?: TutorMode | null): string {
  if (stage === "ANSWER") return mode === "answer_first" ? "Answer" : "Side question";
  if (stage === "DONE") return analysis && analysis.level !== "solid" ? "Full answer" : "Wrap-up";
  if (stage === "FEEDBACK") return "Feedback";
  if (stage === "HINT") return "Hint";
  if (stage === "NO_CONTEXT") return "Not in the course material";
  return STAGE_INFO[stage as LessonStage]?.name ?? String(stage);
}

export const LEVEL_INFO: Record<Level, { name: string; tone: "success" | "warning" | "danger" | "muted" }> = {
  solid: { name: "Solid", tone: "success" },
  partial: { name: "Partly there", tone: "warning" },
  misconception: { name: "Misconception", tone: "danger" },
  unclear: { name: "Unclear or unsure", tone: "muted" },
};

/**
 * Turns [S1] markers into markdown links with a `cite:` scheme the renderer resolves, leaving fenced and inline
 * code untouched. Markers that point at no retrieved source are dropped: during streaming the text is not
 * yet validated by the server, which drops such markers from the final message.
 */
export function linkCitations(text: string, sources: Source[]): string {
  const refs = new Set(sources.map((s) => s.ref));
  return text
    .split(/(```[\s\S]*?(?:```|$)|`[^`\n]*`)/)
    .map((part, i) =>
      i % 2 ? part : part.replace(/(\s*)\[S(\d+)\]/g, (_m, sp: string, n: string) => (refs.has(`S${n}`) ? `${sp}[S${n}](cite:S${n})` : "")),
    )
    .join("");
}

/** "p.12" -> "Page 12", "slide 4" -> "Slide 4"; null when the server had no page or slide number. */
export function formatLocation(location: string): string | null {
  const m = /^(p\.|slide)\s*(\d+)$/.exec(location.trim());
  if (!m) return null;
  return `${m[1] === "p." ? "Page" : "Slide"} ${m[2]}`;
}

/** First non-empty user-facing line of a question, for titles. */
export function titleFrom(text: string): string {
  const line = text.trim().split("\n")[0] ?? "";
  return line.length > 72 ? `${line.slice(0, 71).trimEnd()}…` : line;
}

/**
 * Sources a reply starts with, before the server reports its own. A new topic starts empty. Socratic replies cite the
 * lesson's sources. Answer-first replies may use another context (the answer a check is about), so they start empty
 * and show only this request's `sources` event or the turn's own provenance, never a stale earlier set.
 */
export function replySources(conv: Conversation | null, opensTopic: boolean): Source[] {
  if (opensTopic || !conv || conv.mode === "answer_first") return [];
  return conv.topicSources;
}

/** Whether the tutor is waiting for the student's answer (composer wording). Older servers do not say: as before,
 * an open lesson stage counts as waiting. */
export function lessonAwaitsAnswer(conv: Conversation | null): boolean {
  if (!conv?.sessionId || conv.stage === null || conv.stage === "DONE") return false;
  return conv.awaitingAnswer ?? true;
}

/**
 * The reply whose passages the sources panel shows: the one a citation or "sources" click picked, else the latest
 * reply, even when it used no passage (it must not inherit an earlier reply's passages).
 */
export function sourceTarget(conv: Conversation | null, msgId: string | null): TutorMessage | null {
  const tutors = (conv?.messages ?? []).filter((m): m is TutorMessage => m.role === "tutor");
  return tutors.find((m) => m.id === msgId) ?? tutors.at(-1) ?? null;
}

export function sourcesLabel(target: TutorMessage | null, conv: Conversation | null): string {
  if (!target) return "Course material for your question";
  if (!target.sources.length) return "This reply did not use any course passages";
  if (target.mode === "answer_first" || conv?.mode === "answer_first") return "Passages this reply was based on";
  const side = target.stage === "ANSWER" || target.sources[0]?.chunk_id !== conv?.topicSources[0]?.chunk_id;
  return side ? "Retrieved for your side question" : "Retrieved for this lesson's question";
}
