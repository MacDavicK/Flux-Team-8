import { describe, expect, it } from "vitest";

describe("Frontend smoke test", () => {
  it("should confirm test infrastructure is working", () => {
    expect(true).toBe(true);
  });

  it("should have access to jsdom environment", () => {
    const div = document.createElement("div");
    div.textContent = "Flux";
    expect(div.textContent).toBe("Flux");
  });
});
