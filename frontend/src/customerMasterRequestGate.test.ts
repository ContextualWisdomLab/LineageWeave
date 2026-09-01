import { describe, expect, it } from "vitest";
import { CustomerMasterRequestGate } from "./customerMasterRequestGate";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("CustomerMasterRequestGate", () => {
  it("prevents an older response from overwriting the newest Customer Master request", async () => {
    const gate = new CustomerMasterRequestGate<string>();
    const older = deferred<string>();
    const newer = deferred<string>();

    const olderResult = gate.run(() => older.promise);
    const newerResult = gate.run(() => newer.promise);

    older.resolve("old-account-view");
    newer.resolve("new-account-view");

    await expect(olderResult).resolves.toBe("new-account-view");
    await expect(newerResult).resolves.toBe("new-account-view");
  });

  it("ignores a stale request failure once a newer request owns the view", async () => {
    const gate = new CustomerMasterRequestGate<string>();
    const older = deferred<string>();
    const newer = deferred<string>();

    const olderResult = gate.run(() => older.promise);
    const newerResult = gate.run(() => newer.promise);

    older.reject(new Error("stale authorization failed"));
    newer.resolve("current-account-view");

    await expect(olderResult).resolves.toBe("current-account-view");
    await expect(newerResult).resolves.toBe("current-account-view");
  });

  it("does not supersede the current request when the next request cannot start", async () => {
    const gate = new CustomerMasterRequestGate<string>();
    const current = deferred<string>();
    const currentResult = gate.run(() => current.promise);

    expect(() =>
      gate.run(() => {
        throw new Error("request construction failed");
      }),
    ).toThrow("request construction failed");

    current.resolve("still-current-account-view");

    await expect(currentResult).resolves.toBe("still-current-account-view");
  });

  it("still surfaces a failure from the current request", async () => {
    const gate = new CustomerMasterRequestGate<string>();
    const current = deferred<string>();
    const result = gate.run(() => current.promise);

    current.reject(new Error("current request failed"));

    await expect(result).rejects.toThrow("current request failed");
  });
});
