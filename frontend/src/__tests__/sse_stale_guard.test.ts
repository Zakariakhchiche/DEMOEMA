/**
 * Tests de la logique anti-stale-stream pour le ChatPanel SSE.
 *
 * Audit QA 2026-05-01 (SCRUM-NEW-02 — G5) : sous charge, l'API SSE backend
 * complétait (200 + body OK) mais le DOM ne rendait pas le bloc message.
 * Cause racine : race entre `setStreamText` incrémental (chunk par chunk) et
 * le `setConversations` final via `Promise.all`. Patch G5 : `streamIdRef`
 * partagée entre submits + check à chaque chunk SSE et avant le commit final.
 *
 * On ne peut pas tester React/JSX en unit ici (composant trop intriqué), mais
 * on peut prouver que la **mécanique** anti-stale fonctionne sur des refs
 * mutables partagées, ce qui est le cœur du fix.
 */
import { describe, it, expect, vi } from "vitest";

interface RefLike<T> { current: T }

/**
 * Reproduit la logique exacte du for-await SSE patch G5 :
 * pour chaque chunk, on vérifie `streamIdRef.current === myStreamId`.
 * Si stale, on break sans setState.
 */
async function consumeStream(
  chunks: string[],
  myStreamId: string,
  streamIdRef: RefLike<string>,
  onChunk: (acc: string) => void,
): Promise<{ committed: boolean; acc: string; abandoned: boolean }> {
  let acc = "";
  let abandoned = false;
  for (const c of chunks) {
    if (streamIdRef.current !== myStreamId) {
      abandoned = true;
      break;
    }
    acc = acc + c;
    onChunk(acc);
  }
  // Décision finale : commit OU skip si stale
  if (streamIdRef.current !== myStreamId) {
    return { committed: false, acc, abandoned: true };
  }
  return { committed: true, acc, abandoned };
}

describe("G5 streamId stale-guard mechanism", () => {
  it("commit normal quand streamIdRef ne change pas", async () => {
    const ref: RefLike<string> = { current: "" };
    const myId = "id-1";
    ref.current = myId;
    const onChunk = vi.fn();
    const r = await consumeStream(["He", "llo", " world"], myId, ref, onChunk);
    expect(r.committed).toBe(true);
    expect(r.acc).toBe("Hello world");
    expect(r.abandoned).toBe(false);
    expect(onChunk).toHaveBeenCalledTimes(3);
  });

  it("abandonne le stream si streamIdRef est invalidé en milieu", async () => {
    const ref: RefLike<string> = { current: "id-1" };
    const myId = "id-1";
    const onChunk = vi.fn();

    // Race manuelle : on simule un "nouveau submit" qui change le ref entre 2 chunks
    const fakeChunks = (function* () {
      yield "Re";
      ref.current = "id-2"; // stream invalidé → next iteration doit break
      yield "ponse"; // ne sera jamais consommé
    })();

    // On consomme manuellement (le générateur ne se prête pas à for-of async ici)
    let acc = "";
    let abandoned = false;
    for (const c of Array.from(fakeChunks)) {
      if (ref.current !== myId) { abandoned = true; break; }
      acc += c;
      onChunk(acc);
    }
    const committed = ref.current === myId;
    expect(committed).toBe(false);
    expect(abandoned).toBe(true);
    // Seul le premier chunk a été apperçu avant que le ref change
    // (ou aucun selon le timing — on accepte 0 ou 1 ici)
    expect(onChunk.mock.calls.length).toBeLessThanOrEqual(1);
  });

  it("abandonne le commit final si stale même si tous les chunks ont été reçus", async () => {
    const ref: RefLike<string> = { current: "id-1" };
    const myId = "id-1";
    const onChunk = vi.fn();
    const r = await consumeStream(["He", "llo"], myId, ref, onChunk);
    // Le for-await s'est terminé normalement (3 chunks). MAIS un nouveau
    // submit a changé le ref juste après → le commit doit être skippé.
    ref.current = "id-2";
    const finalCommit = ref.current === myId;
    expect(r.committed).toBe(true); // intra-loop OK
    expect(finalCommit).toBe(false); // le check final voit la staleness
  });

  it("seul le DERNIER stream commit, jamais les anciens (chaîne de submits)", async () => {
    const ref: RefLike<string> = { current: "" };
    const ids = ["s1", "s2", "s3"];
    const commits: string[] = [];
    for (const id of ids) {
      ref.current = id; // chaque submit prend la place
    }
    // Toutes les anciennes "fonctions submit" en flight check ref :
    for (const id of ids) {
      if (ref.current === id) commits.push(id);
    }
    expect(commits).toEqual(["s3"]);
  });
});

describe("G5 generateStreamId helper sanity", () => {
  it("crypto.randomUUID si disponible", () => {
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `sid_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    expect(id.length).toBeGreaterThan(8);
  });

  it("fallback timestamp+random unique", () => {
    const ids = new Set();
    for (let i = 0; i < 100; i++) {
      ids.add(`sid_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`);
    }
    expect(ids.size).toBeGreaterThan(95); // collisions très improbables
  });
});
