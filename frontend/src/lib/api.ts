import type { ModelsResponse, ServerEvent } from "../types";

/** Raised when the tutor server itself cannot be reached or answers with a non-stream response. */
export class ServerUnavailable extends Error {}

export async function fetchModels(signal?: AbortSignal): Promise<ModelsResponse> {
  let res: Response;
  try {
    res = await fetch("/api/models", { signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ServerUnavailable("The tutor server is not reachable.");
  }
  if (!res.ok) throw new ServerUnavailable(`The tutor server answered ${res.status}.`);
  return (await res.json()) as ModelsResponse;
}

/**
 * Splits a server-sent event stream into parsed events. The server writes one `data: <json>` line per event,
 * separated by a blank line. Feed it decoded text chunks; it returns the complete events and keeps the rest.
 */
export function createEventParser() {
  let buffer = "";
  return (chunk: string): ServerEvent[] => {
    buffer += chunk;
    const events: ServerEvent[] = [];
    let end: number;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      for (const line of block.split("\n")) {
        if (!line.startsWith("data:")) continue;
        try {
          events.push(JSON.parse(line.slice(5).trim()) as ServerEvent);
        } catch {
          // a malformed line is dropped; the stream stays usable
        }
      }
    }
    return events;
  };
}

export type StartBody = { question: string; model: string };
export type ReplyBody = { session_id: string; text: string };

/**
 * POSTs to /api/start or /api/reply and calls `onEvent` for each event as it arrives. Resolves when the server
 * closes the stream. There is no reconnect: a turn is one request, and replaying it would duplicate the
 * student's answer in the server's session. Abort with `signal` (new lesson, page unload).
 */
export async function streamTurn(
  path: "/api/start" | "/api/reply",
  body: StartBody | ReplyBody,
  onEvent: (event: ServerEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ServerUnavailable("The tutor server is not reachable.");
  }
  if (!res.ok || !res.body) throw new ServerUnavailable(`The tutor server answered ${res.status}.`);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const parse = createEventParser();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    for (const event of parse(value)) onEvent(event);
  }
}
