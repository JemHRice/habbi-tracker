/**
 * The celebration ladder has three rungs and no fourth. These tests exist as
 * much to pin down what must *never* happen as what should.
 */

import { describe, expect, it } from "vitest";

import { __testing } from "./useCelebrationLadder";

const { tierFor } = __testing;

describe("which rung fires", () => {
  it("celebrates halfway on the tick that reaches it", () => {
    expect(tierFor(5, 5)).toBe("halfway");
  });

  it("does not re-celebrate halfway once past it", () => {
    expect(tierFor(6, 4)).toBeNull();
  });

  it("encourages when one is left", () => {
    expect(tierFor(9, 1)).toBe("lastOne");
  });

  it("gives the big moment only when the day is done", () => {
    expect(tierFor(10, 0)).toBe("complete");
  });

  it("says nothing on an ordinary tick", () => {
    expect(tierFor(2, 8)).toBeNull();
  });

  it("says nothing at all on a rest day", () => {
    expect(tierFor(0, 0)).toBeNull();
  });

  it("never celebrates an untouched day just for being opened", () => {
    expect(tierFor(0, 6)).toBeNull();
  });

  it("only ever returns an encouraging rung", () => {
    const rungs = new Set<string | null>();
    for (let done = 0; done <= 12; done += 1) {
      for (let remaining = 0; remaining <= 12; remaining += 1) {
        rungs.add(tierFor(done, remaining));
      }
    }
    rungs.delete(null);

    expect([...rungs].sort()).toEqual(["complete", "halfway", "lastOne"]);
  });
});
