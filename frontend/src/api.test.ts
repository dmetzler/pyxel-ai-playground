import { afterEach, describe, expect, it, vi } from "vitest";
import { deleteGame, importGame, streamChat } from "./api";

const done = { done: true, commit: "abc1234", code: "new", base_code: "old", resources: null, resources_changed: false };

function serve(chunks: string[], status = 200) {
  const enc = new TextEncoder();
  const body = new ReadableStream({
    start(c) {
      chunks.forEach((s) => c.enqueue(enc.encode(s)));
      c.close();
    },
  });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status })));
}

const sse = (...events: object[]) => events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");

afterEach(() => vi.unstubAllGlobals());

describe("streamChat", () => {
  it("streams text and tools, then returns the saved game", async () => {
    const all = sse({ delta: "Sal" }, { tool: "write" }, { delta: "ut é" }, done);
    // Cut the stream at awkward places, including inside a multi-byte character.
    const bytes = new TextEncoder().encode(all);
    const cut = [7, 31, all.indexOf("é") + 6];
    const dec = new TextDecoder();
    serve([0, ...cut].map((s, k) => dec.decode(bytes.slice(s, cut[k] ?? bytes.length), { stream: true })));

    const deltas: string[] = [];
    const tools: string[] = [];
    const result = await streamChat("jeu", "hi", "old", [], (d) => deltas.push(d), (t) => tools.push(t));
    expect(deltas.join("")).toBe("Salut é");
    expect(tools).toEqual(["write"]);
    expect(result).toEqual({ commit: "abc1234", code: "new", baseCode: "old", resources: null, resourcesChanged: false });
  });

  it("throws the error but still hands back what Pix saved", async () => {
    serve([sse({ error: "Pix a eu un problème" }, done)]);
    const err = await streamChat("jeu", "hi", "", [], () => {}, () => {}).catch((e) => e);
    expect(err.message).toBe("Pix a eu un problème");
    expect(err.result.code).toBe("new");
  });

  it("reports a cut connection", async () => {
    serve([sse({ delta: "a" })]);
    await expect(streamChat("jeu", "hi", "", [], () => {}, () => {})).rejects.toThrow("La connexion avec Pix a été coupée.");
  });

  it("reports server errors", async () => {
    serve([""], 409);
    await expect(streamChat("jeu", "hi", "", [], () => {}, () => {})).rejects.toThrow("Erreur du serveur 409");
  });
});

const reply = (status: number, body: object) =>
  vi.fn(async (..._args: unknown[]) => new Response(JSON.stringify(body), { status }));

describe("manage games", () => {
  it("imports a zip file as the raw body", async () => {
    const fetch = reply(200, { id: "mon-jeu-2", name: "Mon jeu" });
    vi.stubGlobal("fetch", fetch);
    const file = new File(["PK"], "mon-jeu.zip", { type: "application/zip" });
    expect(await importGame(file)).toEqual({ id: "mon-jeu-2", name: "Mon jeu" });
    const [url, init] = fetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/games/import");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/zip" });
    expect(init.body).toBe(file);
  });

  it("shows the server's French message when an import is refused", async () => {
    vi.stubGlobal("fetch", reply(400, { detail: "Ce fichier zip ne contient pas de jeu (game.py manquant)." }));
    await expect(importGame(new File(["x"], "x.zip"))).rejects.toThrow("game.py manquant");
  });

  it("deletes a game, or says why it cannot", async () => {
    const ok = reply(200, { ok: true });
    vi.stubGlobal("fetch", ok);
    expect(await deleteGame("mon-jeu")).toEqual({ ok: true });
    expect(ok.mock.calls[0]).toEqual(["/api/games/mon-jeu", { method: "DELETE" }]);

    vi.stubGlobal("fetch", reply(409, { detail: "Pix travaille encore sur ce jeu." }));
    await expect(deleteGame("mon-jeu")).rejects.toThrow("Pix travaille encore sur ce jeu.");
  });
});
