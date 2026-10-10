import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from "react";
import { ServerUnavailable, streamTurn } from "../lib/api";
import { titleFrom } from "../lib/tutor";
import { useSettings } from "./settings";
import type { Conversation, Message, ServerEvent, StudentMessage, TutorMessage } from "../types";
import { reducer, type State } from "./reducer";

const STORAGE_KEY = "os-tutor:conversations";
const MAX_SAVED = 30;

function load(): Conversation[] {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as Conversation[];
    // A reply that was still streaming when the page closed can never finish: mark it instead of spinning.
    return saved.map((c) => ({
      ...c,
      messages: c.messages.map((m): Message =>
        m.role === "tutor" && m.status !== "done" && m.status !== "error"
          ? { ...m, status: "error", error: "This reply was interrupted when the page closed." }
          : m,
      ),
    }));
  } catch {
    return [];
  }
}

function save(conversations: Conversation[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, MAX_SAVED)));
  } catch {
    // storage full or blocked: history just is not kept
  }
}

const uid = () => crypto.randomUUID();

interface ChatApi {
  state: State;
  active: Conversation | null;
  busy: boolean;
  send: (text: string, model: string) => void;
  retry: (tutorMessageId: string, model: string) => void;
  newLesson: () => void;
  select: (id: string) => void;
  remove: (id: string) => void;
}

const ChatContext = createContext<ChatApi | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, () => ({ conversations: load(), activeId: null, streaming: null }));
  const abortRef = useRef<AbortController | null>(null);
  const { reloadModels } = useSettings();

  // Persist only between turns: saving on every token would rewrite storage dozens of times a second.
  useEffect(() => {
    if (!state.streaming) save(state.conversations);
  }, [state.conversations, state.streaming]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = useCallback(
    async (conv: Conversation | null, studentText: string, model: string, opts: { reuseTutorId?: string } = {}) => {
      if (abortRef.current) return; // one reply in flight at a time
      const convId = conv?.id ?? uid();
      // An open lesson takes every message as a reply: the server decides whether it is an answer or a new
      // question (answered on the side, with the tutor's question kept pending). Only a finished or missing
      // session starts a new topic.
      const opensTopic = !conv?.sessionId || conv.stage === "DONE";
      const student: StudentMessage = { id: uid(), role: "student", text: studentText, opensTopic };
      const tutor: TutorMessage = {
        id: opts.reuseTutorId ?? uid(),
        role: "tutor",
        text: "",
        status: opensTopic ? "retrieving" : "analysing",
        sources: opensTopic ? [] : (conv?.topicSources ?? []),
      };
      dispatch({
        type: "begin",
        convId,
        title: titleFrom(studentText),
        student: opts.reuseTutorId ? null : student,
        tutor,
        opensTopic,
      });

      const controller = new AbortController();
      abortRef.current = controller;
      // Tokens arrive far faster than the screen refreshes; batch them into one update per frame.
      let pending = "";
      let frame = 0;
      const flush = () => {
        frame = 0;
        if (pending) dispatch({ type: "token", convId, msgId: tutor.id, text: pending });
        pending = "";
      };
      const onEvent = (event: ServerEvent) => {
        if (controller.signal.aborted) return;
        if (event.type === "token") {
          pending += event.data.text;
          if (!frame) frame = requestAnimationFrame(flush);
          return;
        }
        if (frame) cancelAnimationFrame(frame);
        flush();
        dispatch({ type: "event", convId, msgId: tutor.id, studentId: student.id, event, retryQuestion: opensTopic ? studentText : undefined });
      };

      try {
        if (opensTopic) await streamTurn("/api/start", { question: studentText, model }, onEvent, controller.signal);
        else await streamTurn("/api/reply", { session_id: conv!.sessionId!, text: studentText }, onEvent, controller.signal);
        if (frame) cancelAnimationFrame(frame);
        flush();
        dispatch({ type: "end", convId, msgId: tutor.id });
      } catch (e) {
        if (frame) cancelAnimationFrame(frame);
        if ((e as Error).name === "AbortError") {
          dispatch({
            type: "fail",
            convId,
            msgId: tutor.id,
            error: "Stopped because you started a new lesson.",
            retryQuestion: opensTopic ? studentText : undefined,
          });
          return;
        }
        // The banner (driven by /api/models) states the cause and the command; the thread only says what happened.
        if (e instanceof ServerUnavailable) reloadModels();
        const message =
          e instanceof ServerUnavailable
            ? "The tutor server didn't answer, so this wasn't sent."
            : "The connection to the tutor dropped before the reply finished.";
        dispatch({ type: "fail", convId, msgId: tutor.id, error: message, retryQuestion: opensTopic ? studentText : undefined });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [reloadModels],
  );

  const api = useMemo<ChatApi>(() => {
    const active = state.conversations.find((c) => c.id === state.activeId) ?? null;
    return {
      state,
      active,
      busy: state.streaming !== null,
      send: (text, model) => void run(active, text.trim(), model),
      // Retry is offered only for a failed new topic: a fresh /api/start never duplicates server-side state.
      retry: (tutorId, model) => {
        const msg = active?.messages.find((m) => m.id === tutorId);
        if (active && msg?.role === "tutor" && msg.retryQuestion)
          void run({ ...active, sessionId: null }, msg.retryQuestion, model, { reuseTutorId: tutorId });
      },
      newLesson: () => {
        abortRef.current?.abort();
        dispatch({ type: "select", id: null });
      },
      select: (id) => dispatch({ type: "select", id }),
      remove: (id) => {
        if (state.streaming?.convId === id) abortRef.current?.abort();
        dispatch({ type: "remove", id });
      },
    };
  }, [state, run]);

  return <ChatContext.Provider value={api}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatApi {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat outside ChatProvider");
  return ctx;
}
