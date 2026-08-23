import { describe, expect, it } from "vitest";
import { BackendError } from "./api";
import { productExceptionCopy } from "./productExceptionCopy";

describe("productExceptionCopy", () => {
  it("keeps the 503 product title and names a next action", () => {
    const copy = productExceptionCopy(new BackendError("/api/chat", 503, "gateway exploded"), "Chat");
    expect(copy.title).toBe("Chat is temporarily unavailable. Saved evidence is still available.");
    expect(copy.description.toLowerCase()).toMatch(/retry|saved evidence/);
    expect(copy.title).not.toMatch(/gateway exploded/i);
  });

  it("does not render raw exception types, stacks, or 5xx provider detail", () => {
    const raw = new Error("TypeError: Cannot read properties of undefined (reading 'choices')\n    at chat_completion_content");
    const copy = productExceptionCopy(raw, "Ask Agent");
    expect(copy.title).not.toMatch(/TypeError|choices|chat_completion_content|Traceback/i);
    expect(copy.description).not.toMatch(/TypeError|choices|Traceback/i);
    expect(copy.title).toMatch(/Ask Agent could not be completed/);
    expect(copy.description.toLowerCase()).toMatch(/retry/);
  });

  it("does not interpolate HTTP 5xx provider payloads", () => {
    const copy = productExceptionCopy(
      new BackendError("/api/ask", 502, "Internal Server Error: OPENROUTER_API_KEY missing"),
      "Ask",
    );
    expect(copy.title).not.toMatch(/OPENROUTER_API_KEY|Internal Server Error|502/i);
    expect(copy.description.toLowerCase()).toMatch(/retry/);
  });

  it("keeps client-actionable validation text when it is not a raw exception", () => {
    const copy = productExceptionCopy(
      new BackendError("/api/tenant", 422, "Copyright year must be an integer."),
      "Tenant settings",
    );
    expect(copy.title).toBe("Copyright year must be an integer.");
    expect(copy.description.toLowerCase()).toMatch(/correct|retry/);
  });
});
