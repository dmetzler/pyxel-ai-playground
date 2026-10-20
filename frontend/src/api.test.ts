import { afterEach, describe, expect, it, vi } from "vitest";
import { streamChat } from "./api";

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
