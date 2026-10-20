export type Role = "user" | "assistant";
export interface ChatMessage {
  role: Role;
  content: string;
  // On a kid's message: the version of the game just before Pix answered it.
  commit?: string;
}

export interface ChatResult {
  commit: string;
  code: string;
  baseCode: string | null;
  resources: string | null;
  resourcesChanged: boolean;
}

/** Send one message to Pix and stream the reply. Pix edits the game's files
 * itself; the final event carries their new content. */
export async function streamChat(
  gameId: string,
  message: string,
  currentCode: string,
  history: ChatMessage[],
  onDelta: (chunk: string) => void,
  onTool: (name: string) => void,
  signal?: AbortSignal,
): Promise<ChatResult> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game_id: gameId, message, current_code: currentCode, history }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Erreur du serveur ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let error: string | null = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buf.indexOf("\n\n")) !== -1) {
      const event = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      const line = event.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const data = JSON.parse(line.slice(5));
      // An error still ends with a "done" carrying whatever Pix saved before it.
      if (data.error) error = data.error;
      if (data.delta) onDelta(data.delta);
      if (data.tool) onTool(data.tool);
      if (data.done) {
        const result = {
          commit: data.commit,
          code: data.code,
          baseCode: data.base_code,
          resources: data.resources,
          resourcesChanged: data.resources_changed,
        };
        if (error) throw Object.assign(new Error(error), { result });
        return result;
      }
    }
  }
  throw new Error(error ?? "La connexion avec Pix a été coupée.");
}

export interface GameSummary {
  id: string;
  name: string;
  updated: number;
}
export interface Game {
  id: string;
  name: string;
  code: string;
  base_code: string | null;
  messages: ChatMessage[];
  resources: string | null;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`Erreur du serveur ${res.status}`);
  return res.json();
}

export const listGames = () => fetch("/api/games").then((r) => json<GameSummary[]>(r));

export const loadGame = (id: string) => fetch(`/api/games/${id}`).then((r) => json<Game>(r));

export const createGame = (name: string, code: string, messages: ChatMessage[]) =>
  fetch("/api/games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, code, messages }),
  }).then((r) => json<{ id: string; name: string }>(r));

export const saveGame = (id: string, code: string, messages: ChatMessage[]) =>
  fetch(`/api/games/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, messages }),
  }).then((r) => json<{ ok: boolean }>(r));

export const saveResources = (id: string, data: string) =>
  fetch(`/api/games/${id}/resources`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data }),
  }).then((r) => json<{ ok: boolean }>(r));

/** Ask Pix to stop; the chat stream then ends normally with what was done. */
export const stopChat = (id: string) =>
  fetch(`/api/games/${id}/stop`, { method: "POST" }).then((r) => json<{ ok: boolean }>(r));

/** Put the game back to a version (the one before a message). */
export const undoTo = (id: string, commit: string) =>
  fetch(`/api/games/${id}/undo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ commit }),
  }).then((r) => json<{ code: string; base_code: string | null; resources: string | null }>(r));
