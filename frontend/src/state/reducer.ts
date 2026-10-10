import type { Conversation, Message, ServerEvent, StudentMessage, TutorMessage } from "../types";

export interface State {
  conversations: Conversation[];
  activeId: string | null;
  /** The one reply in flight. Events are applied by conversation and message id, never to "whatever is open". */
  streaming: { convId: string; msgId: string } | null;
}

export type Action =
  | { type: "select"; id: string | null }
  | { type: "remove"; id: string }
  | { type: "begin"; convId: string; title: string; student: StudentMessage | null; tutor: TutorMessage; opensTopic: boolean }
  | { type: "token"; convId: string; msgId: string; text: string }
  | { type: "event"; convId: string; msgId: string; studentId: string; event: ServerEvent; retryQuestion?: string }
  | { type: "end"; convId: string; msgId: string }
  | { type: "fail"; convId: string; msgId: string; error: string; retryQuestion?: string };

// ponytail: the server reports an expired session only as text; match it here, a typed code if it ever gets one.
const EXPIRED = /expired/i;

function updateConv(state: State, id: string, fn: (c: Conversation) => Conversation): State {
  return { ...state, conversations: state.conversations.map((c) => (c.id === id ? fn(c) : c)) };
}

function updateTutor(c: Conversation, msgId: string, fn: (m: TutorMessage) => TutorMessage): Conversation {
  return { ...c, messages: c.messages.map((m) => (m.id === msgId && m.role === "tutor" ? fn(m) : m)) };
}

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "select":
      return { ...state, activeId: action.id };

    case "remove":
      return {
        ...state,
        conversations: state.conversations.filter((c) => c.id !== action.id),
        activeId: state.activeId === action.id ? null : state.activeId,
        streaming: state.streaming?.convId === action.id ? null : state.streaming,
      };

    case "begin": {
      const now = Date.now();
      const exists = state.conversations.some((c) => c.id === action.convId);
      const base: Conversation = exists
        ? state.conversations.find((c) => c.id === action.convId)!
        : {
            id: action.convId,
            title: action.title,
            createdAt: now,
            updatedAt: now,
            messages: [],
            sessionId: null,
            model: null,
            stage: null,
            explainRounds: 0,
            topicSources: [],
          };
      let messages: Message[];
      if (action.student) messages = [...base.messages, action.student, action.tutor];
      else messages = base.messages.map((m) => (m.id === action.tutor.id ? action.tutor : m)); // retry in place
      const conv: Conversation = {
        ...base,
        messages,
        updatedAt: now,
        ...(action.opensTopic ? { sessionId: null, stage: null, explainRounds: 0, topicSources: [], awaitingAnswer: undefined } : {}),
      };
      // Most recent conversation first.
      const others = state.conversations.filter((c) => c.id !== conv.id);
      return {
        conversations: [conv, ...others],
        activeId: conv.id,
        streaming: { convId: conv.id, msgId: action.tutor.id },
      };
    }

    case "token":
      return updateConv(state, action.convId, (c) =>
        updateTutor(c, action.msgId, (m) => ({ ...m, status: "streaming", text: m.text + action.text })),
      );

    case "event": {
      const { event, msgId } = action;
      return updateConv(state, action.convId, (c) => {
        switch (event.type) {
          case "session":
            return { ...c, sessionId: event.data.id, model: event.data.model, mode: event.data.mode ?? null };
          case "sources":
            // At /api/start these are the topic's sources; mid-lesson they belong to a side answer only.
            return updateTutor(
              c.sessionId && c.stage === null ? { ...c, topicSources: event.data } : c,
              msgId,
              (m) => ({ ...m, sources: event.data, status: m.status === "streaming" ? m.status : "composing" }),
            );
          case "analysis":
            return updateTutor(
              {
                ...c,
                messages: c.messages.map((m) => (m.id === action.studentId && m.role === "student" ? { ...m, analysis: event.data } : m)),
              },
              msgId,
              (m) => ({ ...m, status: "composing" }),
            );
          case "token":
            return updateTutor(c, msgId, (m) => ({ ...m, status: "streaming", text: m.text + event.data.text }));
          case "turn": {
            const { stage, message, analysis, sources, tutor_state } = event.data;
            // newer servers say whether a question is pending (false after the explanation a lesson opens with)
            const awaiting = typeof tutor_state?.awaiting_answer === "boolean" ? { awaitingAnswer: tutor_state.awaiting_answer } : {};
            const next = { ...updateTutor(c, msgId, (m) => ({
              ...m,
              status: "done",
              stage,
              mode: c.mode ?? undefined,
              analysis,
              // the server's own provenance for this turn wins; older servers omit it and keep the previous sources
              sources: sources ?? m.sources,
              text: message || m.text, // the server's validated text replaces the raw stream
              error: undefined,
              retryQuestion: undefined,
            })), ...awaiting };
            if (stage === "ANSWER" || stage === "HINT") return next; // side answer or hint: the tutor's question stays pending
            // newer servers report the rounds used ("I'm not sure" uses none); older ones: count EXPLAIN turns as before
            const rounds = typeof tutor_state?.rounds === "number" ? tutor_state.rounds : c.explainRounds + (stage === "EXPLAIN" ? 1 : 0);
            return { ...next, stage, explainRounds: rounds };
          }
          case "error": {
            const next = updateTutor(c, msgId, (m) => ({
              ...m,
              status: "error",
              error: event.data.message,
              retryQuestion: action.retryQuestion,
            }));
            return EXPIRED.test(event.data.message) || action.retryQuestion ? { ...next, sessionId: null, stage: null } : next;
          }
        }
      });
    }

    case "end":
      return {
        ...updateConv(state, action.convId, (c) =>
          // A stream that closed without a turn or an error event still must not spin forever.
          updateTutor(c, action.msgId, (m) =>
            m.status === "done" || m.status === "error"
              ? m
              : { ...m, status: "error", error: "The tutor stopped without finishing this reply." },
          ),
        ),
        streaming: null,
      };

    case "fail":
      return {
        ...updateConv(state, action.convId, (c) => {
          const next = updateTutor(c, action.msgId, (m) => ({ ...m, status: "error", error: action.error, retryQuestion: action.retryQuestion }));
          return action.retryQuestion ? { ...next, sessionId: null, stage: null } : next;
        }),
        streaming: null,
      };
  }
}
