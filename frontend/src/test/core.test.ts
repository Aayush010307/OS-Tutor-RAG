import { describe, expect, it } from "vitest";
import { createEventParser } from "../lib/api";
import { formatLocation, linkCitations, replySources, turnLabel } from "../lib/tutor";
import { reducer, type State } from "../state/reducer";
import type { Conversation, ServerEvent, Source, TutorMessage } from "../types";

const src = (n: number, chunk = `doc::c${n}`): Source => ({
  ref: `S${n}`, chunk_id: chunk, filename: "doc.pdf", section: "Sec", location: `p.${n}`, text: "context",
});

describe("event parser", () => {
  it("parses events split across chunks and ignores malformed lines", () => {
    const parse = createEventParser();
    expect(parse('data: {"type":"session","data":{"id":"a","model":"m"}}\n\ndata: {"type":"tok')).toHaveLength(1);
    const rest = parse('en","data":{"text":"Hi"}}\n\ndata: not json\n\n');
    expect(rest).toEqual([{ type: "token", data: { text: "Hi" } }]);
  });
});

describe("citations", () => {
  it("links known refs, drops unknown ones, leaves code alone", () => {
    const out = linkCitations("A [S1] B [S9] `x[S1]`\n```c\nint a[S1];\n```", [src(1)]);
    expect(out).toContain("[S1](cite:S1)");
    expect(out).not.toContain("[S9]");
    expect(linkCitations("them [S1] [S9].", [src(1)])).toBe("them [S1](cite:S1).");
    expect(out).toContain("`x[S1]`");
    expect(out).toContain("int a[S1];");
  });
  it("formats locations without inventing them", () => {
    expect(formatLocation("p.12")).toBe("Page 12");
    expect(formatLocation("slide 4")).toBe("Slide 4");
    expect(formatLocation("slide None")).toBeNull();
  });
  it("tells a wrap-up from a full answer at DONE", () => {
    expect(turnLabel("DONE", { level: "solid", gap: "" })).toBe("Wrap-up");
    expect(turnLabel("DONE", { level: "partial", gap: "x" })).toBe("Full answer");
    expect(turnLabel("ANSWER", null)).toBe("Side question");
  });
});

describe("reducer", () => {
  const empty: State = { conversations: [], activeId: null, streaming: null };
  const tutor = (id: string, sources: Source[] = []): TutorMessage => ({ id, role: "tutor", text: "", status: "retrieving", sources });
  const ev = (s: State, msgId: string, event: ServerEvent, retryQuestion?: string) =>
    reducer(s, { type: "event", convId: "c", msgId, studentId: "s", event, retryQuestion });

  it("runs a lesson; a side answer keeps the stage and its own sources", () => {
    let s = reducer(empty, { type: "begin", convId: "c", title: "Q", opensTopic: true, tutor: tutor("t1"),
      student: { id: "s", role: "student", text: "Q", opensTopic: true } });
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "qwen3:8b" } });
    s = ev(s, "t1", { type: "sources", data: [src(1)] });
    s = reducer(s, { type: "token", convId: "c", msgId: "t1", text: "What [S1]" });
    s = ev(s, "t1", { type: "turn", data: { stage: "DIAGNOSE", message: "What? [S1]", analysis: null } });
    s = reducer(s, { type: "end", convId: "c", msgId: "t1" });
    let c = s.conversations[0]!;
    expect(c.stage).toBe("DIAGNOSE");
    expect(c.topicSources).toHaveLength(1);
    expect(s.streaming).toBeNull();

    // side question mid-lesson
    s = reducer(s, { type: "begin", convId: "c", title: "Q", opensTopic: false, tutor: tutor("t2", c.topicSources),
      student: { id: "s2", role: "student", text: "what is a mutex?", opensTopic: false } });
    s = ev(s, "t2", { type: "sources", data: [src(1, "other::c1")] });
    s = ev(s, "t2", { type: "turn", data: { stage: "ANSWER", message: "A lock.", analysis: null } });
    c = s.conversations[0]!;
    expect(c.stage).toBe("DIAGNOSE");
    expect(c.topicSources[0]!.chunk_id).toBe("doc::c1");
    expect((c.messages[3] as TutorMessage).sources[0]!.chunk_id).toBe("other::c1");
  });

  it("an expired session resets so the next message starts a new topic", () => {
    let s = reducer(empty, { type: "begin", convId: "c", title: "Q", opensTopic: true, tutor: tutor("t1"),
      student: { id: "s", role: "student", text: "Q", opensTopic: true } });
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "m" } });
    s = ev(s, "t1", { type: "turn", data: { stage: "DIAGNOSE", message: "?", analysis: null } });
    s = ev(s, "t1", { type: "error", data: { message: "This conversation has expired. Ask your question again." } });
    expect(s.conversations[0]!.sessionId).toBeNull();
  });

  it("a stream that ends without a turn does not spin forever", () => {
    let s = reducer(empty, { type: "begin", convId: "c", title: "Q", opensTopic: true, tutor: tutor("t1"),
      student: { id: "s", role: "student", text: "Q", opensTopic: true } });
    s = reducer(s, { type: "end", convId: "c", msgId: "t1" });
    expect((s.conversations[0]!.messages[1] as TutorMessage).status).toBe("error");
  });
});

describe("answer-first mode and unknown stages", () => {
  const empty: State = { conversations: [], activeId: null, streaming: null };
  const tutor = (id: string): TutorMessage => ({ id, role: "tutor", text: "", status: "retrieving", sources: [] });
  const ev = (s: State, msgId: string, event: ServerEvent) =>
    reducer(s, { type: "event", convId: "c", msgId, studentId: "s", event });

  it("labels every answer-first stage and never throws on a stage it does not know", () => {
    expect(turnLabel("FEEDBACK", { level: "partial", gap: "x" })).toBe("Feedback");
    expect(turnLabel("NO_CONTEXT", null)).toBe("Not in the course material");
    expect(turnLabel("ANSWER", null, "answer_first")).toBe("Answer");
    expect(turnLabel("ANSWER", null, "socratic")).toBe("Side question");
    expect(turnLabel("CHECK", null, "answer_first")).toBe("Check");
    expect(() => turnLabel("SUMMARY" as never, null)).not.toThrow();
    expect(turnLabel("SUMMARY" as never, null)).toBe("SUMMARY");
  });

  it("keeps the session's mode and every answer-first turn with its analysis", () => {
    let s = reducer(empty, { type: "begin", convId: "c", title: "Q", opensTopic: true, tutor: tutor("t1"),
      student: { id: "s", role: "student", text: "Q", opensTopic: true } });
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "qwen3:8b", mode: "answer_first" } });
    s = ev(s, "t1", { type: "sources", data: [src(1)] });
    s = ev(s, "t1", { type: "turn", data: { stage: "ANSWER", message: "A mutex [S1].", analysis: null } });
    s = reducer(s, { type: "begin", convId: "c", title: "Q", opensTopic: false, tutor: tutor("t2"),
      student: { id: "s2", role: "student", text: "answer", opensTopic: false } });
    s = ev(s, "t2", { type: "analysis", data: { level: "partial", gap: "ownership" } });
    s = ev(s, "t2", { type: "turn", data: { stage: "FEEDBACK", message: "Close.", analysis: { level: "partial", gap: "ownership" } } });
    s = reducer(s, { type: "begin", convId: "c", title: "Q", opensTopic: false, tutor: tutor("t3"),
      student: { id: "s3", role: "student", text: "how do I bake bread?", opensTopic: false } });
    s = ev(s, "t3", { type: "turn", data: { stage: "NO_CONTEXT", message: "The course material does not cover this.", analysis: null } });
    const c = s.conversations[0]!;
    expect(c.mode).toBe("answer_first");
    const turns = c.messages.filter((m): m is TutorMessage => m.role === "tutor");
    expect(turns.map((m) => [m.stage, m.mode])).toEqual([
      ["ANSWER", "answer_first"], ["FEEDBACK", "answer_first"], ["NO_CONTEXT", "answer_first"]]);
    expect(turns.map((m) => turnLabel(m.stage!, m.analysis, m.mode))).toEqual(["Answer", "Feedback", "Not in the course material"]);
    expect(turns[1]!.analysis?.level).toBe("partial");
    expect(turns[0]!.sources[0]!.ref).toBe("S1");
  });

  it("socratic sessions and history saved before the server sent a mode behave as before", () => {
    let s = reducer(empty, { type: "begin", convId: "c", title: "Q", opensTopic: true, tutor: tutor("t1"),
      student: { id: "s", role: "student", text: "Q", opensTopic: true } });
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "m" } }); // a v1 server sends no mode
    s = ev(s, "t1", { type: "turn", data: { stage: "DIAGNOSE", message: "?", analysis: null } });
    expect(s.conversations[0]!.mode).toBeNull();
    expect(s.conversations[0]!.stage).toBe("DIAGNOSE");
    expect(turnLabel("ANSWER", null, s.conversations[0]!.mode)).toBe("Side question");
  });
});

describe("turn-level source provenance", () => {
  const empty: State = { conversations: [], activeId: null, streaming: null };
  const cite = (ref: string, chunk_id: string, text: string): Source => ({
    ref, chunk_id, filename: "doc.pdf", section: "Sec", location: "p.3", text,
  });
  const A = [cite("S1", "vit::c0036", "Bakery Algorithm"), cite("S2", "vit::c0025", "compare and swap (CAS)")];
  const B = [cite("S1", "sema::c0002", "sem_wait() decrements"), cite("S2", "sema::c0003", "sem_post() increments")];
  const C = [cite("S1", "bugs::c0012", "Deadlock conditions")];
  const ids = (srcs: Source[]) => srcs.map((s) => s.chunk_id);
  const conv = (s: State) => s.conversations[0]!;
  const tutorMsg = (s: State, id: string) => conv(s).messages.find((m): m is TutorMessage => m.id === id)!;
  // a reply placeholder starts with the topic's sources, exactly as state/chat.tsx creates it
  const ask = (s: State, id: string, text: string, opensTopic = false) =>
    reducer(s, { type: "begin", convId: "c", title: "Q", opensTopic, student: { id: `s-${id}`, role: "student", text, opensTopic },
      tutor: { id, role: "tutor", text: "", status: "retrieving", sources: opensTopic ? [] : conv(s).topicSources } });
  const ev = (s: State, msgId: string, event: ServerEvent) =>
    reducer(s, { type: "event", convId: "c", msgId, studentId: `s-${msgId}`, event });

  it("Check and Feedback cite the answer they check (B), never an earlier question's sources (A)", () => {
    let s = ask(empty, "t1", "How do I bake sourdough bread?", true);
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "qwen3:8b", mode: "answer_first" } });
    s = ev(s, "t1", { type: "sources", data: A }); // shown while retrieving, then rejected by the server
    s = ev(s, "t1", { type: "turn", data: { stage: "NO_CONTEXT", message: "Not in the material.", analysis: null, sources: [] } });
    expect(tutorMsg(s, "t1").sources).toEqual([]); // NO_CONTEXT keeps no unrelated passages

    s = ask(s, "t2", "What do sem_wait and sem_post do?");
    s = ev(s, "t2", { type: "sources", data: B });
    s = ev(s, "t2", { type: "turn", data: { stage: "ANSWER", message: "It blocks [S1]; it wakes [S2].", analysis: null, sources: B } });
    s = ask(s, "t3", "test my understanding");
    s = ev(s, "t3", { type: "turn", data: { stage: "CHECK", message: "What does sem_wait do at 0? [S1]", analysis: null, sources: B } });
    s = ask(s, "t4", "it blocks until a post");
    s = ev(s, "t4", { type: "analysis", data: { level: "solid", gap: "" } });
    s = ev(s, "t4", { type: "turn", data: { stage: "FEEDBACK", message: "Right [S1], and post wakes it [S2].",
      analysis: { level: "solid", gap: "" }, sources: B } });

    expect(ids(conv(s).topicSources)).toEqual(ids(A)); // the stale state that caused the bug is still there...
    for (const id of ["t2", "t3", "t4"]) {
      expect(ids(tutorMsg(s, id).sources)).toEqual(ids(B)); // ...but every turn keeps its own provenance
      expect(ids(tutorMsg(s, id).sources).some((c) => ids(A).includes(c))).toBe(false);
    }
    // a click on [S1] / [S2] in the feedback opens that message's passage with the same ref: B, never A
    const feedback = tutorMsg(s, "t4");
    expect(linkCitations(feedback.text, feedback.sources)).toBe("Right [S1](cite:S1), and post wakes it [S2](cite:S2).");
    expect(feedback.sources.find((x) => x.ref === "S1")!.chunk_id).toBe("sema::c0002");
    expect(feedback.sources.find((x) => x.ref === "S2")!.text).toBe("sem_post() increments");
  });

  it("an older server without turn sources keeps the previous behaviour", () => {
    let s = ask(empty, "t1", "Q", true);
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "m" } });
    s = ev(s, "t1", { type: "sources", data: B });
    s = ev(s, "t1", { type: "turn", data: { stage: "DIAGNOSE", message: "What do you know? [S1]", analysis: null } });
    s = ask(s, "t2", "an answer");
    s = ev(s, "t2", { type: "turn", data: { stage: "EXPLAIN", message: "Close [S2].", analysis: null } });
    expect(ids(tutorMsg(s, "t1").sources)).toEqual(ids(B));
    expect(ids(tutorMsg(s, "t2").sources)).toEqual(ids(B)); // the topic's sources, as before
  });

  it("socratic stages are unchanged and a side question keeps its own sources", () => {
    let s = ask(empty, "t1", "Q", true);
    s = ev(s, "t1", { type: "session", data: { id: "sid", model: "m", mode: "socratic" } });
    s = ev(s, "t1", { type: "sources", data: B });
    s = ev(s, "t1", { type: "turn", data: { stage: "DIAGNOSE", message: "?", analysis: null, sources: B } });
    s = ask(s, "t2", "What is a deadlock?");
    s = ev(s, "t2", { type: "sources", data: C });
    s = ev(s, "t2", { type: "turn", data: { stage: "ANSWER", message: "Four conditions [S1].", analysis: null, sources: C } });
    s = ask(s, "t3", "my answer");
    s = ev(s, "t3", { type: "turn", data: { stage: "EXPLAIN", message: "Not quite [S2].", analysis: null, sources: B } });
    expect(conv(s).stage).toBe("EXPLAIN");
    expect(conv(s).explainRounds).toBe(1);
    expect(ids(conv(s).topicSources)).toEqual(ids(B));
    expect(ids(tutorMsg(s, "t2").sources)).toEqual(ids(C));
    expect(ids(tutorMsg(s, "t3").sources)).toEqual(ids(B));
    expect(turnLabel("ANSWER", null, tutorMsg(s, "t2").mode)).toBe("Side question");
  });
});

describe("reply placeholders", () => {
  const src2 = (ref: string, chunk_id: string): Source => ({ ref, chunk_id, filename: "f", section: null, location: "p.1", text: "t" });
  const base = (mode: Conversation["mode"]): Conversation => ({
    id: "c", title: "Q", createdAt: 0, updatedAt: 0, messages: [], sessionId: "sid", model: "m", mode,
    stage: "CHECK", explainRounds: 0, topicSources: [src2("S1", "vit::c0036")],
  });

  it("answer-first replies never start with an earlier question's sources; socratic replies keep the lesson's", () => {
    expect(replySources(base("answer_first"), false)).toEqual([]);
    expect(replySources(base("socratic"), false).map((s) => s.chunk_id)).toEqual(["vit::c0036"]);
    expect(replySources(base(null), false).map((s) => s.chunk_id)).toEqual(["vit::c0036"]); // v1 server: as before
    expect(replySources(base("socratic"), true)).toEqual([]);
    expect(replySources(null, false)).toEqual([]);
  });
});
