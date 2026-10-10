// Wire types mirror src/tutor/server.py and src/tutor/controller.py exactly. The server is authoritative.

/** How the server teaches (`TUTOR_MODE`, sent in the `session` event). socratic is the default. */
export type TutorMode = "socratic" | "answer_first";

/**
 * Stage of a finished turn. In socratic mode ANSWER only ever marks a side answer to a new question asked
 * mid-lesson. answer_first mode (API_CONTRACT.md) sends ANSWER for its main answer, CHECK, FEEDBACK (reaction to a
 * check answer) and NO_CONTEXT (nothing relevant retrieved). HINT (both modes, newer servers) is a hint on the pending
 * question; like a side answer it leaves the lesson where it was. Other values are shown as sent, never a crash.
 */
export type TurnStage = "DIAGNOSE" | "EXPLAIN" | "CHECK" | "DONE" | "ANSWER" | "FEEDBACK" | "NO_CONTEXT" | "HINT";

/** `tutor_state` of a turn (newer servers). Socratic turns report the explanation rounds used; answer-first turns
 * report the conversation state. Older servers omit it. */
export interface TutorState {
  rounds?: number;
  max_rounds?: number;
  /** Socratic: whether the tutor is waiting for an answer (false after the explanation a lesson opens with). */
  awaiting_answer?: boolean;
  pending_check?: boolean;
}

export type Level = "solid" | "partial" | "misconception" | "unclear";

export interface Analysis {
  level: Level;
  gap: string;
}

/** One retrieved passage, from `source_cards` in server.py. `location` is "p.<n>" or "slide <n>". */
export interface Source {
  ref: string; // "S1", "S2", ...
  chunk_id: string;
  filename: string;
  section: string | null;
  location: string;
  text: string;
}

export interface ModelsResponse {
  models: string[];
  default: string;
}

export type ServerEvent =
  | { type: "session"; data: { id: string; model: string; mode?: TutorMode } }
  | { type: "sources"; data: Source[] }
  | { type: "analysis"; data: Analysis }
  | { type: "token"; data: { text: string } }
  /** `sources` (newer servers): the exact passages this turn's reply was generated from; its [Sn] refer to these.
   * [] when no passage was used. Absent from older servers, which keep the previous source handling. */
  | { type: "turn"; data: { stage: TurnStage; message: string; analysis: Analysis | null; sources?: Source[]; tutor_state?: TutorState } }
  | { type: "error"; data: { message: string } };

// ---- client state ----

export interface StudentMessage {
  id: string;
  role: "student";
  text: string;
  /** The tutor's judgement of this answer, from the `analysis` event (evaluator view only). */
  analysis?: Analysis;
  /** True when this message opened a new topic (sent to /api/start). */
  opensTopic: boolean;
}

/** retrieving: searching the course material; analysing: reading the student's answer; composing: waiting
 * for the first token; streaming: text arriving. */
export type TutorStatus = "retrieving" | "analysing" | "composing" | "streaming" | "done" | "error";

export interface TutorMessage {
  id: string;
  role: "tutor";
  text: string;
  status: TutorStatus;
  stage?: TurnStage;
  /** Mode of the session that produced this turn (labels ANSWER as an answer or a side answer). */
  mode?: TutorMode;
  /** Analysis attached to the finished turn, used to tell a wrap-up from a full answer at DONE. */
  analysis?: Analysis | null;
  sources: Source[];
  error?: string;
  /** For a failed /api/start: the question, so it can be asked again in a fresh session. */
  retryQuestion?: string;
}

export type Message = StudentMessage | TutorMessage;

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  /** Server session of the current topic; null before the first question or after an expired session. */
  sessionId: string | null;
  model: string | null;
  /** From the `session` event; absent in history saved before the server reported it. */
  mode?: TutorMode | null;
  /** From `tutor_state.awaiting_answer`; absent when the server did not send it. */
  awaitingAnswer?: boolean;
  /** Last lesson stage (side answers do not change it). */
  stage: Exclude<TurnStage, "ANSWER" | "HINT"> | null;
  explainRounds: number;
  /** Sources of the current topic's original question; replies that are not side answers cite these. */
  topicSources: Source[];
}
