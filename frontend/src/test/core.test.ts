import { describe, expect, it } from "vitest";
import { createEventParser } from "../lib/api";
import { formatLocation, linkCitations, turnLabel } from "../lib/tutor";
import { reducer, type State } from "../state/reducer";
import type { ServerEvent, Source, TutorMessage } from "../types";

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
