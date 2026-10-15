import { vi } from "vitest";

export type MockReply = { status?: number; body?: unknown; headers?: Record<string, string> } | Response;
export type Handler = MockReply | ((req: { url: string; method: string; headers: Headers; body: unknown }) => MockReply);

export type Call = { url: string; method: string; headers: Headers; body: unknown; credentials?: RequestCredentials };

/**
 * Routes are keyed "METHOD /path" (query string ignored unless the key contains "?").
 * Unmatched requests fail the test loudly. Nothing here touches the network.
 */
export function mockFetch(routes: Record<string, Handler>) {
  const calls: Call[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = (init?.method ?? "GET").toUpperCase();
    const headers = new Headers(init?.headers);
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    calls.push({ url, method, headers, body, credentials: init?.credentials });
    const path = url.split("?")[0];
    const handler = routes[`${method} ${url}`] ?? routes[`${method} ${path}`];
    if (!handler) throw new Error(`Unmocked request: ${method} ${url}`);
    const reply = typeof handler === "function" ? handler({ url, method, headers, body }) : handler;
    if (reply instanceof Response) return reply;
    const status = reply.status ?? 200;
    const noBody = status === 204;
    return new Response(noBody ? null : JSON.stringify(reply.body ?? {}), {
      status,
      headers: { "Content-Type": "application/json", ...reply.headers },
    });
  });
  vi.stubGlobal("fetch", fn);
  return { calls, fn, count: (key: string) => calls.filter((c) => `${c.method} ${c.url.split("?")[0]}` === key).length };
}
