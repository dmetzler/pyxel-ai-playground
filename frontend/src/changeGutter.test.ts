import { describe, expect, it } from "vitest";
import { diffLines } from "./changeGutter";

const lines = (...l: string[]) => l.join("\n");

describe("diffLines", () => {
  it("marks nothing when the code is the same", () => {
    expect(diffLines(lines("a", "b"), lines("a", "b")).size).toBe(0);
  });

  it("marks inserted lines as added", () => {
    const d = diffLines(lines("a", "b"), lines("a", "x", "y", "b"));
    expect([...d]).toEqual([[1, "added"], [2, "added"]]);
  });

  it("marks replaced lines as changed", () => {
    const d = diffLines(lines("a", "b", "c"), lines("a", "B", "c"));
    expect([...d]).toEqual([[1, "changed"]]);
  });

  it("marks removed lines on the line that follows them", () => {
    const d = diffLines(lines("a", "b", "c"), lines("a", "c"));
    expect([...d]).toEqual([[1, "deleted"]]);
  });

  it("puts a deletion at the end on the last line", () => {
    const d = diffLines(lines("a", "b", "c"), lines("a", "b"));
    expect([...d]).toEqual([[1, "deleted"]]);
  });

  it("gives up on huge files instead of freezing", () => {
    const big = Array.from({ length: 3001 }, (_, i) => `l${i}`).join("\n");
    expect(diffLines(big, big + "\nnew").size).toBe(0);
  });
});
