/**
 * Keeps Customer Master rendering bound to the newest request started by the view.
 *
 * A token/account transition can leave an older HTTP request in flight after a newer
 * request has started. React callers cannot distinguish those promises once they resolve,
 * so an older response could otherwise overwrite the current authorized view. Stale
 * completions adopt the newest request's result instead of exposing their own payload.
 * A request that throws before returning its promise never takes ownership of the view.
 */
export class CustomerMasterRequestGate<T> {
  private generation = 0;
  private latestRequest: Promise<T> | null = null;

  run(start: () => Promise<T>): Promise<T> {
    const generation = ++this.generation;
    let pending: Promise<T>;
    try {
      pending = start();
    } catch (error) {
      if (this.generation === generation) this.generation = generation - 1;
      throw error;
    }
    const guarded = pending.then(
      (value) => {
        if (generation !== this.generation) return this.latestRequest!;
        return value;
      },
      (error: unknown) => {
        if (generation !== this.generation) return this.latestRequest!;
        throw error;
      },
    );
    this.latestRequest = guarded;
    return guarded;
  }
}
