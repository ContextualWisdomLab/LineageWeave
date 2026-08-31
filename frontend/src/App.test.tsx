import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { SurfaceBoundary } from "./App";
import { optionalKnowledgeCutoffIso } from "./api";
import { setLocale } from "./i18n";
import { OIDC_RETURN_URL_STORAGE_KEY } from "./oidcReturnUrl";

const signinRedirect = vi.fn();
const signoutRedirect = vi.fn();
let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

beforeEach(() => {
  setLocale("en");
  signinRedirect.mockReset();
  signoutRedirect.mockReset();
  mockAuth = {
    isLoading: false,
    isAuthenticated: false,
    error: undefined,
    user: undefined,
    signinRedirect,
    signoutRedirect,
  };
});

it("normalizes valid knowledge cutoffs and rejects invalid input", () => {
  expect(optionalKnowledgeCutoffIso("")).toBeUndefined();
  expect(optionalKnowledgeCutoffIso("2026-01-15T12:00")).toBe(
    new Date("2026-01-15T12:00").toISOString(),
  );
  expect(() => optionalKnowledgeCutoffIso("not-a-date")).toThrow(
    "invalid knowledge cutoff",
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
  window.sessionStorage.clear();
  window.localStorage.clear();
  vi.restoreAllMocks();
});


it("announces a lazy surface load failure with a recovery action", () => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  const BrokenSurface = () => {
    throw new Error("synthetic chunk failure");
  };

  const { rerender } = render(
    <SurfaceBoundary key="failed-post">
      <BrokenSurface />
    </SurfaceBoundary>,
  );

  expect(screen.getByRole("alert")).toHaveTextContent(
    "This view is unavailable. Refresh once; if it fails again, contact your administrator.",
  );
  expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();

  rerender(
    <SurfaceBoundary key="next-post">
      <span>Recovered surface</span>
    </SurfaceBoundary>,
  );
  expect(screen.getByText("Recovered surface")).toBeInTheDocument();
});


describe("App, unauthenticated", () => {
  it("shows a login button that starts the real OIDC redirect", async () => {
    window.history.replaceState({}, "", "/?post=abc#evidence");
    render(<App showLabPanels />);
    expect(screen.queryByRole("heading", { name: /admin settings/i })).toBeNull();
    const button = screen.getByRole("button", { name: /log in/i });
    await userEvent.click(button);
    expect(signinRedirect).toHaveBeenCalledTimes(1);
    expect(signinRedirect).toHaveBeenCalledWith(
      expect.objectContaining({
        state: { returnUrl: "/?post=abc#evidence" },
      }),
    );
    // Persisted as a fallback in case the OIDC state round-trip is dropped
    // (see oidcReturnUrl.ts's restoreOidcReturnUrl, consumed in main.tsx).
    expect(window.sessionStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY)).toMatch(/^\//);
    expect(window.localStorage.getItem(OIDC_RETURN_URL_STORAGE_KEY)).toMatch(/^\//);
  });

  it("announces the app-root auth loading gate as a live region", () => {
    mockAuth = { ...mockAuth, isLoading: true };
    render(<App showLabPanels />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading authentication state...");
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 });
}

describe("App, authenticated", () => {
  beforeEach(() => {
    mockAuth = {
      ...mockAuth,
      isAuthenticated: true,
      user: {
        access_token: "test-access-token",
        profile: { preferred_username: "demo.analyst" },
      },
    };
  });

  function stubBackend(options?: {
    admin?: boolean;
    calendarCommitments?: unknown[];
    rankings?: {
      status?: "accepted" | "unavailable";
      status_reason?: string | null;
      rankings?: {
        post_id: string;
        post_title: string;
        fused_rank: number;
        channel_evidence?: {
          signal_code: string;
          signal_label: string;
          channel_rank: number;
          weight: number;
          contribution: number;
          rank: number;
        }[];
      }[];
    };
    chatUnavailable?: boolean;
    evidenceUnavailable?: boolean;
    searchUnavailable?: boolean;
    verificationEvidenceUrl?: string | null;
    failedLineageRun?: boolean;
    runningLineageRun?: boolean;
    failedReportRun?: boolean;
    succeededReportRun?: boolean;
    succeededTeppRun?: boolean;
    pendingTeppRun?: boolean;
    pluralAffiliations?: boolean;
    deferMe?: boolean;
    deferPostOne?: boolean;
    meFailed?: boolean;
    postBody?: string;
    manyCustomerHints?: number;
    hintRelatedPosts?: boolean;
    customerEntityHierarchy?: boolean;
    staleSummary?: boolean;
    contentAfterSummary?: boolean;
    organizationAliases?: boolean;
    combinedVoices?: boolean;
    omitVoiceOptions?: boolean;
    askLineageGraph?: boolean;
    askImageCitation?: boolean;
    askDelivery?: boolean;
    lineageIsolationReason?: "comparison_candidates_available" | "no_comparison_group";
  }): ReturnType<typeof vi.fn> & { releaseMe: () => void; releasePostOne: () => void } {
    const statusLabel: Record<string, string> = {
      open: "Open",
      in_progress: "In progress",
      closed: "Closed",
    };
    const tickets: {
      issue_ticket_id: string;
      post_id: string;
      ticket_status_code: string;
      ticket_status_label?: string;
      ticket_title: string;
      assigned_account_id: null;
      due_date: string | null;
      commitment_summary: string | null;
      created_at: string;
      updated_at: string;
    }[] = [];
    let nextTicketId = 1;
    const events: { event_id: string; event_type: string; actor_account_id: string; summary: string }[] = [];
    let nextEventId = 1;
    let createdPendingLineage: Record<string, unknown> | null = null;
    let createdPendingTepp: Record<string, unknown> | null = null;
    let resolvedHintCode: string | null = null;
    let contentRequests = 0;

    let releaseMe = () => {};
    const demoOrgAlias = options?.organizationAliases ? { organization_alias: "DC" } : {};
    const meReady = options?.deferMe
      ? new Promise<void>((resolve) => {
          releaseMe = resolve;
        })
      : Promise.resolve();

    let releasePostOne = () => {};
    const postOneReady = options?.deferPostOne
      ? new Promise<void>((resolve) => {
          releasePostOne = resolve;
        })
      : Promise.resolve();

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/settings")) {
        return Promise.resolve(jsonResponse({ brandName: "LineageWeave" }));
      }
      if (url.endsWith("/api/me/preferences") && method === "PATCH") {
        const body = JSON.parse(String(init?.body));
        return Promise.resolve(jsonResponse({ preferred_locale: body.preferred_locale }));
      }
      if (url.endsWith("/api/me")) {
        return meReady.then(() => {
          if (options?.meFailed) {
            return new Response(JSON.stringify({ detail: "unavailable" }), {
              status: 500,
              headers: { "Content-Type": "application/json" },
            });
          }
          return jsonResponse({
            user_account_id: options?.admin ? "acct-admin" : "acct-1",
            display_name: options?.admin ? "Demo Admin" : "Demo Analyst",
            permission_codes: options?.admin ? ["post_read", "post_admin"] : ["post_read"],
            corporate_entities: options?.pluralAffiliations
              ? [
                  { corporate_entity_id: "corp-demo", entity_name: "Demo Corp" },
                  { corporate_entity_id: "corp-north", entity_name: "Northridge Grid" },
                ]
              : [{ corporate_entity_id: "corp-demo", entity_name: "Demo Corp" }],
          });
        });
      }
      if (url.endsWith("/api/lineage/rebuild") && method === "POST") {
        return Promise.resolve(jsonResponse({ edge_count: 4 }));
      }
      if (url.endsWith("/api/posts/post-1/tickets") && method === "GET") {
        return Promise.resolve(jsonResponse({ tickets }));
      }
      if (url.endsWith("/api/posts/post-1/tickets") && method === "POST") {
        const body = JSON.parse(String(init?.body));
        const ticket = {
          issue_ticket_id: `ticket-${nextTicketId++}`,
          post_id: "post-1",
          ticket_status_code: body.ticket_status_code,
          ticket_status_label: statusLabel[body.ticket_status_code] ?? body.ticket_status_code,
          ticket_title: body.ticket_title,
          assigned_account_id: null,
          due_date: body.due_date ?? null,
          commitment_summary: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        };
        tickets.unshift(ticket);
        events.unshift({
          event_id: `event-${nextEventId++}`,
          event_type: "ticket_created",
          actor_account_id: "acct-admin",
          summary: `Ticket created: ${ticket.ticket_title}`,
        });
        return Promise.resolve(new Response(JSON.stringify(ticket), { status: 201 }));
      }
      if (url.match(/\/api\/tickets\/ticket-\d+$/) && method === "PATCH") {
        const ticketId = url.split("/").pop();
        const body = JSON.parse(String(init?.body));
        const ticket = tickets.find((t) => t.issue_ticket_id === ticketId);
        if (!ticket) return Promise.resolve(new Response(null, { status: 404 }));
        ticket.ticket_status_code = body.ticket_status_code;
        ticket.ticket_status_label = statusLabel[body.ticket_status_code] ?? body.ticket_status_code;
        events.unshift({
          event_id: `event-${nextEventId++}`,
          event_type: "ticket_status_changed",
          actor_account_id: "acct-admin",
          summary: `Ticket status changed to ${statusLabel[body.ticket_status_code] ?? body.ticket_status_code}`,
        });
        return Promise.resolve(jsonResponse(ticket));
      }
      if (url.endsWith("/api/posts/post-1/activity") && method === "GET") {
        return Promise.resolve(jsonResponse({ events }));
      }
      if (url.endsWith("/api/posts/post-1/derive-commitment") && method === "POST") {
        if (options?.chatUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Commitment extraction is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
              }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        const ticket = {
          issue_ticket_id: `ticket-${nextTicketId++}`,
          post_id: "post-1",
          ticket_status_code: "open",
          ticket_status_label: "Open",
          ticket_title: "Send the revised delivery schedule",
          assigned_account_id: null,
          due_date: "2026-01-09",
          commitment_summary: "Send the revised delivery schedule",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        };
        tickets.unshift(ticket);
        return Promise.resolve(
          jsonResponse({ post_id: "post-1", has_commitment: true, ticket }),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-report")) {
        const reportSucceeded = !options?.failedReportRun;
        return Promise.resolve(
          jsonResponse({
            analysis_run_id: "run-demo-report",
            run_kind_code: "analysis_run_report",
            run_kind_label: "Period report",
            scope_kind_code: "analysis_scope_corporate_entity",
            scope_kind_label: "Corporate entity",
            scope_entity_name: "Demo Corp",
            scope_key: "2026-W02",
            scope_grouping_key: "corp-1",
            status_code: reportSucceeded ? "analysis_status_succeeded" : "analysis_status_failed",
            status_label: reportSucceeded ? "Succeeded" : "Failed",
            knowledge_cutoff: "2026-01-12T12:00:00Z",
            requested_at: "2026-01-12T12:38:00Z",
            source_counts: [
              {
                count_type_code: "analysis_count_document",
                count_type_label: "Documents",
                count_value: 3,
              },
            ],
            visible_posts: reportSucceeded
              ? [{ post_id: "post-1", post_title: "Public post" }]
              : [],
            status_history: reportSucceeded
              ? [
                  {
                    status_ordinal: 1,
                    status_code: "analysis_status_pending",
                    status_label: "Pending",
                    occurred_at: "2026-01-12T12:39:00Z",
                  },
                  {
                    status_ordinal: 2,
                    status_code: "analysis_status_running",
                    status_label: "Running",
                    occurred_at: "2026-01-12T12:40:00Z",
                  },
                  {
                    status_ordinal: 3,
                    status_code: "analysis_status_succeeded",
                    status_label: "Succeeded",
                    occurred_at: "2026-01-12T12:41:00Z",
                  },
                ]
              : [
                  {
                    status_ordinal: 1,
                    status_code: "analysis_status_pending",
                    status_label: "Pending",
                    occurred_at: "2026-01-12T12:39:00Z",
                  },
                  {
                    status_ordinal: 2,
                    status_code: "analysis_status_failed",
                    status_label: "Failed",
                    occurred_at: "2026-01-12T12:40:00Z",
                    failure_code: "period_report_rebuild_failed",
                  },
                ],
          }),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-tepp-pending")) {
        return Promise.resolve(
          jsonResponse(
            createdPendingTepp ?? {
              analysis_run_id: "run-demo-tepp-pending",
              run_kind_code: "analysis_run_tepp",
              run_kind_label: "TEPP measurement",
              scope_kind_code: "analysis_scope_corporate_entity",
              scope_kind_label: "Corporate entity",
              scope_entity_name: "Demo Corp",
              status_code: "analysis_status_pending",
              status_label: "Pending",
              knowledge_cutoff: "2026-01-12T12:00:00Z",
              requested_at: "2026-01-12T12:41:00Z",
              source_counts: [],
              visible_posts: [{ post_id: "post-1", post_title: "Public post" }],
              status_history: [
                {
                  status_ordinal: 1,
                  status_code: "analysis_status_pending",
                  status_label: "Pending",
                  occurred_at: "2026-01-12T12:41:00Z",
                },
              ],
            },
          ),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-tepp")) {
        const teppStatus = options?.succeededTeppRun
          ? "analysis_status_succeeded"
          : options?.pendingTeppRun
            ? "analysis_status_pending"
            : "analysis_status_failed";
        const teppLabel = options?.succeededTeppRun
          ? "Succeeded"
          : options?.pendingTeppRun
            ? "Pending"
            : "Failed";
        return Promise.resolve(
          jsonResponse({
            analysis_run_id: "run-demo-tepp",
            run_kind_code: "analysis_run_tepp",
            run_kind_label: "TEPP measurement",
            scope_kind_code: "analysis_scope_corporate_entity",
            scope_kind_label: "Corporate entity",
            scope_entity_name: "Demo Corp",
            status_code: teppStatus,
            status_label: teppLabel,
            knowledge_cutoff: "2026-01-12T12:00:00Z",
            requested_at: "2026-01-12T12:34:00Z",
            ...(options?.succeededTeppRun
              ? {
                  tepp_accepted_receipt: {
                    remote_run_id: "tepp-remote-run-1",
                    accepted_status_code: "accepted",
                    received_at: "2026-01-12T12:36:00Z",
                  },
                }
              : {}),
            source_counts: [
              {
                count_type_code: "analysis_count_document",
                count_type_label: "Documents",
                count_value: 3,
              },
            ],
            visible_posts: [{ post_id: "post-1", post_title: "Public post" }],
            status_history: options?.pendingTeppRun
              ? [
                  {
                    status_ordinal: 1,
                    status_code: "analysis_status_pending",
                    status_label: "Pending",
                    occurred_at: "2026-01-12T12:35:00Z",
                  },
                ]
              : [
                  {
                    status_ordinal: 1,
                    status_code: "analysis_status_pending",
                    status_label: "Pending",
                    occurred_at: "2026-01-12T12:35:00Z",
                  },
                  {
                    status_ordinal: 2,
                    status_code: "analysis_status_running",
                    status_label: "Running",
                    occurred_at: "2026-01-12T12:36:00Z",
                  },
                  {
                    status_ordinal: 3,
                    status_code: options?.succeededTeppRun
                      ? "analysis_status_succeeded"
                      : "analysis_status_failed",
                    status_label: options?.succeededTeppRun ? "Succeeded" : "Failed",
                    occurred_at: "2026-01-12T12:37:00Z",
                    ...(options?.succeededTeppRun
                      ? {}
                      : { failure_code: "tepp_not_available" }),
                  },
                ],
          }),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-lineage")) {
        return Promise.resolve(
          jsonResponse({
            analysis_run_id: "run-demo-lineage",
            run_kind_code: "analysis_run_lineage",
            run_kind_label: "Lineage reconstruction",
            scope_kind_code: "analysis_scope_corporate_entity",
            scope_kind_label: "Corporate entity",
            scope_entity_name: "Demo Corp",
            status_code: options?.runningLineageRun
              ? "analysis_status_running"
              : options?.failedLineageRun
                ? "analysis_status_failed"
                : "analysis_status_succeeded",
            status_label: options?.runningLineageRun
              ? "Running"
              : options?.failedLineageRun
                ? "Failed"
                : "Succeeded",
            knowledge_cutoff: "2026-01-12T12:00:00Z",
            requested_at: "2026-01-12T12:30:00Z",
            source_counts: [
              {
                count_type_code: "analysis_count_document",
                count_type_label: "Documents",
                count_value: 3,
              },
            ],
            visible_posts: [
              {
                post_id: "post-1",
                post_title: "Public post",
                updated_at: "2026-01-13T09:00:00Z",
                live_after_cutoff: true,
              },
              {
                post_id: "post-2",
                post_title: "Private post",
                updated_at: "2026-01-10T12:00:00Z",
                live_after_cutoff: false,
              },
            ],
            reconstructed_edges: [
              {
                parent_post_id: "post-2",
                parent_post_title: "Pricing renegotiation follow-up",
                child_post_id: "post-1",
                child_post_title: "Pricing renegotiation: revised quote sent",
                fused_score: 0.72,
              },
              {
                parent_post_id: "post-2",
                parent_post_title: "Pricing renegotiation follow-up",
                child_post_id: "post-delivery",
                child_post_title: "Delivery schedule question raised",
                fused_score: 0.68,
              },
            ],
            reconstruction_result_sha256: "aa".repeat(32),
            outbox_deliveries: [
              {
                delivery_ordinal: 1,
                delivery_status_code: "analysis_outbox_claimed",
                delivery_status_label: "Claimed",
                occurred_at: "2026-01-12T12:32:00Z",
              },
              {
                delivery_ordinal: 2,
                delivery_status_code: "analysis_outbox_delivered",
                delivery_status_label: "Delivered",
                occurred_at: "2026-01-12T12:33:00Z",
              },
            ],
            code_revision_sha: "abcdef0123456789deadbeefcafebabe",
            configuration_sha256:
              "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            status_history: [
              {
                status_ordinal: 1,
                status_code: "analysis_status_pending",
                status_label: "Pending",
                occurred_at: "2026-01-12T12:31:00Z",
              },
              {
                status_ordinal: 2,
                status_code: "analysis_status_running",
                status_label: "Running",
                occurred_at: "2026-01-12T12:32:00Z",
              },
              {
                status_ordinal: 3,
                status_code: "analysis_status_succeeded",
                status_label: "Succeeded",
                occurred_at: "2026-01-12T12:33:00Z",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-lineage-pending/start") && method === "POST") {
        return Promise.resolve(
          jsonResponse({
            analysis_run_id: "run-demo-lineage-pending",
            run_kind_code: "analysis_run_lineage",
            run_kind_label: "Lineage reconstruction",
            scope_kind_code: "analysis_scope_corporate_entity",
            scope_kind_label: "Corporate entity",
            scope_entity_name: "Demo Corp",
            status_code: "analysis_status_succeeded",
            status_label: "Succeeded",
            knowledge_cutoff: "2026-01-12T12:00:00Z",
            requested_at: "2026-01-12T12:35:00Z",
            source_counts: [],
            visible_posts: [
              {
                post_id: "post-1",
                post_title: "Pricing renegotiation: revised quote sent",
                live_after_cutoff: true,
              },
              {
                post_id: "post-2",
                post_title: "Pricing renegotiation follow-up",
                live_after_cutoff: false,
              },
            ],
            reconstructed_edges: [
              {
                parent_post_id: "post-2",
                parent_post_title: "Pricing renegotiation follow-up",
                child_post_id: "post-1",
                child_post_title: "Pricing renegotiation: revised quote sent",
                fused_score: 0.72,
              },
              {
                parent_post_id: "post-2",
                parent_post_title: "Pricing renegotiation follow-up",
                child_post_id: "post-delivery",
                child_post_title: "Delivery schedule question raised",
                fused_score: 0.68,
              },
            ],
            reconstruction_result_sha256: "aa".repeat(32),
            status_history: [
              {
                status_ordinal: 1,
                status_code: "analysis_status_pending",
                status_label: "Pending",
                occurred_at: "2026-01-12T12:35:00Z",
              },
              {
                status_ordinal: 2,
                status_code: "analysis_status_running",
                status_label: "Running",
                occurred_at: "2026-01-12T12:36:00Z",
              },
              {
                status_ordinal: 3,
                status_code: "analysis_status_succeeded",
                status_label: "Succeeded",
                occurred_at: "2026-01-12T12:37:00Z",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-tepp/start") && method === "POST") {
        return Promise.resolve(
          jsonResponse({
            analysis_run_id: "run-demo-tepp",
            run_kind_code: "analysis_run_tepp",
            run_kind_label: "TEPP measurement",
            scope_kind_code: "analysis_scope_corporate_entity",
            scope_kind_label: "Corporate entity",
            scope_entity_name: "Demo Corp",
            status_code: "analysis_status_failed",
            status_label: "Failed",
            failure_code: "tepp_not_available",
            knowledge_cutoff: "2026-01-12T12:00:00Z",
            requested_at: "2026-01-12T12:34:00Z",
            source_counts: [
              {
                count_type_code: "analysis_count_document",
                count_type_label: "Documents",
                count_value: 3,
              },
            ],
            visible_posts: [{ post_id: "post-1", post_title: "Public post" }],
            status_history: [
              {
                status_ordinal: 1,
                status_code: "analysis_status_pending",
                status_label: "Pending",
                occurred_at: "2026-01-12T12:35:00Z",
              },
              {
                status_ordinal: 2,
                status_code: "analysis_status_running",
                status_label: "Running",
                occurred_at: "2026-01-12T12:36:00Z",
              },
              {
                status_ordinal: 3,
                status_code: "analysis_status_failed",
                status_label: "Failed",
                occurred_at: "2026-01-12T12:37:00Z",
                failure_code: "tepp_not_available",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/analysis-runs") && method === "POST") {
        const payload = init?.body ? JSON.parse(String(init.body)) : {};
        if (payload.run_kind_code === "analysis_run_tepp" || payload.run_kind_code === "analysis_run_report") {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail:
                  payload.run_kind_code === "analysis_run_tepp"
                    ? "Connect a TEPP transport from a Failed TEPP row; this endpoint does not invent a measurement."
                    : "Rebuild the period report from the Reports panel.",
              }),
              { status: 422, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        const created = {
          analysis_run_id: "run-demo-lineage-pending",
          run_kind_code: "analysis_run_lineage",
          run_kind_label: "Lineage reconstruction",
          scope_kind_code: "analysis_scope_corporate_entity",
          scope_kind_label: "Corporate entity",
          scope_entity_name: "Demo Corp",
          status_code: "analysis_status_pending",
          status_label: "Pending",
          knowledge_cutoff: "2026-01-12T12:00:00Z",
          requested_at: "2026-01-12T12:35:00Z",
          source_counts: [],
          visible_posts: [{ post_id: "post-1", post_title: "Public post" }],
          reconstructed_edges: [],
          status_history: [
            {
              status_ordinal: 1,
              status_code: "analysis_status_pending",
              status_label: "Pending",
              occurred_at: "2026-01-12T12:35:00Z",
            },
          ],
        };
        createdPendingLineage = created;
        return Promise.resolve(new Response(JSON.stringify(created), { status: 201 }));
      }
      if (url.endsWith("/api/analysis-runs")) {
        return Promise.resolve(
          jsonResponse({
            analysis_runs: [
              ...(createdPendingLineage ? [createdPendingLineage] : []),
              ...(createdPendingTepp ? [createdPendingTepp] : []),
              {
                analysis_run_id: "run-demo-lineage",
                run_kind_code: "analysis_run_lineage",
                run_kind_label: "Lineage reconstruction",
                scope_kind_code: "analysis_scope_corporate_entity",
                scope_kind_label: "Corporate entity",
                scope_entity_name: "Demo Corp",
                status_code: options?.failedLineageRun
                  ? "analysis_status_failed"
                  : options?.runningLineageRun
                    ? "analysis_status_running"
                    : "analysis_status_succeeded",
                status_label: options?.failedLineageRun
                  ? "Failed"
                  : options?.runningLineageRun
                    ? "Running"
                    : "Succeeded",
                knowledge_cutoff: "2026-01-12T12:00:00Z",
                requested_at: "2026-01-12T12:30:00Z",
                source_counts: [
                  {
                    count_type_code: "analysis_count_document",
                    count_type_label: "Documents",
                    count_value: 3,
                  },
                ],
                code_revision_sha: "abcdef0123456789deadbeefcafebabe",
                configuration_sha256:
                  "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
              },
              {
                analysis_run_id: "run-demo-tepp",
                run_kind_code: "analysis_run_tepp",
                run_kind_label: "TEPP measurement",
                scope_kind_code: "analysis_scope_corporate_entity",
                scope_kind_label: "Corporate entity",
                scope_entity_name: "Demo Corp",
                status_code: options?.succeededTeppRun
                  ? "analysis_status_succeeded"
                  : options?.pendingTeppRun
                    ? "analysis_status_pending"
                    : "analysis_status_failed",
                status_label: options?.succeededTeppRun
                  ? "Succeeded"
                  : options?.pendingTeppRun
                    ? "Pending"
                    : "Failed",
                knowledge_cutoff: "2026-01-12T12:00:00Z",
                requested_at: "2026-01-12T12:34:00Z",
                source_counts: [
                  {
                    count_type_code: "analysis_count_document",
                    count_type_label: "Documents",
                    count_value: 3,
                  },
                ],
              },
              {
                analysis_run_id: "run-demo-report",
                run_kind_code: "analysis_run_report" as const,
                run_kind_label: "Period report",
                scope_kind_code: "analysis_scope_corporate_entity",
                scope_kind_label: "Corporate entity",
                scope_entity_name: "Demo Corp",
                scope_key: "2026-W02",
                scope_grouping_key: "corp-1",
                status_code: options?.failedReportRun
                  ? ("analysis_status_failed" as const)
                  : ("analysis_status_succeeded" as const),
                status_label: options?.failedReportRun ? "Failed" : "Succeeded",
                knowledge_cutoff: "2026-01-12T12:00:00Z",
                requested_at: "2026-01-12T12:38:00Z",
                source_counts: [
                  {
                    count_type_code: "analysis_count_document",
                    count_type_label: "Documents",
                    count_value: 3,
                  },
                ],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/calendar")) {
        return Promise.resolve(
          jsonResponse({
            events: [],
            commitments:
              options?.calendarCommitments ?? [
                {
                  issue_ticket_id: "ticket-a100",
                  post_id: "post-1",
                  ticket_status_code: "open",
                  ticket_status_label: "Open",
                  ticket_title: "Send Northridge Grid the revised quote",
                  assigned_account_id: null,
                  due_date: "2026-01-12",
                  commitment_summary: null,
                  created_at: "2026-01-01T00:00:00Z",
                  updated_at: "2026-01-01T00:00:00Z",
                  post_title: "Public post",
                },
                {
                  issue_ticket_id: "ticket-b200",
                  post_id: "post-2",
                  ticket_status_code: "open",
                  ticket_status_label: "Open",
                  ticket_title: "Send Westfield Power the revised specification",
                  assigned_account_id: null,
                  due_date: "2026-01-14",
                  commitment_summary: null,
                  created_at: "2026-01-02T00:00:00Z",
                  updated_at: "2026-01-02T00:00:00Z",
                  post_title: "Specification revision requested",
                },
              ],
            calendar_sources: {
              naruon_available: false,
              naruon_next_action:
                "Ask your workspace administrator to enable calendar access. Open a commitment below to read its source post.",
            },
          }),
        );
      }
      if (url.endsWith("/api/rankings")) {
        const rankings = options?.rankings ?? {
          status: "unavailable" as const,
          status_reason: "rankweave_not_available",
          rankings: [],
        };
        return Promise.resolve(
          jsonResponse({
            port: "rankweave",
            status: rankings.status,
            status_reason: rankings.status_reason,
            rankings: rankings.rankings ?? [],
          }),
        );
      }
      if (url.includes("/api/reports/compare/") && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            period_code: "2026-W02",
            groupings: [
              {
                grouping_kind: "process_unit",
                grouping_key: "pu-high",
                grouping_label: "Demo Report High",
                mean_theta: 0.81,
                post_count: 4,
                link_method: "fipc",
                leftover_map_coverage: {
                  map_post_count: 5,
                  scored_post_count: 3,
                  map_item_count: 2,
                  scored_item_count: 2,
                  incomplete_post_count: 0,
                  incomplete_item_count: 0,
                },
                leftover_pairs: [
                  {
                    pair_kind: "closest",
                    post_id: "post-2",
                    post_title: "Specification revision requested",
                    criterion_code: "general_sentiment_negative",
                    leftover_distance: 2.0,
                    leftover_residual: -1.1,
                  },
                ],
              },
              {
                grouping_kind: "corporate_entity",
                grouping_key: "corp-1",
                grouping_label: "Demo Corp",
                mean_theta: 0.42,
                post_count: 8,
                link_method: "fipc",
              },
              {
                grouping_kind: "thread_group",
                grouping_key: "A-100",
                grouping_label: "A-100",
                mean_theta: 0.81,
                post_count: 4,
                link_method: "fipc",
                leftover_pairs: [
                  {
                    pair_kind: "closest",
                    post_id: "post-1",
                    post_title: "Public post",
                    criterion_code: "sales_lead_specificity",
                    leftover_distance: 0.12,
                    leftover_residual: 0.4,
                    leftover_map_reconstruction: 0.248,
                    leftover_map_explained_share: 0.76,
                    leftover_map_unexplained_share: 0.02,
                    leftover_map_cross_share: 0.12,
                    leftover_map_unexplained: 0.05,
                    observed_response: 2.4,
                    expected_response: 2.0,
                    leftover_map_rank: 1,
                    leftover_map_person_axis_1: 0.5,
                    leftover_map_person_axis_2: 0.1,
                    leftover_map_item_axis_1: 0.5,
                    leftover_map_item_axis_2: -0.02,
                  },
                ],
                leftover_map_axes: [
                  {
                    axis_index: 1,
                    leftover_singular_value: 1.84,
                    leftover_share: 0.82,
                  },
                  {
                    axis_index: 2,
                    leftover_singular_value: 0.86,
                    leftover_share: 0.18,
                  },
                ],
                leftover_map_coverage: {
                  map_post_count: 2,
                  scored_post_count: 3,
                  map_item_count: 2,
                  scored_item_count: 2,
                  incomplete_post_count: 1,
                  incomplete_item_count: 0,
                },
              },
            ],
          }),
        );
      }
      if (/\/api\/reports\/[^/]+$/.test(url) && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            grouping_kind: "process_unit",
            periods: [
              {
                grouping_key: "TEST-PU-REPORT",
                period_code: "2026-W02",
                selected_model: "grm",
                mean_theta: 0.0,
                post_count: 8,
                link_method: "fipc",
                anchor_period_code: "2026-W02",
                delta_mean_theta: null,
                selected_item_code: "sales_lead_specificity",
                selected_item_information: 0.7,
              },
              {
                grouping_key: "TEST-PU-REPORT",
                period_code: "2026-W03",
                selected_model: "grm",
                mean_theta: 0.92,
                post_count: 6,
                link_method: "fipc",
                anchor_period_code: "2026-W02",
                delta_mean_theta: 0.92,
                selected_item_code: "sales_lead_specificity",
                selected_item_information: 0.65,
              },
            ],
          }),
        );
      }
      if (url.includes("/api/reports/corporate_entity/") && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            grouping_kind: "corporate_entity",
            period_code: url.includes("2026-W03") ? "2026-W03" : "2026-W02",
            reports: [
              {
                grouping_key: "corp-other",
                grouping_label: "Other Corp",
                selected_model: "grm",
                mean_theta: -0.2,
                mean_theta_sd: 0.1,
                post_count: 2,
                item_count: 3,
                fit_converged: true,
                link_method: "fipc",
                anchor_period_code: "2026-W02",
                delta_mean_theta: null,
                selected_items: [],
                members: [],
              },
              {
                grouping_key: "corp-1",
                grouping_label: "Demo Corp",
                selected_model: "grm",
                mean_theta: 0.42,
                mean_theta_sd: 0.1,
                post_count: 8,
                item_count: 3,
                fit_converged: true,
                link_method: "fipc",
                anchor_period_code: "2026-W02",
                delta_mean_theta: null,
                selected_items: [
                  { item_code: "sales_lead_specificity", rank: 1, information: 0.7 },
                ],
                members: [
                  {
                    post_id: "post-1",
                    post_title: "Public post",
                    theta_eap: 0.91,
                    theta_sd: 0.2,
                    ticket_due_date: "2026-01-12",
                    ticket_title: "Send Northridge Grid the revised quote",
                    ticket_status_code: "open",
                    ticket_status_label: "Open",
                  },
                ],
              },
            ],
          }),
        );
      }
      if (url.includes("/api/reports/") && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            grouping_kind: "process_unit",
            period_code: "2026-W02",
            reports: [
              {
                grouping_key: "TEST-PU-REPORT",
                selected_model: "grm",
                mean_theta: 0.42,
                mean_theta_sd: 0.1,
                post_count: 8,
                item_count: 3,
                fit_converged: true,
                link_method: "fipc",
                anchor_period_code: "2026-W02",
                delta_mean_theta: null,
                selected_items: [
                  { item_code: "sales_lead_specificity", rank: 1, information: 0.7 },
                  { item_code: "general_sentiment_positive", rank: 2, information: 0.4 },
                  { item_code: "general_sentiment_negative", rank: 3, information: 0.2 },
                ],
                leftover_pairs: [
                  {
                    pair_kind: "closest",
                    post_id: "post-1",
                    post_title: "Public post",
                    criterion_code: "sales_lead_specificity",
                    leftover_distance: 0.12,
                    leftover_residual: 0.4,
                    leftover_map_unexplained: 0.05,
                    observed_response: 2.4,
                    expected_response: 2.0,
                    leftover_map_rank: 1,
                    leftover_map_cross_share: 0.12,
                    leftover_map_reconstruction: 0.248,
                    leftover_map_unexplained_share: 0.02,
                    leftover_map_explained_share: 0.76,
                    leftover_map_person_axis_1: 0.5,
                    leftover_map_person_axis_2: 0.1,
                    leftover_map_item_axis_1: 0.5,
                    leftover_map_item_axis_2: -0.02,
                  },
                  {
                    pair_kind: "farthest",
                    post_id: "post-2",
                    post_title: "Specification revision requested",
                    criterion_code: "general_sentiment_negative",
                    leftover_distance: 2.0,
                    leftover_residual: -1.1,
                    leftover_map_unexplained: -0.25,
                    observed_response: 0.9,
                    expected_response: 2.0,
                    leftover_map_rank: 1,
                    leftover_map_cross_share: -0.24,
                    leftover_map_reconstruction: -0.95,
                    leftover_map_unexplained_share: 0.05,
                    leftover_map_explained_share: 0.60,
                    leftover_map_person_axis_1: 0.9,
                    leftover_map_person_axis_2: 0.8,
                    leftover_map_item_axis_1: -0.7,
                    leftover_map_item_axis_2: -0.4,
                  },
                ],
                leftover_map_axes: [
                  {
                    axis_index: 1,
                    leftover_singular_value: 1.84,
                    leftover_share: 0.82,
                  },
                  {
                    axis_index: 2,
                    leftover_singular_value: 0.86,
                    leftover_share: 0.18,
                  },
                ],
                leftover_map_coverage: {
                  map_post_count: 2,
                  scored_post_count: 3,
                  map_item_count: 2,
                  scored_item_count: 2,
                  incomplete_post_count: 1,
                  incomplete_item_count: 0,
                },
                members: [
                  {
                    post_id: "post-1",
                    post_title: "Public post",
                    theta_eap: 0.91,
                    theta_sd: 0.2,
                    ticket_due_date: "2026-01-12",
                    ticket_title: "Send Northridge Grid the revised quote",
                    ticket_status_code: "open",
                    ticket_status_label: "Open",
                  },
                  {
                    post_id: "post-2",
                    post_title: "Specification revision requested",
                    theta_eap: 0.18,
                    theta_sd: 0.3,
                    ticket_due_date: "2026-01-14",
                    ticket_title: "Send Westfield Power the revised specification",
                    ticket_status_code: "open",
                    ticket_status_label: "Open",
                  },
                ],
              },
            ],
          }),
        );
      }
      if (url.includes("/api/reports/") && method === "POST") {
        return Promise.resolve(jsonResponse({ group_count: 1 }));
      }
      if (url.includes("/api/lineage") && method === "GET") {
        if (options?.lineageIsolationReason) {
          return Promise.resolve(
            jsonResponse({
              nodes: [],
              edges: [],
              truncated: false,
              isolation_reason: options.lineageIsolationReason,
            }),
          );
        }
        return Promise.resolve(
          jsonResponse({
            nodes: [
              {
                id: "post-1",
                group: "A-100",
                label: "Public post",
                occurred_at: "2026-01-01T00:00:00Z",
                is_root: true,
                is_branch_point: false,
              },
              {
                id: "post-2",
                group: "A-100",
                label: "Linked post",
                occurred_at: "2026-01-02T00:00:00Z",
                is_root: false,
                is_branch_point: false,
              },
              {
                id: "rec-002",
                group: "A-100",
                label: "Pricing renegotiation follow-up",
                occurred_at: "2026-01-06T00:00:00Z",
                is_root: false,
                is_branch_point: true,
              },
              {
                id: "rec-003",
                group: "A-100",
                label: "Pricing renegotiation: revised quote sent",
                occurred_at: "2026-01-10T00:00:00Z",
                is_root: false,
                is_branch_point: false,
              },
              {
                id: "rec-004",
                group: "A-100",
                label: "Delivery schedule question raised",
                occurred_at: "2026-01-07T00:00:00Z",
                is_root: false,
                is_branch_point: false,
              },
              {
                id: "rec-006",
                group: "A-100",
                label: "Unrelated: annual account review",
                occurred_at: "2026-02-10T00:00:00Z",
                is_root: true,
                is_branch_point: false,
              },
            ],
            edges: [
              { source: "post-1", target: "post-2", fused_score: 0.8 },
              { source: "rec-002", target: "rec-003", fused_score: 0.9 },
              { source: "rec-002", target: "rec-004", fused_score: 0.85 },
            ],
          }),
        );
      }
      const postsUrl = new URL(url, "https://backend.test");
      if (postsUrl.pathname === "/api/posts") {
        return Promise.resolve(
          jsonResponse(
            postsUrl.searchParams.get("search")
              ? []
              : {
                  posts: [
                    {
                      post_id: "post-1",
                      post_title: "Public post",
                      voc_type_code: "voc",
                      voc_type_label: "Voice of Customer",
                      ...(options?.combinedVoices
                        ? {
                            voice_types: [
                              {
                                code: "voc",
                                label: "Voice of Customer",
                                is_primary: true,
                                truth_status_code: "truth_observed",
                                evidence_available: false,
                              },
                              {
                                code: "vops",
                                label: "Voice of Process",
                                is_primary: false,
                                truth_status_code: "truth_observed",
                                evidence_available: true,
                              },
                            ],
                          }
                        : {}),
                      visibility_code: "public",
                      visibility_label: "Public",
                      created_at: "2026-01-01T00:00:00Z",
                    },
                  ],
                  total_count: 1,
                  limit: 50,
                  offset: 0,
                  ...(options?.omitVoiceOptions
                    ? {}
                    : {
                        voc_type_options: [
                          { code: "voc", label: "Voice of Customer" },
                          { code: "vop", label: "Voice of Partner" },
                          ...(options?.combinedVoices
                            ? [{ code: "vops", label: "Voice of Process" }]
                            : []),
                        ],
                        voice_type_catalog: [
                          { code: "voc", label: "Voice of Customer" },
                          { code: "vop", label: "Voice of Partner" },
                          { code: "vos", label: "Voice of Supplier" },
                        ],
                      }),
                  visibility_options: [{ code: "public", label: "Public" }],
                },
          ),
        );
      }
      const postOneUrl = new URL(url, "https://backend.test");
      if (postOneUrl.pathname === "/api/posts/post-1/similar-voc") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      if (postOneUrl.pathname === "/api/posts/post-1") {
        const asOf = postOneUrl.searchParams.get("as_of");
        return postOneReady.then(() =>
          jsonResponse({
            post_id: "post-1",
            post_title: "Public post",
            post_body: options?.postBody ?? "The full body text.",
            voc_type_code: "voc",
            voc_type_label: "Voice of Customer",
            visibility_code: "public",
            visibility_label: "Public",
            project_evidence: [
              {
                project_key: "source-project",
                project_name: "Semantic project",
                evidence: "project was described in the body",
                confidence: 0.9,
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Project",
                ontology_label: "Project",
                extraction_method: "contextual_orchestrator_semantic",
                resolution_status: "semantic_candidate",
                provenance: "post_project_mention.evidence_text",
              },
            ],
            created_at: "2026-01-01T00:00:00Z",
            ...(asOf
              ? {
                  known_at: {
                    post_title: "Public post",
                    post_body: "The cutoff body this run knew.",
                    written_at: "2026-01-10T12:00:00Z",
                    as_of: asOf,
                  },
                }
              : {}),
          }),
        );
      }
      if (postOneUrl.pathname === "/api/posts/post-1/content") {
        contentRequests += 1;
        return Promise.resolve(
          jsonResponse({
            status: "ready",
            images: [],
            units:
              options?.contentAfterSummary && contentRequests > 1
                ? [
                    {
                      unit_index: 0,
                      unit_kind_code: "plain_text",
                      unit_label: "p",
                      unit_text: "Freshly processed source paragraph.",
                      indent_level: 0,
                      indent_source_code: "explicit",
                      indent_confidence: 1,
                      indent_evidence: "HTML paragraph boundary",
                    },
                  ]
                : [],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-2")) {
        if (options?.evidenceUnavailable) {
          return Promise.resolve(new Response("unavailable", { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            post_id: "post-2",
            post_title: "Linked post",
            post_body: "The evidence panel should show exactly this text.",
            voc_type_code: "voc",
            visibility_code: "public",
            created_at: "2026-01-02T00:00:00Z",
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/evaluation")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            rubric_version: "2026-08-13",
            responses: [
              {
                criterion_code: "general_sentiment_positive",
                criterion_label: "Constructive stance",
                response_category: 2,
                rubric_version: "2026-08-13",
              },
              {
                criterion_code: "sales_lead_specificity",
                criterion_label: "Sales-lead specificity",
                response_category: 3,
                rubric_version: "2026-08-13",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/summary")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            korean_summary: "이것은 요약입니다.",
            ...(options?.staleSummary
              ? { summary_status: "stale", summary_contract_version: 4 }
              : {}),
            key_events: ["첫 번째 이벤트"],
            roles_and_responsibilities: [
              {
                actor_name: "Ada West",
                responsibility: "우리 측 후속",
                actor_type_code: "prov_person",
                affiliated_organization_name: "Demo Corp",
              },
              {
                actor_name: "Priya Nair",
                responsibility: "고객 측 수신",
                actor_type_code: "prov_person",
                affiliated_organization_name: "Northridge Grid",
                catalog_node_id: "person-priya",
                catalog_node_type_code: "node_person",
              },
              {
                actor_name: "당사",
                responsibility: "출하 일정 확정",
                actor_type_code: "prov_organization",
                affiliated_organization_name: null,
              },
              {
                actor_name: "설계팀",
                responsibility: "도면 검토",
                actor_type_code: "prov_team",
                affiliated_organization_name: "Demo Corp",
                catalog_node_id: "team-1",
                catalog_node_type_code: "node_team",
              },
            ],
            project_mentions: [
              {
                project_key: "sample-project",
                project_name: "Sample project",
                evidence: "post body",
                confidence: 0.9,
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Project",
                extraction_method: "contextual_orchestrator_semantic",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/keymen")) {
        return Promise.resolve(
          jsonResponse({
            keymen: [
              {
                person_id: "person-ada",
                person_name: "Ada West",
                person_side_code: "our_side",
                person_side_label: "Our side",
                last_known_job_title: "Account manager",
                mention_context: null,
                affiliations: [
                  {
                    organization_name: "Demo Corp",
                    corporate_entity_id: "corp-1",
                    role_title: null,
                    ...demoOrgAlias,
                  },
                ],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/extract-keymen") && method === "POST") {
        if (options?.chatUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Keymen extraction is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
              }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return Promise.resolve(jsonResponse({ extracted_count: 1 }));
      }
      if (url.endsWith("/api/posts/post-1/evaluate") && method === "POST") {
        if (options?.chatUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Post evaluation is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
              }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return Promise.resolve(jsonResponse({ post_id: "post-1", rubric_version: "2026-08-13", responses: [] }));
      }
      if (url.endsWith("/api/keymen/person-priya/related")) {
        return Promise.resolve(
          jsonResponse({
            person_id: "person-priya",
            person_name: "Priya Nair",
            person_side_code: "counterparty",
            role_history: [],
            related: [
              {
                node_id: "person-ada",
                node_type_code: "node_person",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Person",
                ontology_label: "Person",
                label: "Ada West",
                person_side_code: "our_side",
                person_side_label: "Our side",
                relevance: 0.4,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/keymen/person-ada/related")) {
        return Promise.resolve(
          jsonResponse({
            person_id: "person-ada",
            person_name: "Ada West",
            person_side_code: "our_side",
            role_history: [
              {
                post_id: "post-early",
                post_title: "Early post",
                created_at: "2026-01-01T00:00:00Z",
                responsibility: "junior account rep",
                affiliated_organization_name: "Northwind Labs",
              },
              {
                post_id: "post-later",
                post_title: "Later post",
                created_at: "2026-06-01T00:00:00Z",
                responsibility: "account lead",
                affiliated_organization_name: "Demo Corp",
              },
            ],
            related: [
              {
                node_id: "person-priya",
                node_type_code: "node_person",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Person",
                ontology_label: "Person",
                label: "Priya Nair",
                person_side_code: "counterparty",
                person_side_label: "Counterparty",
                relevance: 0.4,
              },
              {
                node_id: "post-2",
                node_type_code: "node_post",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Post",
                ontology_label: "Post",
                label: "Linked post",
                relevance: 0.3,
              },
              {
                node_id: "corp-1",
                node_type_code: "node_corporate_entity",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#CorporateEntity",
                ontology_label: "Corporate entity",
                label: "Demo Corp",
                relevance: 0.2,
                ...demoOrgAlias,
              },
              {
                node_id: "team-1",
                node_type_code: "node_team",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Team",
                ontology_label: "Team",
                label: "설계팀",
                relevance: 0.15,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/teams/team-1/related")) {
        return Promise.resolve(
          jsonResponse({
            team_id: "team-1",
            team_name: "설계팀",
            related: [
              {
                node_id: "post-2",
                node_type_code: "node_post",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Post",
                ontology_label: "Post",
                label: "Linked post",
                relevance: 0.6,
              },
            ],
          }),
        );
      }
      if (url.includes("/api/ontology/neighborhood")) {
        return Promise.resolve(
          jsonResponse({
            focus_node_id: "post-1",
            focus_node_type_code: "node_post",
            truncated: false,
            next_cursor: null,
            limitation_code: "neighborhood_empty",
            nodes: [
              {
                node_id: "post-1",
                node_type_code: "node_post",
                ontology_class_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Post",
                display_label: "Public post",
                truth_status_code: "truth_observed",
                valid_from: null,
                valid_to: null,
                recorded_at: "2026-01-10T12:00:00+00:00",
                evidence_count: 0,
                shape_code: "rectangle",
              },
            ],
            edges: [],
            exact_value_rows: [],
            jsonld: { "@graph": [] },
          }),
        );
      }
      if (url.endsWith("/api/corporate-entities/corp-1/related")) {
        return Promise.resolve(
          jsonResponse({
            corporate_entity_id: "corp-1",
            entity_name: "Demo Corp",
            related: [
              {
                node_id: "person-ada",
                node_type_code: "node_person",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Person",
                ontology_label: "Person",
                label: "Ada West",
                person_side_code: "our_side",
                person_side_label: "Our side",
                relevance: 0.5,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/corporate-entities/corp-demo/related")) {
        return Promise.resolve(
          jsonResponse({
            corporate_entity_id: "corp-demo",
            entity_name: "Demo Corp",
            related: [
              {
                node_id: "person-ada",
                node_type_code: "node_person",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Person",
                ontology_label: "Person",
                label: "Ada West",
                person_side_code: "our_side",
                person_side_label: "Our side",
                relevance: 0.5,
              },
              {
                node_id: "post-1",
                node_type_code: "node_post",
                ontology_iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#Post",
                ontology_label: "Post",
                label: "Linked post",
                relevance: 0.6,
                post_body_excerpt: "A linked body preview.",
                post_body_truncated: false,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/affiliate-tree")) {
        return Promise.resolve(
          jsonResponse({
            trees: [
              {
                entity_id: "group-1",
                entity_name: "Demo Group",
                entity_level_code: "group",
                entity_level_label: "Group",
                resolved: true,
                people: [],
                children: [
                  {
                    entity_id: "corp-1",
                    entity_name: "Demo Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    resolved: true,
                    ...demoOrgAlias,
                    people: [
                      {
                        person_id: "person-ada",
                        person_name: "Ada West",
                        person_side_code: "our_side",
                        person_side_label: "Our side",
                      },
                    ],
                    children: [],
                  },
                ],
              },
              {
                entity_id: null,
                entity_name: "Northridge Grid",
                entity_level_code: null,
                resolved: false,
                people: [
                  {
                    person_id: "person-priya",
                    person_name: "Priya Nair",
                    person_side_code: "counterparty",
                    person_side_label: "Counterparty",
                  },
                ],
                children: [],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/voc-evidence")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            voc_type_code: "voc",
            voc_type_label: "Voice of Customer",
            excerpts: [
              "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
              "The weekly recap listed the delay against the open ticket.",
            ],
            counterparties: [
              {
                counterparty_entity_name: "Northridge Grid",
                relationship_type_code: "rel_voc",
                relationship_label: "Voice of Customer",
                evidence_excerpt:
                  "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
                verification_status_code: "verify_pending",
                verification_evidence_url: options?.verificationEvidenceUrl ?? null,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/counterparties")) {
        return Promise.resolve(
          jsonResponse({
            counterparties: [
              {
                counterparty_entity_name: "Demo Corp",
                relationship_type_code: "rel_voc",
                relationship_label: "Voice of Customer",
                verification_status_code: "verify_pending",
                verification_evidence_url: null,
                corporate_entity_id: "corp-1",
                ...demoOrgAlias,
              },
              {
                counterparty_entity_name: "Northridge Grid",
                relationship_type_code: "rel_voc",
                relationship_label: "Voice of Customer",
                verification_status_code: "verify_pending",
                verification_evidence_url: options?.verificationEvidenceUrl ?? null,
                corporate_entity_id: null,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/verify-relations") && method === "POST") {
        if (options?.searchUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ detail: "Relation verification is unavailable: set SEARXNG_BASE_URL" }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return Promise.resolve(jsonResponse({ verified: [] }));
      }
      if (url.endsWith("/api/posts/post-1/lineage")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            direct: options?.lineageIsolationReason ? [] : [
              {
                post_id: "rec-003",
                post_title: "Pricing renegotiation: revised quote sent",
                interval_relation_code: "interval_contains",
                interval_relation_label: "Contains",
                interval_is_parent: true,
              },
            ],
            indirect: options?.lineageIsolationReason
              ? []
              : [{ post_id: "post-2", post_title: "Linked post" }],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/chat") && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            exchanges: [
              {
                question_text: "What happened between these events?",
                answer_text: "The seeded follow-up after the site visit.",
                cited_post_ids: ["post-2"],
                cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
              },
              {
                question_text: "Who is involved?",
                answer_text: "Ada West and Priya Nair are the Keymen on this thread.",
                cited_post_ids: ["post-1"],
                cited_posts: [{ post_id: "post-1", post_title: "Public post" }],
              },
              {
                question_text: "What is the next commitment?",
                answer_text:
                  "The next commitment is Send Northridge Grid the revised quote, due 2026-01-12.",
                cited_post_ids: ["post-1"],
                cited_posts: [{ post_id: "post-1", post_title: "Public post" }],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/chat") && method === "POST") {
        if (options?.chatUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Post chat is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
              }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            answer_text: "Here is what happened, drawing on the linked post.",
            cited_post_ids: ["post-2"],
            cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
            source_post_ids: ["post-1", "post-2"],
          }),
        );
      }
      if (url.endsWith("/api/ask") && method === "POST") {
        return Promise.resolve(
          jsonResponse({ ask_job_id: "ask-job-1", job_status_code: "queued" }),
        );
      }
      if (url.includes("/api/ask/jobs/") && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            ask_job_id: "ask-job-1",
            job_status_code: "succeeded",
            answer: {
            answer_text: "The cited project is supported by the stored semantic evidence.",
            cited_post_ids: ["post-2"],
            cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
            cited_post_evidence: [
              {
                post_id: "post-2",
                facts: [
                  { kind: "semantic_project", text: "project: Semantic project | evidence: Body evidence" },
                  { kind: "semantic_keyman", text: "Keyman mention: Ada West | context: account lead" },
                ],
              },
            ],
            cited_post_images: options?.askImageCitation
              ? [
                  {
                    post_id: "post-2",
                    unit_index: 1,
                    mime_type: "image/png",
                    status_code: "described",
                    extracted_text: "Error code 500 on checkout",
                    caption: "Screenshot of the checkout error",
                    tags: ["screenshot", "error"],
                  },
                ]
              : [],
            source_post_ids: ["post-1", "post-2"],
            lineage_graph: options?.askLineageGraph
              ? {
                  nodes: [
                    {
                      id: "post-2",
                      group: "thread-alpha",
                      label: "Linked post",
                      occurred_at: "2026-08-01T00:00:00Z",
                      is_root: true,
                      is_branch_point: false,
                    },
                    {
                      id: "post-3",
                      group: "thread-alpha",
                      label: "Follow-up post",
                      occurred_at: "2026-08-02T00:00:00Z",
                      is_root: false,
                      is_branch_point: false,
                    },
                    {
                      id: "post-4",
                      group: "thread-beta",
                      label: "Unrelated thread post",
                      occurred_at: "2026-08-03T00:00:00Z",
                      is_root: true,
                      is_branch_point: false,
                    },
                  ],
                  edges: [{ source: "post-2", target: "post-3", fused_score: 0.7 }],
                  truncated: false,
                }
              : { nodes: [], edges: [], truncated: false },
            delivery: options?.askDelivery ? {
              contract_version: "1.0",
              report: {
                media_type: "text/markdown",
                body: "Answer",
                source_documents: [{
                  post_id: "post-2", title: "Linked post", api_path: "/api/posts/post-2",
                  resource_uri: "lineageweave://posts/post-2", evidence_facts: [],
                }],
              },
              alert: {
                trigger_code: "cited_evidence_changed", delivery_status_code: "not_subscribed",
                eligible: true, watched_resource_uris: ["lineageweave://posts/post-2"],
              },
            } : undefined,
            },
          }),
        );
      }
      if (url.endsWith("/api/customer-master") && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            corporate_entities: options?.customerEntityHierarchy
              ? [
                  {
                    corporate_entity_id: "corp-group",
                    corporate_entity_code: "DEMO-GROUP-01",
                    entity_name: "Demo Group",
                    entity_level_code: "group",
                    entity_level_label: "Group",
                    parent_entity_id: null,
                  },
                  {
                    corporate_entity_id: "corp-demo",
                    corporate_entity_code: "DEMO-CORP-01",
                    entity_name: "Demo Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: "corp-group",
                  },
                ]
              : [
                  {
                    corporate_entity_id: "corp-demo",
                    corporate_entity_code: "DEMO-CORP-01",
                    entity_name: "Demo Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: null,
                  },
                ],
            keymen: [
              {
                person_id: "person-1",
                person_name: "Ada West",
                person_side_code: "our_side",
                person_side_label: "Our side",
                last_known_job_title: null,
                affiliations: [],
              },
            ],
            source_customer_hints: options?.hintRelatedPosts
              ? [
                  {
                    customer_code: "CUST-HINT",
                    customer_name: null,
                    post_count: 1,
                    related_posts: [
                      {
                        post_id: "hint-post-customer",
                        post_title: "Hinted customer post",
                        post_body_excerpt: "Excerpt from a hinted customer post.",
                        post_body_truncated: false,
                      },
                    ],
                    resolution_status: "hint_only",
                    hint_trust: "normal",
                    provenance: "source_post.source_customer_code",
                  },
                ]
              : options?.manyCustomerHints
                ? Array.from({ length: options.manyCustomerHints }, (_, index) => ({
                    customer_code: `CUST-${index}`,
                    customer_name: resolvedHintCode === `CUST-${index}` ? "Southfield Utilities" : null,
                    post_count: options.manyCustomerHints! - index,
                    related_posts: [],
                    resolution_status: resolvedHintCode === `CUST-${index}` ? "resolved" : "hint_only",
                    hint_trust: "normal",
                    provenance: "source_post.source_customer_code",
                  }))
                : [],
            source_author_hints: options?.hintRelatedPosts
              ? [
                  {
                    author_code: "AUTH-HINT",
                    author_name: null,
                    author_account_id: "acct-hint",
                    account_display_name: "Guest account",
                    account_affiliations: [],
                    post_count: 1,
                    keyman_hints: [],
                    related_posts: [
                      {
                        post_id: "hint-post-author",
                        post_title: "Hinted author post",
                        post_body_excerpt: "Excerpt from a hinted author post.",
                        post_body_truncated: false,
                      },
                    ],
                    resolution_status: "hint_only",
                    provenance: "source_post.source_author_code",
                  },
                ]
              : [],
            relationship_network: [
              {
                counterparty_entity_name: "Northridge Grid",
                corporate_entity_id: null,
                total_post_count: 2,
                relationships: [
                  { relationship_type_code: "rel_voc", relationship_label: "Voice of Customer", post_count: 1 },
                  { relationship_type_code: "rel_voco", relationship_label: "Voice of Competitor", post_count: 1 },
                ],
                multi_role: true,
              },
              {
                counterparty_entity_name: "Solo Role Corp",
                corporate_entity_id: null,
                total_post_count: 1,
                relationships: [
                  { relationship_type_code: "rel_vos", relationship_label: "Voice of Supplier", post_count: 1 },
                ],
                multi_role: false,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/customer-master/resolve-hint") && method === "POST") {
        const body = JSON.parse(String(init?.body));
        resolvedHintCode = body.hint_code;
        return Promise.resolve(
          jsonResponse({
            corporate_entity_id: "corp-southfield",
            entity_name: "Southfield Utilities",
            linked_post_count: 3,
            verification_evidence_url: "https://example.org/southfield",
          }),
        );
      }
      return Promise.reject(new Error(`unexpected fetch: ${method} ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    return Object.assign(fetchMock, { releaseMe, releasePostOne });
  }

  it("shows all evidence-bearing Voice-of-X labels on a post card", async () => {
    stubBackend({ combinedVoices: true });
    render(<App />);

    expect(
      await screen.findByText("Voice of Customer (Observed) + Voice of Process (Observed)"),
    ).toBeInTheDocument();
  });

  it("keeps a post whose additional voice matches the board filter", async () => {
    stubBackend({ combinedVoices: true });
    render(<App />);

    await screen.findByRole("button", { name: "View post: Public post" });
    await userEvent.click(screen.getByRole("checkbox", { name: "Voice of Process" }));
    expect(screen.getByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
  });

  it("offers additional voices when filter options are omitted", async () => {
    stubBackend({ combinedVoices: true, omitVoiceOptions: true });
    render(<App />);

    expect(await screen.findByRole("checkbox", { name: "Voice of Process" })).toBeInTheDocument();
  });

  it("offers an unused governed Voice when an administrator connects evidence", async () => {
    stubBackend({ admin: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    expect(await screen.findByRole("option", { name: "Voice of Supplier" })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: "Voice of Supplier" })).not.toBeInTheDocument();
  });

  it("renders safe Ask Agent evidence under each cited post", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("list", { name: "Evidence facts" })).toBeInTheDocument();
    expect(screen.getByText("Semantic project", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/project: Semantic project \| evidence: Body evidence/)).toBeInTheDocument();
    expect(screen.queryByText(/ontology_iri|contextual_orchestrator/i)).not.toBeInTheDocument();
  });

  it("converts the local knowledge cutoff to UTC for Global Ask", async () => {
    const fetchMock = stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    expect(screen.getByLabelText("Use evidence available by (optional)")).toBeInTheDocument();
    expect(screen.getByText("Choose a time on this device, or leave blank to use the latest evidence.")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Phoenix?");
    await userEvent.type(
      screen.getByLabelText("Use evidence available by (optional)"),
      "2026-01-15T12:00",
    );
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(
      await screen.findByText("The cited project is supported by the stored semantic evidence."),
    ).toBeInTheDocument();
    const askCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input).endsWith("/api/ask") && (init as RequestInit | undefined)?.method === "POST",
    );
    expect(askCall).toBeTruthy();
    const askInit = askCall?.[1] as RequestInit | undefined;
    expect(askInit).toBeDefined();
    expect(JSON.parse(String(askInit?.body))).toEqual({
      question: "Phoenix?",
      verify_external: false,
      knowledge_cutoff: new Date("2026-01-15T12:00").toISOString(),
    });
  });

  it("localizes Ask delivery copy instead of rendering Korean literals in English", async () => {
    stubBackend({ askDelivery: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("complementary", { name: "Report · alert · MCP" })).toHaveTextContent(
      "1 evidence documents are linked to this report.",
    );
    expect(screen.queryByText(/근거 문서/)).not.toBeInTheDocument();
  });

  it("renders every cited lineage thread as its own git-branch-style graph", async () => {
    stubBackend({ askLineageGraph: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByLabelText("Reconstructed lineage")).toBeInTheDocument();
    // Two distinct reconstruct threads (thread-alpha, thread-beta) must
    // render as two independent branch-tree figures, not merged into one.
    expect(screen.getByRole("group", { name: "thread-alpha lineage" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "thread-beta lineage" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open post: Follow-up post" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open post: Unrelated thread post" })).toBeInTheDocument();
  });

  it("shows no lineage graph section when the answer cites no reconstructed thread", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("list", { name: "Evidence facts" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Reconstructed lineage")).not.toBeInTheDocument();
  });

  it("cites a cited post's persisted image evidence under that post", async () => {
    stubBackend({ askImageCitation: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText(/Image evidence: Screenshot of the checkout error/)).toBeInTheDocument();
    expect(screen.getByText(/Error code 500 on checkout/)).toBeInTheDocument();
    expect(screen.getByText(/Image tags: screenshot, error/)).toBeInTheDocument();
  });

  it("shows no image evidence line when the answer cites no image", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("list", { name: "Evidence facts" })).toBeInTheDocument();
    expect(screen.queryByText(/Image evidence:/)).not.toBeInTheDocument();
  });

  it("opens a cited post's evidence in a Layer Popup without leaving the answer", async () => {
    stubBackend({ askImageCitation: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    await userEvent.click(await screen.findByRole("button", { name: "View evidence" }));

    const dialog = await screen.findByRole("dialog", { name: "Linked post" });
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText(/project: Semantic project/)).toBeInTheDocument();
    expect(within(dialog).getByText("Screenshot of the checkout error")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close evidence panel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // The answer itself is still on screen -- the layer never navigated away.
    expect(screen.getByRole("button", { name: "View evidence" })).toBeInTheDocument();
  });

  it("labels the Customer Master entity level and Keymen side, never the raw lookup code", async () => {
    // Live UI finding (2026-08-19): read_customer_master() skipped the
    // common_lookup_value join both endpoints elsewhere already use,
    // so the panel showed raw codes ("company", "our_side") whenever
    // a Keyman had no last_known_job_title -- confirm the human labels
    // render and the raw codes never leak into visible text.
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    expect(await screen.findByText("Demo Corp")).toBeInTheDocument();
    expect(screen.getByText("DEMO-CORP-01 · Company")).toBeInTheDocument();
    expect(screen.getByText("Ada West")).toBeInTheDocument();
    expect(screen.getByText("Our side")).toBeInTheDocument();
    expect(screen.queryByText("company", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("our_side", { exact: true })).not.toBeInTheDocument();
  });

  it("nests a corporate entity under its parent instead of a flat list", async () => {
    // Live bug (2026-08-19): corporate_entities already carries
    // parent_entity_id and the codebase already builds a real forest from
    // it elsewhere (lineageweave/affiliate_tree.py, the post-detail
    // popup's Affiliate tree) -- Customer Master's own entity list never
    // did, so a holding company and its subsidiary rendered as two
    // unrelated top-level rows with no visual hierarchy at all.
    stubBackend({ customerEntityHierarchy: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    expect(await screen.findByText("Demo Group")).toBeInTheDocument();
    const subsidiaryRow = screen.getByText("Demo Corp").closest("li");
    expect(subsidiaryRow).not.toBeNull();
    const parentRow = screen.getByText("Demo Group").closest("li");
    expect(parentRow).not.toBeNull();
    // The subsidiary's <li> is nested inside the parent's <li>, not a
    // sibling at the same top level.
    expect(parentRow?.contains(subsidiaryRow)).toBe(true);
  });

  it("opens a customer's related post in place instead of jumping to the Board", async () => {
    // Live bug (2026-08-19): opening a related post from Customer
    // Master swapped the whole workspace to the Board and opened the
    // popup there, so the customer context the reader was standing in
    // was gone. The popup must open inside the Customer Master panel.
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    const entityButton = (await screen.findByText("DEMO-CORP-01 · Company")).closest("button");
    expect(entityButton).not.toBeNull();
    await userEvent.click(entityButton as HTMLElement);
    await userEvent.click(await screen.findByRole("button", { name: "Open related post: Linked post" }));

    // The popup shows the post body without leaving Customer Master:
    // the Board never mounts and the customer heading stays on screen.
    expect(await screen.findByText("The full body text.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Board" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Customer master" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByText("The full body text.")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Customer master" })).toBeInTheDocument();
  }, 15000);

  it("shows every observed relationship role for a counterparty, flagging multi-role names", async () => {
    // Feature request (2026-08-19): a real counterparty is not limited
    // to one role -- a customer in one post can be a competitor,
    // supplier, or partner in another. The Customer Master screen must
    // surface the whole observed network per name, not just one role.
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    expect(await screen.findByText("Northridge Grid")).toBeInTheDocument();
    expect(screen.getByText("Voice of Customer (1), Voice of Competitor (1)")).toBeInTheDocument();
    expect(screen.getByText("Multiple roles observed")).toBeInTheDocument();

    expect(screen.getByText("Solo Role Corp")).toBeInTheDocument();
    expect(screen.getByText("Voice of Supplier (1)")).toBeInTheDocument();
    // Solo Role Corp has exactly one observed role -- no badge for it.
    const soloRow = screen.getByText("Solo Role Corp").closest("li");
    expect(soloRow).not.toBeNull();
    expect(within(soloRow as HTMLElement).queryByText("Multiple roles observed")).not.toBeInTheDocument();
  });

  it("lets a post_admin account resolve an unresolved customer hint into a real name", async () => {
    // Feature (2026-08-19): a Customer Master hint (an opaque customer
    // code with no name) previously had no action at all -- a dead end
    // even for an admin account. Resolving now creates/binds a real
    // corporate_entity and the panel reloads to show the resolved name.
    stubBackend({ admin: true, manyCustomerHints: 1 });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    expect(await screen.findByText("CUST-0")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Resolve" }));

    expect(await screen.findByText("Southfield Utilities")).toBeInTheDocument();
  });

  it("hides the resolve action from an account without post_admin", async () => {
    stubBackend({ manyCustomerHints: 1 });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    expect(await screen.findByText("CUST-0")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resolve" })).not.toBeInTheDocument();
  });

  it("gives the customer-master hint disclosures a CSS hook for the shared touch target", async () => {
    // Regression test (touch_interaction gap): these three <details> used
    // to render with no className at all, so App.css had no selector able
    // to size them -- the browser-default disclosure marker falls well
    // under --size-control-min. They now share .hint-disclosure with the
    // other secondary toggles (advanced-review-tools, semantic-provenance,
    // operator-action-tools, keyman-source-context).
    stubBackend({ hintRelatedPosts: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    const customerSection = await screen.findByRole("region", { name: "Observed customer evidence" });
    expect(within(customerSection).getByText("Related posts (1)").closest("details")).toHaveClass(
      "hint-disclosure",
    );

    const authorSection = screen.getByRole("region", { name: "Author context" });
    expect(within(authorSection).getByText("AUTH-HINT · Hint only").closest("details")).toHaveClass(
      "hint-disclosure",
    );
    expect(within(authorSection).getByText("Related posts (1)").closest("details")).toHaveClass(
      "hint-disclosure",
    );
  });

  it("caps the observed customer identifier list instead of rendering all of them", async () => {
    // Live UI finding (2026-08-19): real imported data routinely hits the
    // backend's 100-row cap on source_customer_hints; rendering all of
    // them (each with its own collapsed-but-mounted Related posts
    // details) pushed the page to a ~37,000px scroll height. Confirm the
    // frontend now truncates and says so, matching VISIBLE_POSTS_RENDER_LIMIT's
    // established pattern elsewhere in this screen.
    stubBackend({ manyCustomerHints: 45 });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "고객 마스터" }));

    expect(await screen.findByText("CUST-0")).toBeInTheDocument();
    expect(screen.getByText(/Showing the first 30 of 45 observed customer identifiers/)).toBeInTheDocument();
    expect(screen.getByText("CUST-29")).toBeInTheDocument();
    expect(screen.queryByText("CUST-30")).not.toBeInTheDocument();
    expect(screen.queryByText("CUST-44")).not.toBeInTheDocument();
  });

  it("searches the board from a semantic project mention", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await userEvent.click(
      await screen.findByRole("button", { name: "Search related posts for: Semantic project" }),
    );

    const searchInput = await screen.findByRole("searchbox", { name: "Search semantic evidence" });
    expect(searchInput).toHaveValue("Semantic project");
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
  });

  it("renders the A-100 fork as a git-style DAG, not a flat edge list", async () => {
    stubBackend();
    render(<App showLabPanels />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    expect(screen.queryByLabelText("A-100 lineage")).not.toBeInTheDocument();
    expect(screen.queryByText("Public post → Linked post")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /rebuild lineage/i })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "View post: Public post" }));
    expect(await screen.findByLabelText("A-100 lineage")).toBeInTheDocument();
    expect(screen.getByLabelText("Open post: Pricing renegotiation follow-up")).toHaveClass(
      "lineage-dag-branch",
    );
    expect(screen.getByLabelText("Open post: Unrelated: annual account review")).toHaveClass(
      "lineage-dag-root",
    );
  });

  it("renders the board landmark and functional post controls", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    const board = await screen.findByRole("region", { name: "Board" });
    expect(within(board).getByRole("search", { name: "Search and filter posts" })).toBeInTheDocument();
    expect(within(board).getByLabelText("Search semantic evidence")).toHaveAttribute("type", "search");
    expect(within(board).getByRole("list", { name: "Board posts" })).toBeInTheDocument();
    expect(within(board).getByText(/Posts shown:/)).toBeInTheDocument();
    expect(within(board).getByLabelText("Voice of Partner")).toBeInTheDocument();

    await userEvent.selectOptions(within(board).getByLabelText("Sort posts"), "title");
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes("sort=title"))).toBe(true),
    );

    await userEvent.type(within(board).getByLabelText("Search semantic evidence"), "not found");
    await userEvent.click(within(board).getByRole("button", { name: "Search" }));
    expect(within(board).getByRole("status")).toHaveTextContent("No posts match the current filters.");
    await userEvent.click(within(board).getByRole("button", { name: "Reset filters" }));
    expect(within(board).getByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
  });

  it("opens a post from a DAG node click", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByLabelText("Open post: Linked post"));
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
    expect(screen.getByRole("dialog", { name: "Linked post" })).toHaveFocus();
  });

  it.each([
    [
      "comparison_candidates_available" as const,
      "Other visible posts share this comparison group, but no Event Lineage link is available. Read Keyman and evaluation next.",
    ],
    [
      "no_comparison_group" as const,
      "No other visible posts share this comparison group yet. Request reconstruction after more posts arrive, or read Keyman and evaluation.",
    ],
  ])(
    "explains an empty focused Event Lineage graph: %s",
    async (lineageIsolationReason, message) => {
      stubBackend({ lineageIsolationReason });
      render(<App showLabPanels />);
      await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
      expect(await screen.findByText(message)).toBeInTheDocument();
      expect(screen.queryByText("No linked posts yet.")).not.toBeInTheDocument();
    },
    15_000,
  );

  it("shows an embedded invoice image instead of the raw base64 string", async () => {
    const tinyPng =
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";
    stubBackend({
      postBody: `<p>Quote attached.</p><img src="data:image/png;base64,${tinyPng}" alt=""><p>Please confirm.</p>`,
    });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const image = await screen.findByRole("img", { name: "Embedded image" });
    expect(image).toHaveAttribute("src", `data:image/png;base64,${tinyPng}`);
    expect(screen.getByText("Quote attached.")).toBeInTheDocument();
    expect(screen.getByText("Please confirm.")).toBeInTheDocument();
    expect(screen.queryByText(/Extract Keyman or ask a question/)).not.toBeInTheDocument();
    expect(screen.queryByText(new RegExp(tinyPng))).not.toBeInTheDocument();
  });

  it("fetches and renders the post list, then opens a detail popup on click", async () => {
    const fetchMock = stubBackend();

    render(<App showLabPanels />);

    const listButton = await screen.findByRole("button", { name: "View post: Public post" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/posts"),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer test-access-token" }) }),
    );
    expect(listButton).toHaveTextContent("Voice of Customer");
    expect(listButton).toHaveTextContent("Public");

    await userEvent.click(listButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByText(/Voice of Customer ·/)).toBeInTheDocument();
    expect(screen.getByText("Constructive stance: 2")).toBeInTheDocument();
    expect(screen.getByText("Sales-lead specificity: 3")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Related posts" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open related post: Linked post" })).toBeInTheDocument();
    expect(screen.queryByText("Not yet evaluated.")).not.toBeInTheDocument();
  });

  it("announces the post-detail popup loading state as a live region before the post resolves", async () => {
    const fetchMock = stubBackend({ deferPostOne: true });

    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const popup = screen.getByRole("dialog", { name: "Post details" });
    expect(popup).toHaveFocus();
    expect(within(popup).getByRole("status")).toHaveTextContent("Loading...");

    fetchMock.releasePostOne();
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(within(popup).queryByText("Loading...")).not.toBeInTheDocument();
    expect(popup).toHaveAccessibleName("Public post");
  });

  it("closes the post-detail dialog with Escape and restores focus to its opener", async () => {
    stubBackend();
    const { rerender } = render(<App showLabPanels />);

    const opener = await screen.findByRole("button", { name: "View post: Public post" });
    await userEvent.click(opener);
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    expect(dialog).toHaveFocus();

    const collapsed = document.createElement("details");
    const collapsedButton = document.createElement("button");
    collapsedButton.textContent = "Collapsed action";
    collapsed.append(collapsedButton);
    dialog.append(collapsed);
    await userEvent.tab({ shift: true });
    const focusable = within(dialog)
      .getAllByRole("button")
      .filter((button) => !button.hasAttribute("disabled") && !button.closest("details:not([open])"));
    expect(focusable.at(-1)).toHaveFocus();
    expect(collapsedButton).not.toHaveFocus();
    await userEvent.tab();
    const closeButton = within(dialog).getByRole("button", { name: "Close" });
    expect(closeButton).toHaveFocus();

    rerender(<App showLabPanels />);
    expect(closeButton).toHaveFocus();

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("switches the product surface between supported languages", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const language = screen.getByRole("combobox", { name: "Language" });
    await userEvent.selectOptions(language, "ko");
    expect(screen.getByRole("heading", { name: "관련 글" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("ko");

    await userEvent.selectOptions(language, "en");
    expect(screen.getByRole("heading", { name: "Related posts" })).toBeInTheDocument();
  });

  it("persists the authenticated member's language preference", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    const language = await screen.findByRole("combobox", {
      name: /language|언어|言語|语言|ngôn ngữ/i,
    });
    await userEvent.selectOptions(language, "ja");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/me/preferences"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ preferred_locale: "ja" }),
        }),
      );
    });
  });

  it("rebuilds lineage when the account has post_admin", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByText("Advanced review tools"));
    await userEvent.click(await screen.findByRole("button", { name: /rebuild lineage/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/lineage/rebuild"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("shows the advanced-review section to post_admin without the test-only prop", async () => {
    stubBackend({ admin: true });
    render(<App />);
    await screen.findByRole("button", { name: "View post: Public post" });
    expect(await screen.findByText("Advanced review tools")).toBeInTheDocument();
  });

  it("hides the advanced-review section from accounts without post_admin, even without the test-only prop", async () => {
    stubBackend();
    render(<App />);
    await screen.findByRole("button", { name: "View post: Public post" });
    expect(screen.queryByText("Advanced review tools")).not.toBeInTheDocument();
  });

  it("renders the Korean summary, key events, R&R, and Event Lineage panels", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() => expect(screen.getByText("이것은 요약입니다.")).toBeInTheDocument());
    const provenance = screen.getByText("Why this item is listed").closest("details");
    expect(provenance).not.toBeNull();
    expect(provenance).not.toHaveAttribute("open");
    await userEvent.click(screen.getByText("Why this item is listed"));
    expect(screen.getByText(/Category:/)).toBeInTheDocument();
    expect(screen.getByText(/How this item was found: Semantic extraction/)).toBeInTheDocument();
    expect(screen.getByText(/Recorded evidence: Stored semantic evidence/)).toBeInTheDocument();
    expect(screen.queryByText("contextual_orchestrator_semantic")).not.toBeInTheDocument();
    expect(screen.queryByText("https://contextualwisdomlab.github.io/LineageWeave/ontology#Project")).not.toBeInTheDocument();
    expect(screen.getByText("첫 번째 이벤트")).toBeInTheDocument();
    expect(screen.getByText(/우리 측 후속/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "R&R Keyman: Ada West" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "R&R person: Priya Nair" })).toBeInTheDocument();
    expect(screen.getByText("당사").closest("li")).toHaveTextContent("Organization");
    expect(screen.queryByRole("button", { name: "R&R Keyman: 당사" })).not.toBeInTheDocument();
    const relatedPosts = screen.getByRole("heading", { name: "Related posts", level: 3 }).closest(
      ".related-posts-section",
    );
    expect(relatedPosts).not.toBeNull();
    expect(within(relatedPosts as HTMLElement).getByText("Indirect relation")).toBeInTheDocument();
    expect(within(relatedPosts as HTMLElement).getByText("Direct relation")).toBeInTheDocument();
    expect(within(relatedPosts as HTMLElement).getByText("Contains")).toBeInTheDocument();
    expect(relatedPosts).toHaveTextContent("Linked post");
    // The Event Lineage DAG belongs to the opened post, not the list surface.
    expect(screen.getAllByLabelText("A-100 lineage")).toHaveLength(1);
    expect(screen.getAllByLabelText("Open post: Pricing renegotiation follow-up")).toHaveLength(1);
    expect(document.getElementById("post-event-lineage")).not.toHaveFocus();
    expect(document.getElementById("post-ask")).not.toHaveFocus();
    expect(
      screen.queryByRole("status", { name: "Event Lineage next action" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Keyman next action" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Related next action" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Ask next action" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Ask seed next action" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Ask citation next action" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Evidence next action" })).not.toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: "Evidence" })).not.toBeInTheDocument();
    expect(screen.queryByText("Related to Ada West")).not.toBeInTheDocument();
    expect(screen.queryByText("Related to Priya Nair")).not.toBeInTheDocument();
    const popup = document.querySelector(".popup-panel");
    expect(popup).not.toBeNull();
    const evaluation = within(popup as HTMLElement).getByRole("heading", {
      name: "Post quality (IRT)",
    });
    const eventLineage = within(popup as HTMLElement).getByRole("heading", { name: "Event Lineage" });
    const affiliate = within(popup as HTMLElement).getByRole("heading", { name: "Affiliate tree" });
    const keyman = within(popup as HTMLElement).getByRole("heading", { name: "Keymen" });
    expect(evaluation.compareDocumentPosition(eventLineage) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
      0,
    );
    expect(affiliate.compareDocumentPosition(keyman) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    const ask = within(popup as HTMLElement).getByRole("heading", { name: "Ask about this lineage" });
    expect(keyman.compareDocumentPosition(ask) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it("labels a stale summary and retries the semantic refresh on request", async () => {
    const fetchMock = stubBackend({ staleSummary: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByText("Last saved summary shown. Retry semantic refresh.")).toBeInTheDocument(),
    );
    const summaryCallsBeforeRetry = fetchMock.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/posts/post-1/summary"),
    ).length;

    await userEvent.click(screen.getByRole("button", { name: "Retry summary refresh" }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/api/posts/post-1/summary"))
          .length,
      ).toBeGreaterThan(summaryCallsBeforeRetry),
    );
    expect(screen.getByRole("button", { name: "Retry summary refresh" })).toBeInTheDocument();
  });

  it("refreshes newly processed source content after summary generation", async () => {
    stubBackend({ contentAfterSummary: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    expect(await screen.findByText("Freshly processed source paragraph.")).toBeInTheDocument();
  });

  it("shows a seeded Ask exchange without an orchestrator round-trip", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument(),
    );
    expect(screen.getByText("Ada West and Priya Nair are the Keymen on this thread.")).toBeInTheDocument();
    expect(
      screen.getByText("The next commitment is Send Northridge Grid the revised quote, due 2026-01-12."),
    ).toBeInTheDocument();
    const homePopup = document.querySelector(".popup-panel");
    expect(homePopup).not.toBeNull();
    const homeAsk = within(homePopup as HTMLElement).getByRole("heading", {
      name: "Ask about this lineage",
    });
    const homeInput = within(homePopup as HTMLElement).getByPlaceholderText(/what happened/i);
    const homeAnswer = within(homePopup as HTMLElement).getByText(
      "The seeded follow-up after the site visit.",
    );
    expect(homeAsk.compareDocumentPosition(homeInput) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(homeInput.compareDocumentPosition(homeAnswer) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
      0,
    );
    expect(screen.queryByRole("complementary", { name: "Evidence" })).not.toBeInTheDocument();
    expect(
      screen.queryByText("The evidence panel should show exactly this text."),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask seeded question: what happened between these events/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask seeded question: who is involved/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask seeded question: what is the next commitment/i })).toBeInTheDocument();
  });

  it("asks a chat question and slides in the evidence panel for a cited source on click", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByPlaceholderText(/what happened/i)).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/what happened/i), "What happened?");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));

    await waitFor(() =>
      expect(screen.getByText("Here is what happened, drawing on the linked post.")).toBeInTheDocument(),
    );

    // The evidence panel is not shown until a citation is clicked.
    expect(screen.queryByText("The evidence panel should show exactly this text.")).not.toBeInTheDocument();

    const evidenceChips = screen.getAllByRole("button", { name: "Open evidence: Linked post" });
    await userEvent.click(evidenceChips[evidenceChips.length - 1]);

    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

  it("stops loading and gives the buyer a next action when cited evidence is unavailable", async () => {
    stubBackend({ evidenceUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.type(await screen.findByPlaceholderText(/what happened/i), "What happened?");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));
    const evidenceChips = await screen.findAllByRole("button", { name: "Open evidence: Linked post" });
    await userEvent.click(evidenceChips[evidenceChips.length - 1]);

    expect(
      await screen.findByText("Source evidence is unavailable. Continue with the saved answer."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Loading source post...")).not.toBeInTheDocument();
  });

  it("shows a clear empty state when chat is 503 without an orchestrator", async () => {
    stubBackend({ chatUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByPlaceholderText(/what happened/i)).toBeInTheDocument());
    await userEvent.type(screen.getByPlaceholderText(/what happened/i), "What happened?");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));

    await waitFor(() =>
      expect(screen.getByText("Chat is temporarily unavailable. Saved evidence is still available.")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/what happened/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^ask$/i })).not.toBeInTheDocument();
    expect(
      screen.getByText("Interactive questions are unavailable right now; saved evidence remains available."),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /ask seeded question/i })).toHaveLength(3);
    expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument();
    expect(screen.getByText("Ada West and Priya Nair are the Keymen on this thread.")).toBeInTheDocument();
    expect(
      screen.getByText("The next commitment is Send Northridge Grid the revised quote, due 2026-01-12."),
    ).toBeInTheDocument();
  });

  it("shows a clear empty state when evaluate is 503 without an orchestrator", async () => {
    stubBackend({ admin: true, chatUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /evaluate post/i }));

    await waitFor(() =>
      expect(screen.getByText("Evaluation is temporarily unavailable. Saved evidence is still available.")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /evaluate post/i })).not.toBeInTheDocument();
  });

  it("shows a clear empty state when extract Keymen is 503 without an orchestrator", async () => {
    stubBackend({ admin: true, chatUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /extract keymen/i }));

    await waitFor(() =>
      expect(screen.getByText("Keymen extraction is temporarily unavailable. Saved evidence is still available.")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /extract keymen/i })).not.toBeInTheDocument();
  });

  it("shows a clear empty state when derive commitment is 503 without an orchestrator", async () => {
    stubBackend({ admin: true, chatUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /derive commitment/i }));

    await waitFor(() =>
      expect(
        screen.getByText("Commitment derivation is temporarily unavailable. Saved evidence is still available."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /derive commitment/i })).not.toBeInTheDocument();
  });

  it("shows a clear empty state when verify is 503 without search", async () => {
    stubBackend({ admin: true, searchUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /verify against web search/i }));

    await waitFor(() =>
      expect(
        screen.getByText(
          "Verification is unavailable because public search is not configured yet. Ask an administrator to enable it, then retry.",
        ),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /verify against web search/i })).not.toBeInTheDocument();
  });

  it("shows the affiliate tree, VOC excerpt, and related Keyman nodes on click", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() => expect(screen.getByText("Demo Group")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Affiliate org: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Counterparty org: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Keyman affiliation: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByText("(Company)")).toBeInTheDocument();
    expect(screen.getAllByText(/Ada West \(Our side\)/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Account manager")).toBeInTheDocument();
    expect(screen.queryByText(/our_side/)).not.toBeInTheDocument();
    expect(screen.getByText("unresolved")).toBeInTheDocument();
    expect(screen.getByText(/Voice of Customer\s*\(voc\)/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "VOC Keyman: Northridge Grid" })).toBeInTheDocument();
    expect(screen.getByLabelText("VOC verification: Northridge Grid")).toHaveTextContent("Not yet checked");
    expect(
      screen.getByText(
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
      ),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).toHaveTextContent(
      "Priya Nair (Counterparty)",
    );
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).not.toHaveTextContent(
      "Priya Nair (Person)",
    );
    // Feature request (2026-08-19): clicking a Keyman should show how
    // their responsibility/organization changed over time, in order.
    const roleHistoryList = screen.getByRole("list", { name: "Role history: Ada West" });
    expect(roleHistoryList).toHaveTextContent("junior account rep at Northwind Labs");
    expect(roleHistoryList).toHaveTextContent("account lead at Demo Corp");
    const historyItems = within(roleHistoryList).getAllByRole("listitem");
    expect(historyItems[0]).toHaveTextContent("junior account rep");
    expect(historyItems[1]).toHaveTextContent("account lead");
    expect(
      screen.getByRole("button", {
        name: "Related nodes for Priya Nair (Counterparty)",
      }),
    ).toBeInTheDocument();
    const relatedPosts = screen.getByRole("heading", { name: "Related posts", level: 3 }).closest(
      ".related-posts-section",
    );
    await userEvent.click(
      within(relatedPosts as HTMLElement).getByRole("button", {
        name: "Open related post: Linked post",
      }),
    );
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

  it("shows the corroborated SKOS companion on organization chips", async () => {
    stubBackend({ organizationAliases: true });
    render(<App showLabPanels />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Affiliate org: Demo Corp (DC)" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Counterparty org: Demo Corp (DC)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Keyman affiliation: Demo Corp (DC)" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Affiliate org: Demo Corp" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Related nodes for Demo Corp (DC)" })).toBeInTheDocument();
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).toHaveTextContent(
      "Demo Corp (DC)",
    );
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).not.toHaveTextContent(
      "Demo Corp (Organization)",
    );
  }, 10_000);

  it("opens related Keyman nodes from an R&R person", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "R&R Keyman: Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).toHaveTextContent(
      "Priya Nair (Counterparty)",
    );
    const relatedPosts = screen.getByRole("list", { name: "Related posts: Ada West" });
    expect(within(relatedPosts).getByRole("button", { name: "Open related post: Linked post" })).toBeInTheDocument();
    await userEvent.click(within(relatedPosts).getByText("Linked post", { selector: "strong" }));
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

  it("opens related nodes from an R&R person catalog id", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "R&R person: Priya Nair" }));
    await waitFor(() => expect(screen.getByText("Related to Priya Nair")).toBeInTheDocument());
    expect(screen.getByText("Related to Priya Nair").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
  });

  it("opens related nodes from an R&R team", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "R&R team: 설계팀" }));
    await waitFor(() => expect(screen.getByText("Related to 설계팀")).toBeInTheDocument());
    expect(screen.getByText("Related to 설계팀").closest(".related-keymen")).toHaveTextContent(
      "Linked post",
    );
  });

  it("opens related nodes from a related team chip", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for 설계팀 (Team)" }));
    await waitFor(() => expect(screen.getByText("Related to 설계팀")).toBeInTheDocument());
    expect(screen.getByText("Related to 설계팀").closest(".related-keymen")).toHaveTextContent(
      "Linked post",
    );
  });

  it("opens related nodes from a related corporate entity", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    await userEvent.click(
      screen.getByRole("button", { name: "Related nodes for Demo Corp (Corporate entity)" }),
    );
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(screen.getByText("Related to Demo Corp").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
  });

  it("shows the VOC excerpt under its counterparty, not a detached list", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const name = await screen.findByRole("button", { name: "VOC Keyman: Northridge Grid" });
    const excerpt = screen.getByText(
      "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
    );
    expect(excerpt.tagName).toBe("BLOCKQUOTE");
    expect(name.closest(".voc-counterparty")).toContainElement(excerpt);
    expect(
      screen.getAllByText(
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
      ),
    ).toHaveLength(1);
    const unassigned = screen.getByText("The weekly recap listed the delay against the open ticket.");
    expect(unassigned.closest(".voc-excerpt-list")).not.toBeNull();
    expect(unassigned.closest(".voc-counterparty")).toBeNull();
  });

  it("opens related Keyman nodes from a VOC counterparty organization", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "VOC Keyman: Northridge Grid" }));
    await waitFor(() => expect(screen.getByText("Related to Priya Nair")).toBeInTheDocument());
    expect(screen.getByText("Related to Priya Nair").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
  });

  it("opens related Keyman nodes from an affiliate-tree person", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Affiliate Keyman: Priya Nair" }));
    await waitFor(() => expect(screen.getByText("Related to Priya Nair")).toBeInTheDocument());
    expect(screen.getByText("Related to Priya Nair").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
  });

  it("opens related nodes from a Keyman affiliation organization", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Keyman affiliation: Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(screen.getByText("Related to Demo Corp").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
  });

  it("opens related nodes from an affiliate-tree organization", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Affiliate org: Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(screen.getByText("Related to Demo Corp").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
    expect(screen.queryByRole("button", { name: "Affiliate org: Northridge Grid" })).not.toBeInTheDocument();
  });

  it("opens related nodes from a classified counterparty organization", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Counterparty org: Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(screen.getByText("Related to Demo Corp").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
    expect(screen.queryByRole("button", { name: "Counterparty org: Northridge Grid" })).not.toBeInTheDocument();
  });

  it("links a verification badge only for http(s) evidence URLs", async () => {
    stubBackend({ verificationEvidenceUrl: "https://example.test/searxng?q=Northridge" });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const badge = await screen.findByRole("link", { name: "VOC verification: Northridge Grid" });
    expect(badge).toHaveAttribute("href", "https://example.test/searxng?q=Northridge");
  });

  it("does not turn a javascript: evidence URL into a verification link", async () => {
    stubBackend({ verificationEvidenceUrl: "javascript:alert(1)" });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByLabelText("VOC verification: Northridge Grid")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("link", { name: "VOC verification: Northridge Grid" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("VOC verification: Northridge Grid").tagName).toBe("SPAN");
  });

  it("lets post_admin verify pending counterparties against web search", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByLabelText("VOC verification: Northridge Grid")).toHaveTextContent("Not yet checked"),
    );
    expect(screen.getByLabelText("Counterparty verification: Northridge Grid")).toHaveTextContent(
      "Not yet checked",
    );
    await userEvent.click(screen.getByRole("button", { name: /verify against web search/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/posts/post-1/verify-relations"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("lets post_admin extract Keymen from the popup", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /extract keymen/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/posts/post-1/extract-keymen"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("creates an issue ticket and updates its status via the real endpoints", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("No tickets yet.")).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/new ticket title/i), "Confirm delivery window");
    await userEvent.click(screen.getByRole("button", { name: /create ticket/i }));

    await waitFor(() => expect(screen.getByText("Confirm delivery window")).toBeInTheDocument());

    const statusSelect = screen.getByLabelText(/status for confirm delivery window/i);
    expect(statusSelect).toHaveValue("open");
    expect(screen.getByRole("option", { name: "Open" })).toHaveValue("open");
    expect(screen.queryByRole("option", { name: "open" })).not.toBeInTheDocument();

    await userEvent.selectOptions(statusSelect, "closed");

    await waitFor(() => expect(statusSelect).toHaveValue("closed"));
    expect(screen.getByRole("option", { name: "Closed" })).toHaveValue("closed");
  });

  it("creates a dated ticket and shows the due date on the ticket list", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("No tickets yet.")).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/new ticket title/i), "Ship the sample kit");
    fireEvent.change(screen.getByLabelText(/due date/i), { target: { value: "2026-03-15" } });
    await userEvent.click(screen.getByRole("button", { name: /create ticket/i }));

    await waitFor(() => expect(screen.getByText("Ship the sample kit")).toBeInTheDocument());
    expect(screen.getByText("due 2026-03-15")).toBeInTheDocument();
  });

  it("shows real ticket mutations on the activity feed after a refresh", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("No activity yet.")).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText(/new ticket title/i), "Confirm freight terms");
    await userEvent.click(screen.getByRole("button", { name: /create ticket/i }));
    await waitFor(() => expect(screen.getByText("Confirm freight terms")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));

    await waitFor(() =>
      expect(screen.getByText("Ticket created: Confirm freight terms")).toBeInTheDocument(),
    );
    expect(screen.getByText("Ticket created")).toBeInTheDocument();
    expect(screen.queryByText("ticket_created")).not.toBeInTheDocument();

    await userEvent.selectOptions(
      screen.getByLabelText(/status for confirm freight terms/i),
      "closed",
    );
    await userEvent.click(screen.getByRole("button", { name: /^refresh$/i }));
    await waitFor(() =>
      expect(screen.getByText("Ticket status changed to Closed")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Ticket status changed to closed")).not.toBeInTheDocument();
    expect(screen.getByText("Status changed")).toBeInTheDocument();
    expect(screen.queryByText("ticket_status_changed")).not.toBeInTheDocument();
  });

  it("hides derive commitment for accounts without post_admin", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("No tickets yet.")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /derive commitment/i })).not.toBeInTheDocument();
  });

  it("derives a customer commitment and shows its due date on the ticket list", async () => {
    stubBackend({ admin: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("No tickets yet.")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /derive commitment/i }));

    await waitFor(() =>
      expect(screen.getByText("Send the revised delivery schedule")).toBeInTheDocument(),
    );
    expect(screen.getByText("due 2026-01-09")).toBeInTheDocument();
  });

  it("tells the buyer how to populate an empty calendar", async () => {
    stubBackend({ calendarCommitments: [] });
    render(<App showLabPanels />);

    await waitFor(() =>
      expect(
        screen.getByText(/no upcoming commitments\. derive one from a post/i),
      ).toBeInTheDocument(),
    );
  });

  it("names rankings unavailability on home rankings instead of inventing a score", async () => {
    stubBackend();
    render(<App />);

    expect(
      await screen.findByText(
        "Rankings are not available right now. Reopen this post later to load them.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Pricing renegotiation: revised quote sent")).not.toBeInTheDocument();
  });

  it("drops a prior post's in-flight similar-VOC page after navigation", async () => {
    const backend = stubBackend();
    const original = backend.getMockImplementation() as (
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => Promise<Response>;
    let releasePage!: (response: Response) => void;
    const deferredPage = new Promise<Response>((resolve) => { releasePage = resolve; });
    backend.mockImplementation((...args) => {
      const requestUrl = new URL(String(args[0]), "https://backend.test");
      if (requestUrl.pathname === "/api/posts/post-1/similar-voc") {
        if (requestUrl.searchParams.get("offset") === "50") return deferredPage;
        return Promise.resolve(jsonResponse({
          items: [{
            post_id: "prior-1", post_title: "Prior evidence", issue_summary: "Prior issue",
            focal_evidence_text: "Current evidence", candidate_evidence_text: "Prior evidence",
            customer_cohort_text: null, action_history: [], occurred_at: "2025-12-01T00:00:00Z",
          }],
          next_offset: 50,
        }));
      }
      return original(args[0] as RequestInfo | URL, args[1] as RequestInit | undefined);
    });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: /open report post: public post/i }));
    await userEvent.click(await screen.findByRole("button", { name: "이전 VOC 더 보기" }));
    await userEvent.click((await screen.findAllByLabelText("Open post: Linked post"))[0]);
    await screen.findByText("The evidence panel should show exactly this text.");
    releasePage(jsonResponse({
      items: [{
        post_id: "stale-prior", post_title: "Stale prior VOC", issue_summary: "Stale issue",
        focal_evidence_text: "Stale current", candidate_evidence_text: "Stale prior",
        customer_cohort_text: null, action_history: [], occurred_at: "2025-11-01T00:00:00Z",
      }],
      next_offset: null,
    }));
    await waitFor(() => expect(screen.queryByText("Stale prior VOC")).not.toBeInTheDocument());
  }, 15_000);

  it("opens an accepted ranking hit without inventing a fused score", async () => {
    stubBackend({
      rankings: {
        status: "accepted",
        status_reason: null,
        rankings: [
          {
            post_id: "post-1",
            post_title: "Public post",
            fused_rank: 1,
            channel_evidence: [
              {
                signal_code: "lexical",
                signal_label: "Title overlap",
                channel_rank: 2,
                weight: 0.75,
                contribution: 0.75 / 62,
                rank: 1,
              },
              {
                signal_code: "temporal",
                signal_label: "Newest first",
                channel_rank: 2,
                weight: 0.25,
                contribution: 0.25 / 62,
                rank: 2,
              },
            ],
          },
          {
            post_id: "post-2",
            post_title: "Pricing renegotiation: revised quote sent",
            fused_rank: 2,
            channel_evidence: [
              {
                signal_code: "lexical",
                signal_label: "Title overlap",
                channel_rank: 1,
                weight: 0.75,
                contribution: 0.75 / 61,
                rank: 1,
              },
              {
                signal_code: "temporal",
                signal_label: "Newest first",
                channel_rank: 1,
                weight: 0.25,
                contribution: 0.25 / 61,
                rank: 2,
              },
            ],
          },
        ],
      },
    });
    render(<App />);

    const rankingButton = await screen.findByRole("button", {
      name: /open ranking: public post/i,
    });
    expect(rankingButton).toHaveTextContent("Public post");
    expect(rankingButton).toHaveTextContent("Rankings");
    expect(rankingButton).toHaveTextContent("rank 1");
    expect(
      screen.getByText(
        "Rankings combine newest-first and title-overlap evidence and are not calibrated scores. Open a ranked post to see its evidence.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Ranking evidence for Public post" }),
    ).toHaveTextContent("Title overlap rank 2, contribution 0.012097");
    expect(
      screen.getByRole("list", { name: "Ranking evidence for Public post" }),
    ).toHaveTextContent("Newest first rank 2, contribution 0.004032");
    expect(screen.queryByRole("button", { name: /open ranking: private parent/i })).not.toBeInTheDocument();

    await userEvent.click(rankingButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("shows upcoming commitments on the home page calendar and opens the post on click", async () => {
    stubBackend();
    render(<App showLabPanels />);

    const calendarButton = await screen.findByRole("button", {
      name: /open commitment for: public post/i,
    });
    expect(calendarButton).toHaveTextContent("Send Northridge Grid the revised quote");
    expect(calendarButton).toHaveTextContent("Public post");
    expect(calendarButton).toHaveTextContent("Open");
    expect(calendarButton).toHaveTextContent("due 2026-01-12");
    const betaCalendar = screen.getByRole("button", {
      name: /open commitment for: specification revision requested/i,
    });
    expect(betaCalendar).toHaveTextContent("Send Westfield Power the revised specification");
    expect(betaCalendar).toHaveTextContent("Open");
    expect(betaCalendar).toHaveTextContent("due 2026-01-14");

    await userEvent.click(calendarButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("shows the seeded analysis run on the home page", async () => {
    stubBackend();
    render(<App showLabPanels />);

    expect(await screen.findByRole("heading", { name: "Analysis runs" })).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Analysis runs" });
    expect(list).toHaveTextContent("Lineage reconstruction · Succeeded · Demo Corp");
    expect(list).toHaveTextContent("TEPP measurement · Failed · Demo Corp");
    expect(list).toHaveTextContent("Period report · Succeeded · Demo Corp");
    expect(list).toHaveTextContent(
      "Open this run to see why it failed, then retry with the latest available records.",
    );
    expect(list).toHaveTextContent("3 documents");
    expect(list).not.toHaveTextContent("postgresql://");
    expect(list).not.toHaveTextContent("select ");
    expect(list).not.toHaveTextContent("Claimed");
    expect(list).not.toHaveTextContent("Delivered");
    expect(list).not.toHaveTextContent("Code abcdef012345");
    expect(list).not.toHaveTextContent("Config 0123456789ab");
    expect(list).not.toHaveTextContent("abcdef0123456789deadbeefcafebabe");
    expect(list).not.toHaveTextContent(
      "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    );

    await userEvent.click(
      screen.getByRole("button", {
        name: "Open analysis run: Lineage reconstruction · Succeeded · Demo Corp",
      }),
    );
    expect(await screen.findByRole("heading", { name: "Lineage reconstruction · Succeeded · Demo Corp" })).toBeInTheDocument();
    expect(screen.getByText(/Cutoff 2026-01-12/)).toBeInTheDocument();
    expect(screen.getByText(/Requested 2026-01-12/)).toBeInTheDocument();
    const digests = screen.getByLabelText("Analysis run reproducibility digests");
    expect(digests).toHaveTextContent("Hover a prefix to read the full digest for verification.");
    expect(digests).toHaveTextContent("Code abcdef012345");
    expect(digests).toHaveTextContent("Config 0123456789ab");
    expect(digests).not.toHaveTextContent("abcdef0123456789deadbeefcafebabe");
    expect(digests).not.toHaveTextContent(
      "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    );
    expect(screen.getByTitle("abcdef0123456789deadbeefcafebabe")).toHaveTextContent("Code abcdef012345");
    expect(
      screen.getByTitle("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"),
    ).toHaveTextContent("Config 0123456789ab");
    const history = screen.getByRole("list", { name: "Analysis run status history" });
    expect(history).toHaveTextContent("Pending 2026-01-12 12:31");
    expect(history).toHaveTextContent("Running 2026-01-12 12:32");
    expect(history).toHaveTextContent("Succeeded 2026-01-12 12:33");
    const outbox = screen.getByRole("list", { name: "Analysis run outbox delivery" });
    expect(outbox).toHaveTextContent("Claimed 2026-01-12 12:32");
    expect(outbox).toHaveTextContent("Delivered 2026-01-12 12:33");
    expect(outbox).not.toHaveTextContent("valkey");
    expect(outbox).not.toHaveTextContent("stream");
    expect(screen.getByRole("list", { name: "Posts known at this run cutoff" })).toBeInTheDocument();
    const seededFork = screen.getByRole("list", { name: "Reconstructed lineage edges" });
    expect(seededFork).toHaveTextContent(
      "Pricing renegotiation: revised quote sent follows Pricing renegotiation follow-up",
    );
    expect(seededFork).toHaveTextContent(
      "Delivery schedule question raised follows Pricing renegotiation follow-up",
    );
    await userEvent.click(
      screen.getByRole("button", {
        name: "Open reconstructed child: Pricing renegotiation: revised quote sent",
      }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.getByRole("list", { name: "Posts known at this run cutoff" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Opening a title shows the live post. Titles marked updated after cutoff were rewritten after 2026-01-12. Compare those bodies with this run before you treat them as reconstructed evidence.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open live post (updated after cutoff): Public post",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open live post: Private post",
      }),
    ).toBeInTheDocument();
    const cutoffPosts = screen.getByRole("list", { name: "Posts known at this run cutoff" });
    expect(cutoffPosts).toHaveTextContent("Updated after cutoff");
    expect(screen.getByRole("button", { name: "Open live post: Private post" }).closest("li")).not.toHaveTextContent(
      "Updated after cutoff",
    );
    expect(screen.queryByText(/postgresql:\/\//)).not.toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", {
        name: "Open live post (updated after cutoff): Public post",
      }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());

    await userEvent.click(
      screen.getByRole("button", {
        name: "Open analysis run: TEPP measurement · Failed · Demo Corp",
      }),
    );
    expect(
      await screen.findByRole("heading", { name: "TEPP measurement · Failed · Demo Corp" }),
    ).toBeInTheDocument();
    const teppHistory = screen.getByRole("list", { name: "Analysis run status history" });
    expect(teppHistory).toHaveTextContent("Failed 2026-01-12 12:37 · tepp_not_available");
    expect(screen.getByText(/cutoff corpus TEPP would measure/i)).toBeInTheDocument();
    expect(teppHistory).not.toHaveTextContent("Succeeded");
  });

  it("warns that a cutoff-rewritten title opens the live body, not a snapshot", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: Lineage reconstruction · Succeeded · Demo Corp",
      }),
    );
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open live post (updated after cutoff): Public post",
      }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByRole("status", { name: "Live body warning" })).toHaveTextContent(
      "This is the live body, not a cutoff snapshot. Compare it with this 2026-01-12 run before you treat it as reconstructed evidence.",
    );
    expect(screen.getByRole("heading", { name: "Body this run knew" })).toBeInTheDocument();
    expect(screen.getByText("The cutoff body this run knew.")).toBeInTheDocument();
    expect(screen.getByText(/written 2026-01-10, known at cutoff 2026-01-12/)).toBeInTheDocument();

    const linkedPosts = screen.getAllByLabelText("Open post: Linked post");
    await userEvent.click(linkedPosts[linkedPosts.length - 1]);
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("status", { name: "Live body warning" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(
      screen.getByRole("button", {
        name: "Open live post: Private post",
      }),
    );
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("status", { name: "Live body warning" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Body this run knew" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(screen.getByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.queryByRole("status", { name: "Live body warning" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Body this run knew" })).not.toBeInTheDocument();
  });

  it("tells a running lineage run to refresh the durable outbox", async () => {
    stubBackend({ runningLineageRun: true });
    render(<App showLabPanels />);

    const lineageButton = await screen.findByRole("button", {
      name: "Open analysis run: Lineage reconstruction · Running · Demo Corp",
    });
    expect(lineageButton).toHaveTextContent(
      "Refresh this run. Start already queued the work on the durable outbox.",
    );
    await userEvent.click(lineageButton);
    expect(
      screen.queryByRole("button", { name: "Start reconstruction" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getAllByText("Refresh this run. Start already queued the work on the durable outbox."),
    ).not.toHaveLength(0);
  });

  it("does not tell a failed lineage run to connect the measurement service", async () => {
    stubBackend({ failedLineageRun: true });
    render(<App showLabPanels />);

    await screen.findByRole("list", { name: "Analysis runs" });
    const lineageButton = screen.getByRole("button", {
      name: "Open analysis run: Lineage reconstruction · Failed · Demo Corp",
    });
    const teppButton = screen.getByRole("button", {
      name: "Open analysis run: TEPP measurement · Failed · Demo Corp",
    });
    expect(lineageButton).toHaveTextContent(
      "Open this run to see why it failed, then retry reconstruction from a current snapshot.",
    );
    expect(lineageButton).not.toHaveTextContent("measurement service");
    expect(teppButton).toHaveTextContent(
      "Open this run to see why it failed, then retry with the latest available records.",
    );
    expect(teppButton).not.toHaveTextContent("measurement service");
    expect(teppButton).not.toHaveTextContent("reconstruction");
  });

  it("does not tell a succeeded period report to rebuild, reconstruct, or measure", async () => {
    stubBackend({ succeededReportRun: true });
    render(<App showLabPanels />);

    const reportButton = await screen.findByRole("button", {
      name: "Open analysis run: Period report · Succeeded · Demo Corp",
    });
    expect(reportButton).not.toHaveTextContent("rebuild the period report");
    expect(reportButton).not.toHaveTextContent("Reconstruction has not started yet");
    expect(reportButton).not.toHaveTextContent("The report has not been built yet");
    expect(reportButton).not.toHaveTextContent("measurement service");
    expect(reportButton).not.toHaveTextContent("θ");

    await userEvent.click(reportButton);
    expect(
      await screen.findByRole("heading", { name: "Period report · Succeeded · Demo Corp" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/rebuild the period report/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Reconstruction has not started yet/)).not.toBeInTheDocument();
    expect(screen.queryByText(/The report has not been built yet/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open live post: Public post",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open period report 2026-W02" })).toBeInTheDocument();

    const periodInput = screen.getByLabelText("Report period");
    await userEvent.clear(periodInput);
    await userEvent.type(periodInput, "2026-W03");
    expect(periodInput).toHaveValue("2026-W03");
    const groupingSelect = screen.getByLabelText("Report grouping");
    expect(groupingSelect).toHaveValue("process_unit");
    await userEvent.click(screen.getByRole("button", { name: "Open period report 2026-W02" }));
    expect(periodInput).toHaveValue("2026-W02");
    expect(groupingSelect).toHaveValue("corporate_entity");
    expect(periodInput).toHaveFocus();
    expect(
      screen.getByRole("button", { name: "Compare Corporate entity: Demo Corp, mean θ 0.42" }),
    ).toHaveAttribute("aria-current", "true");
    expect(
      screen.getByRole("button", { name: "Compare Business unit (PU): Demo Report High, mean θ 0.81" }),
    ).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Demo Corp is the opened grouping. Read its mean θ and member posts below, then open a post.",
    );
    expect(await screen.findByText(/Demo Corp: mean θ 0\.42/)).toBeInTheDocument();
    expect(screen.queryByText(/corp-1: mean θ/)).not.toBeInTheDocument();
    const openedReport = screen.getByRole("list", { name: "Opened grouping report" });
    expect(openedReport.textContent ?? "").toMatch(/Demo Corp: mean θ 0\.42[\s\S]*Other Corp: mean θ/);
    expect(
      within(openedReport).getByRole("button", { name: /open report post: public post/i }),
    ).toBeInTheDocument();
    const status = screen.getByRole("status");
    const demoMean = screen.getByText(/Demo Corp: mean θ 0\.42/);
    const weekChip = screen.getByRole("button", { name: /open report period 2026-W03/i });
    expect(status.compareDocumentPosition(demoMean) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(demoMean.compareDocumentPosition(weekChip) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it("lands the comparison strip on Demo Corp when already on that week", async () => {
    stubBackend({ succeededReportRun: true });
    const scrollIntoView = vi.fn();
    const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView = scrollIntoView;
    try {
      render(<App showLabPanels />);

      const periodInput = await screen.findByLabelText("Report period");
      expect(periodInput).toHaveValue("2026-W02");
      expect(screen.getByLabelText("Report grouping")).toHaveValue("process_unit");

      await userEvent.click(
        await screen.findByRole("button", {
          name: "Open analysis run: Period report · Succeeded · Demo Corp",
        }),
      );
      await userEvent.click(screen.getByRole("button", { name: "Open period report 2026-W02" }));

      expect(periodInput).toHaveValue("2026-W02");
      expect(screen.getByLabelText("Report grouping")).toHaveValue("corporate_entity");
      const demoChip = screen.getByRole("button", {
        name: "Compare Corporate entity: Demo Corp, mean θ 0.42",
      });
      expect(demoChip).toHaveAttribute("aria-current", "true");
      expect(demoChip).toHaveFocus();
      expect(demoChip).toHaveAccessibleName(/Corporate entity: Demo Corp/);
      expect(demoChip).toHaveAccessibleName(/mean θ 0\.42/);
      expect(scrollIntoView).toHaveBeenCalled();
      expect(periodInput).not.toHaveFocus();
      expect(screen.getByRole("status")).toHaveTextContent(
        "Demo Corp is the opened grouping. Read its mean θ and member posts below, then open a post.",
      );
      expect(await screen.findByText(/Demo Corp: mean θ 0\.42/)).toBeInTheDocument();
      const openedReport = screen.getByRole("list", { name: "Opened grouping report" });
      expect(within(openedReport).getByText(/Demo Corp: mean θ 0\.42/).closest("li")).toHaveAttribute(
        "aria-current",
        "true",
      );
      expect(openedReport.textContent ?? "").toMatch(/Demo Corp: mean θ 0\.42[\s\S]*Other Corp: mean θ/);
      expect(openedReport.textContent ?? "").not.toMatch(/Other Corp: mean θ[\s\S]*Demo Corp: mean θ 0\.42/);
      const member = within(openedReport).getByRole("button", {
        name: /open report post: public post/i,
      });
      expect(member).toHaveTextContent("θ 0.91");
      expect(member).not.toHaveAttribute("aria-current");
      const status = screen.getByRole("status");
      const demoMean = screen.getByText(/Demo Corp: mean θ 0\.42/);
      const weekChip = screen.getByRole("button", { name: /open report period 2026-W03/i });
      expect(status.compareDocumentPosition(demoMean) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      expect(demoMean.compareDocumentPosition(weekChip) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      await userEvent.click(member);
      await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
      expect(member).toHaveAttribute("aria-current", "true");
      expect(
        screen.getByText(
          "Public post is open from Demo Corp. Read Event Lineage, Keyman, and evaluation on this post.",
        ),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "Public post is open from Demo Corp. Read Event Lineage, Keyman, and evaluation on this post.",
        ),
      ).not.toHaveTextContent("then open a post");
      expect(
        screen.getAllByRole("heading", { name: "Event Lineage" }),
      ).toHaveLength(1);
      const popup = document.querySelector(".popup-panel");
      expect(popup).not.toBeNull();
      const currentNode = within(popup as HTMLElement).getByLabelText("Open post: Public post");
      expect(currentNode).toHaveAttribute("aria-current", "true");
      const lineageNext = screen.getByRole("status", { name: "Event Lineage next action" });
      expect(lineageNext).toHaveTextContent(
        "Public post is current in Event Lineage. Read Keyman and evaluation next.",
      );
      expect(
        currentNode.compareDocumentPosition(lineageNext) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      const keyman = within(popup as HTMLElement).getByRole("heading", { name: "Keymen" });
      const evaluation = within(popup as HTMLElement).getByRole("heading", {
        name: "Post quality (IRT)",
      });
      const affiliate = within(popup as HTMLElement).getByRole("heading", { name: "Affiliate tree" });
      expect(lineageNext.compareDocumentPosition(keyman) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
        0,
      );
      expect(keyman.compareDocumentPosition(evaluation) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      const keymanNext = await screen.findByRole("status", { name: "Keyman next action" });
      expect(keymanNext).toHaveTextContent("Ada West is the first Keyman. Read that person next.");
      const related = await within(popup as HTMLElement).findByRole("heading", {
        name: "Related to Ada West",
      });
      expect(within(related.closest(".related-keymen") as HTMLElement).getByText(/Priya Nair/)).toBeInTheDocument();
      expect(
        within(popup as HTMLElement).getByRole("button", { name: "Related nodes for Ada West" }),
      ).toHaveAttribute("aria-current", "true");
      expect(
        evaluation.compareDocumentPosition(keymanNext) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(keymanNext.compareDocumentPosition(related) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
        0,
      );
      const relatedNext = await screen.findByRole("status", { name: "Related next action" });
      expect(relatedNext).toHaveTextContent(
        "Priya Nair is the first related node. Read that person next.",
      );
      expect(
        within(popup as HTMLElement).getByRole("button", {
          name: "Related nodes for Priya Nair (Counterparty)",
        }),
      ).toHaveAttribute("aria-current", "true");
      const landedRelated = await within(popup as HTMLElement).findByRole("heading", {
        name: "Related to Priya Nair",
      });
      expect(
        within(landedRelated.closest(".related-keymen") as HTMLElement).getByText(/Ada West/),
      ).toBeInTheDocument();
      expect(related.compareDocumentPosition(relatedNext) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
        0,
      );
      expect(
        relatedNext.compareDocumentPosition(landedRelated) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      const askNext = await screen.findByRole("status", { name: "Ask next action" });
      expect(askNext).toHaveTextContent(
        "Related nodes for Priya Nair are current. Ask about this lineage next.",
      );
      expect(
        landedRelated.compareDocumentPosition(askNext) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(askNext.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
        0,
      );
      const ask = within(popup as HTMLElement).getByRole("heading", { name: "Ask about this lineage" });
      expect(askNext.compareDocumentPosition(ask) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      expect(ask.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      const askSeed = await screen.findByRole("status", { name: "Ask seed next action" });
      expect(askSeed).toHaveTextContent(
        "What happened between these events? is the first Ask. Read that answer next.",
      );
      expect(ask.compareDocumentPosition(askSeed) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      expect(askSeed.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
      expect(
        within(popup as HTMLElement).getByRole("button", {
          name: "Ask seeded question: What happened between these events?",
        }),
      ).toHaveAttribute("aria-current", "true");
      const firstAskAnswer = within(popup as HTMLElement).getByText(
        "The seeded follow-up after the site visit.",
      );
      const askInput = within(popup as HTMLElement).getByPlaceholderText(/what happened/i);
      expect(
        askSeed.compareDocumentPosition(firstAskAnswer) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(
        firstAskAnswer.compareDocumentPosition(askInput) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(
        firstAskAnswer.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(
        within(popup as HTMLElement).getAllByText("The seeded follow-up after the site visit."),
      ).toHaveLength(1);
      const citedNext = await screen.findByRole("status", { name: "Ask citation next action" });
      expect(citedNext).toHaveTextContent(
        "Linked post is the first cited source. Open that evidence next.",
      );
      expect(
        firstAskAnswer.compareDocumentPosition(citedNext) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(citedNext.compareDocumentPosition(askInput) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
        0,
      );
      expect(
        within(popup as HTMLElement).getByRole("button", { name: "Open evidence: Linked post" }),
      ).toHaveAttribute("aria-current", "true");
      const citedEvidence = await screen.findByRole("complementary", { name: "Evidence" });
      expect(await within(citedEvidence).findByText("Linked post")).toBeInTheDocument();
      expect(
        await within(citedEvidence).findByText("The evidence panel should show exactly this text."),
      ).toBeInTheDocument();
      expect(
        citedNext.compareDocumentPosition(citedEvidence) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(
        citedEvidence.compareDocumentPosition(askInput) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      const evidenceNext = await screen.findByRole("status", { name: "Evidence next action" });
      expect(evidenceNext).toHaveTextContent(
        "Linked post evidence is current. Read Event Lineage on that post next.",
      );
      expect(
        citedEvidence.compareDocumentPosition(evidenceNext) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).not.toBe(0);
      expect(evidenceNext.compareDocumentPosition(askInput) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
        0,
      );
      await waitFor(() => expect(document.getElementById("post-ask")).toHaveFocus());
    } finally {
      HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
    }
  });

  it("does not tell a failed period report to connect the measurement service", async () => {
    stubBackend({ failedReportRun: true });
    render(<App showLabPanels />);

    const reportButton = await screen.findByRole("button", {
      name: "Open analysis run: Period report · Failed · Demo Corp",
    });
    expect(reportButton).toHaveTextContent(
      "Open this run to see why it failed, then rebuild the period report from a current snapshot.",
    );
    expect(reportButton).not.toHaveTextContent("measurement service");
    expect(reportButton).not.toHaveTextContent("reconstruction");

    await userEvent.click(reportButton);
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Open period report 2026-W02" }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText(
        "No posts were available at this cutoff for the period report. Open a later run or retry after a newer snapshot is available.",
      ),
    ).toBeInTheDocument();
  });

  it("does not tell a pending TEPP run that it already measured", async () => {
    stubBackend({ pendingTeppRun: true });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: TEPP measurement · Pending · Demo Corp",
      }),
    );
    expect(
      await screen.findByText("These posts are the cutoff corpus TEPP will measure once this run finishes."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/replace Failed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/this TEPP run measured/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Reconstruction has not started yet/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start TEPP measurement" })).toBeInTheDocument();
  });

  it("starts a pending TEPP run through tepp_client and does not invent a theta", async () => {
    const fetchMock = stubBackend({ pendingTeppRun: true });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: TEPP measurement · Pending · Demo Corp",
      }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Start TEPP measurement" }));
    expect(
      await screen.findByRole("heading", { name: "TEPP measurement · Failed · Demo Corp" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/tepp_not_available/)).toBeInTheDocument();
    expect(screen.queryByText(/theta/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    const startCall = fetchMock.mock.calls.find((call) =>
      String(call[0]).endsWith("/api/analysis-runs/run-demo-tepp/start"),
    );
    expect(startCall?.[1]?.method).toBe("POST");
  });

  it("does not invent a Pending TEPP row from a Failed TEPP run", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: TEPP measurement · Failed · Demo Corp",
      }),
    );
    expect(
      await screen.findByText(
        "Connect a TEPP transport from this Failed row. Request a lineage reconstruction does not invent a measurement.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request a new TEPP measurement" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "TEPP measurement · Pending · Demo Corp" })).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        (call) => String(call[0]).endsWith("/api/analysis-runs") && call[1]?.method === "POST",
      ),
    ).toBe(false);
  });

  it("does not tell a succeeded TEPP run to replace Failed", async () => {
    stubBackend({ succeededTeppRun: true });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: TEPP measurement · Succeeded · Demo Corp",
      }),
    );
    expect(
      await screen.findByText("These posts are the cutoff corpus this TEPP run measured."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Measurement request accepted")).toHaveTextContent(
      "Refresh this run to check whether results are ready.",
    );
    expect(screen.queryByText("tepp-remote-run-1")).not.toBeInTheDocument();
    expect(screen.queryByText(/replace Failed/i)).not.toBeInTheDocument();
  });

  it("records a pending lineage run and opens the authorized detail", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Request a lineage reconstruction" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Lineage reconstruction · Pending · Demo Corp" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open analysis run: Lineage reconstruction · Pending · Demo Corp",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Open this run, then start reconstruction. Reconstruction has not started yet.",
      ),
    ).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Start reconstruction" })).toBeInTheDocument();
    const postCall = fetchMock.mock.calls.find(
      (call) => String(call[0]).endsWith("/api/analysis-runs") && call[1]?.method === "POST",
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(String(postCall?.[1]?.body));
    expect(body.run_kind_code).toBe("analysis_run_lineage");
    expect(body.corporate_entity_id).toBe("corp-demo");
    expect(body.idempotency_key).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });

  it("lets a multi-affiliation operator choose which corp to reconstruct", async () => {
    const fetchMock = stubBackend({ pluralAffiliations: true });
    render(<App showLabPanels />);

    const picker = await screen.findByRole("combobox", {
      name: "Corporate entity to reconstruct",
    });
    await userEvent.selectOptions(picker, "corp-north");
    await userEvent.click(screen.getByRole("button", { name: "Request a lineage reconstruction" }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          (call) =>
            String(call[0]).endsWith("/api/analysis-runs") &&
            call[1]?.method === "POST" &&
            JSON.parse(String(call[1]?.body)).corporate_entity_id === "corp-north",
        ),
      ).toBe(true),
    );
  });

  it("does not record a lineage run before affiliated corps load", async () => {
    const fetchMock = stubBackend({ deferMe: true, pluralAffiliations: true });
    render(<App showLabPanels />);

    const loading = await screen.findByRole("button", { name: "Loading affiliated entities..." });
    expect(loading).toBeDisabled();
    await userEvent.click(loading);
    expect(
      fetchMock.mock.calls.some(
        (call) => String(call[0]).endsWith("/api/analysis-runs") && call[1]?.method === "POST",
      ),
    ).toBe(false);
    expect(screen.queryByRole("combobox", { name: "Corporate entity to reconstruct" })).toBeNull();

    fetchMock.releaseMe();
    const picker = await screen.findByRole("combobox", {
      name: "Corporate entity to reconstruct",
    });
    expect(picker).toBeInTheDocument();
    await userEvent.selectOptions(picker, "corp-demo");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Request a lineage reconstruction" })).toBeEnabled(),
    );
  });

  it("keeps Request disabled when affiliated corps fail to load", async () => {
    const fetchMock = stubBackend({ meFailed: true });
    render(<App showLabPanels />);

    expect(
      await screen.findByText("Reload to load the corporate entities this account may reconstruct."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload to choose a corporate entity" })).toBeDisabled();
    expect(
      fetchMock.mock.calls.some(
        (call) => String(call[0]).endsWith("/api/analysis-runs") && call[1]?.method === "POST",
      ),
    ).toBe(false);
  });

  it("starts reconstruction and shows the designed A-100 fork", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Request a lineage reconstruction" }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Start reconstruction" }));
    expect(
      await screen.findByRole("heading", { name: "Lineage reconstruction · Succeeded · Demo Corp" }),
    ).toBeInTheDocument();
    const fork = screen.getByRole("list", { name: "Reconstructed lineage edges" });
    expect(fork).toHaveTextContent(
      "Pricing renegotiation: revised quote sent follows Pricing renegotiation follow-up",
    );
    expect(fork).toHaveTextContent(
      "Delivery schedule question raised follows Pricing renegotiation follow-up",
    );
    const digests = screen.getByLabelText("Analysis run reproducibility digests");
    expect(digests).toHaveTextContent("Result aaaaaaaaaaaa");
    expect(screen.getByTitle("aa".repeat(32))).toHaveTextContent("Result aaaaaaaaaaaa");
    const startCall = fetchMock.mock.calls.find((call) =>
      String(call[0]).endsWith("/api/analysis-runs/run-demo-lineage-pending/start"),
    );
    expect(startCall?.[1]?.method).toBe("POST");

    await userEvent.click(
      screen.getByRole("button", {
        name: "Open reconstructed child: Pricing renegotiation: revised quote sent",
      }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByRole("status", { name: "Live body warning" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(
      screen.getAllByRole("button", {
        name: "Open reconstructed parent: Pricing renegotiation follow-up",
      })[0],
    );
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("status", { name: "Live body warning" })).not.toBeInTheDocument();
  });

  it("shows the calibrated period-report mean theta on the home page", async () => {
    stubBackend();
    render(<App showLabPanels />);

    expect((await screen.findAllByText(/mean θ 0.42/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/8 posts/).length).toBeGreaterThan(0);
    expect(screen.getByText(/TEST-PU-REPORT/)).toBeInTheDocument();
    expect(screen.getAllByText("shared metric").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/CAT: sales-lead I=0\.70/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/leftover axis 1 σ 1\.84 82%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/leftover axis 2 σ 0\.86 18%/).length).toBeGreaterThan(0);
    expect(screen.queryByText("leftover axis 1 σ 1.84")).not.toBeInTheDocument();
    expect(screen.queryByText("leftover axis 2 σ 0.86")).not.toBeInTheDocument();
    expect(screen.getByText("leftover map comparison leftover axis 1 σ 1.84 82%")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison leftover axis 2 σ 0.86 18%")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison leftover axis 1 tick +0.50 σ 1.84")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison leftover axis 2 tick −0.02 σ 0.86")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison leftover axis 1 tick 0.00 σ 1.84")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison leftover axis 2 tick 0.00 σ 0.86")).toBeInTheDocument();
    expect(screen.queryByText("leftover axis 1 tick +0.50 σ 1.84")).not.toBeInTheDocument();
    expect(screen.queryByText("leftover-map axis 1 tick +0.50 σ 1.84")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison leftover axis")).toHaveTextContent(
      "Open a leftover pair to read the post–criterion cell",
    );
    expect(screen.getByLabelText("Leftover-map axis share")).toHaveTextContent(
      "Open a leftover pair to read the post–criterion cell",
    );
    expect(screen.getByRole("button", { name: /open report period 2026-W03/i })).toHaveTextContent(
      "vs 2026-W02: +0.92",
    );
    expect(screen.queryByRole("button", { name: /rebuild report/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open report post: public post/i })).toHaveTextContent("θ 0.91");
    expect(screen.getByRole("button", { name: /open report post: public post/i })).toHaveTextContent(
      "Send Northridge Grid the revised quote",
    );
    expect(screen.getByRole("button", { name: /open report post: public post/i })).toHaveTextContent("Open");
    expect(screen.getByRole("button", { name: /open report post: public post/i })).toHaveTextContent("due 2026-01-12");
    expect(await screen.findByLabelText("Leftover pairs")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover-map graphic display")).toBeInTheDocument();
    expect(screen.getByLabelText("Leftover map comparison graphic")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 1 σ 1.84 (82%)")).toBeInTheDocument();
    expect(screen.getByText("leftover-map axis 2 σ 0.86 (18%)")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison graphic leftover-map axis 1 σ 1.84 (82%)")).toBeInTheDocument();
    expect(screen.getByText("leftover map comparison graphic leftover-map axis 2 σ 0.86 (18%)")).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", {
        name: /open leftover-map post public post at ξ \(\+0\.50, \+0\.10\)/i,
      }),
    ).toHaveLength(2);
    expect(screen.getByLabelText("Leftover map coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover map incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
    expect(screen.getByLabelText("Leftover-map graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic coverage")).toHaveTextContent(
      "Leftover map used 2 of 3 scored posts (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover map comparison graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
    expect(screen.getByLabelText("Leftover-map graphic item coverage")).toHaveTextContent(
      "Leftover map used 2 of 2 scored criteria (complete-case)",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete posts")).toHaveTextContent(
      "Leftover map dropped 1 incomplete posts",
    );
    expect(screen.getByLabelText("Leftover-map graphic incomplete items")).toHaveTextContent(
      "Leftover map dropped 0 incomplete criteria",
    );
    const coverageCaption = screen.getByLabelText("Leftover map coverage");
    const closestPair = screen.getByRole("button", { name: /open leftover closest pair: public post/i });
    const farthestPair = screen.getByRole("button", {
      name: /open leftover farthest pair: specification revision requested/i,
    });
    expect(closestPair).toHaveTextContent("Closest leftover: Public post · sales-lead");
    // Leftover-map coordinates are present, so they name the next action
    // instead of leftover-map explained leftover share (ADR 0267).
    expect(closestPair).toHaveTextContent(
      "Leftover map places this post at ξ (+0.50, +0.10) and the criterion at ζ (+0.50, −0.02) after IRT main effects. Open this post to read sales-lead.",
    );
    expect(closestPair).toHaveTextContent("R +0.40");
    expect(closestPair).toHaveTextContent("Y 2.40 · E 2.00");
    expect(closestPair).toHaveTextContent("rank 1");
    expect(closestPair).toHaveTextContent("U +0.05");
    expect(closestPair).toHaveTextContent("U²/R² 0.02");
    expect(closestPair).toHaveTextContent("R̂²/R² 0.76");
    expect(closestPair).toHaveTextContent("2R̂U/R² 0.12");
    expect(closestPair).toHaveTextContent("R̂ +0.25");
    expect(closestPair).toHaveTextContent("ξ (+0.50, +0.10) ζ (+0.50, −0.02)");
    expect(closestPair).toHaveTextContent("d 0.12");
    expect(closestPair).toHaveAccessibleName("Open leftover closest pair: Public post · sales-lead");
    expect(farthestPair).toHaveTextContent("Farthest leftover: Specification revision requested · negative");
    expect(farthestPair).toHaveTextContent(
      "Leftover map places this post at ξ (+0.90, +0.80) and the criterion at ζ (−0.70, −0.40) after IRT main effects. Open this post to read negative.",
    );
    expect(farthestPair).toHaveTextContent("R −1.10");
    expect(farthestPair).toHaveTextContent("Y 0.90 · E 2.00");
    expect(farthestPair).toHaveTextContent("rank 1");
    expect(farthestPair).toHaveTextContent("U −0.25");
    expect(farthestPair).toHaveTextContent("U²/R² 0.05");
    expect(farthestPair).toHaveTextContent("R̂²/R² 0.60");
    expect(farthestPair).toHaveTextContent("2R̂U/R² -0.24");
    expect(farthestPair).toHaveTextContent("R̂ −0.95");
    expect(farthestPair).toHaveTextContent("ξ (+0.90, +0.80) ζ (−0.70, −0.40)");
    expect(farthestPair).toHaveTextContent("d 2.00");
    expect(0.5 * 0.5 + 0.1 * -0.02).toBeCloseTo(0.248);
    expect(Math.hypot(0.5 - 0.5, 0.1 - -0.02)).toBeCloseTo(0.12);
    expect(0.9 * -0.7 + 0.8 * -0.4).toBeCloseTo(-0.95);
    expect(Math.hypot(0.9 - -0.7, 0.8 - -0.4)).toBeCloseTo(2.0);
    const memberButton = screen.getByRole("button", { name: /open report post: public post/i });
    expect(coverageCaption.compareDocumentPosition(closestPair) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(closestPair.compareDocumentPosition(memberButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /open report post: specification revision requested/i }),
    ).toHaveTextContent("Send Westfield Power the revised specification");
    expect(
      screen.getByRole("button", { name: /open report post: specification revision requested/i }),
    ).toHaveTextContent("Open");
    expect(
      screen.getByRole("button", { name: /open report post: specification revision requested/i }),
    ).toHaveTextContent("due 2026-01-14");
    expect(screen.getByRole("button", { name: /open commitment for: public post/i })).toHaveTextContent(
      "Send Northridge Grid the revised quote",
    );
    expect(screen.getByRole("button", { name: /open commitment for: public post/i })).toHaveTextContent(
      "due 2026-01-12",
    );
  });

  it("shows the grouping comparison strip and switches grouping on click", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    expect(await screen.findByLabelText("Grouping comparison")).toBeInTheDocument();
    expect(
      await within(screen.getByLabelText("Grouping comparison")).findByLabelText(
        "Leftover map comparison graphic",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison graphic",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic display",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison graphic leftover-map axis 1 σ 1.84 (82%)",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison graphic leftover-map axis 2 σ 0.86 (18%)",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText("leftover-map axis 1 σ 1.84 (82%)"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText("leftover-map axis 2 σ 0.86 (18%)"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText("leftover-map axis 1 (82%)"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText("leftover-map axis 2 (18%)"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 1 σ 1.84 82%",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 2 σ 0.86 18%",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 1 tick +0.50 σ 1.84",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 2 tick −0.02 σ 0.86",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 1 tick 0.00 σ 1.84",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 2 tick 0.00 σ 0.86",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText(
        "leftover axis 1 tick +0.50 σ 1.84",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText(
        /leftover map comparison leftover axis 1 tick \+0\.50 82%/,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText("leftover axis 1 σ 1.84 82%"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByText("leftover axis 2 σ 0.86 18%"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison leftover axis",
      ),
    ).toHaveTextContent("Open a leftover pair to read the post–criterion cell");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByRole("button", {
        name: "Open leftover-map post Public post at ξ (+0.50, +0.10)",
      }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText("Leftover map coverage"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison coverage",
      ),
    ).toHaveTextContent("Leftover map used 2 of 3 scored posts (complete-case)");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison coverage",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison graphic coverage",
      ),
    ).toHaveTextContent("Leftover map used 2 of 3 scored posts (complete-case)");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison graphic coverage",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic coverage",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison graphic item coverage",
      ),
    ).toHaveTextContent("Leftover map used 2 of 2 scored criteria (complete-case)");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison graphic item coverage",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic item coverage",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison graphic incomplete posts",
      ),
    ).toHaveTextContent("Leftover map dropped 1 incomplete posts");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison graphic incomplete posts",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic incomplete posts",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison graphic incomplete items",
      ),
    ).toHaveTextContent("Leftover map dropped 0 incomplete criteria");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison graphic incomplete items",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic incomplete items",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText("Leftover map item coverage"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison item coverage",
      ),
    ).toHaveLength(2);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison item coverage",
      )[0],
    ).toHaveTextContent("Leftover map used 2 of 2 scored criteria (complete-case)");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText("Leftover map incomplete posts"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete posts",
      ),
    ).toHaveLength(2);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete posts",
      )[0],
    ).toHaveTextContent("Leftover map dropped 0 incomplete posts");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete posts",
      )[1],
    ).toHaveTextContent("Leftover map dropped 1 incomplete posts");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic incomplete posts",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText("Leftover map incomplete items"),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete items",
      ),
    ).toHaveLength(2);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison incomplete items",
      )[0],
    ).toHaveTextContent("Leftover map dropped 0 incomplete criteria");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "Leftover-map graphic incomplete items",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic reconstruction R̂ +0.25",
      ),
    ).toHaveTextContent("R̂ +0.25");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        /leftover-map reconstruction/,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison reconstruction",
      ),
    ).toHaveTextContent("R̂ +0.25");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison reconstruction",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic explained leftover share R̂²/R² 0.76",
      ),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        /leftover-map explained leftover share/,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison explained leftover share",
      ),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison explained leftover share",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic unexplained leftover share U²/R² 0.02",
      ),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        /leftover-map unexplained leftover share/,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison unexplained leftover share",
      ),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison unexplained leftover share",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic cross share 2R̂U/R² 0.12",
      ),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        /leftover-map cross share/,
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison cross share",
      ),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison cross share",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic unexplained leftover U +0.05",
      ),
    ).toHaveTextContent("U +0.05");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover-map unexplained leftover U +0.05",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison unexplained leftover",
      ),
    ).toHaveTextContent("U +0.05");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison unexplained leftover",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic leftover residual R +0.40",
      ),
    ).toHaveTextContent("R +0.40");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover residual R +0.40",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison residual",
      ),
    ).toHaveLength(2);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison residual",
      )[0],
    ).toHaveTextContent("R −1.10");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison residual",
      )[1],
    ).toHaveTextContent("R +0.40");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic leftover observed Y 2.40",
      ),
    ).toHaveTextContent("Y 2.40");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover observed Y 2.40",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison observed",
      ),
    ).toHaveTextContent("Y 2.40");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison observed",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic leftover expected E 2.00",
      ),
    ).toHaveTextContent("E 2.00");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover expected E 2.00",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison expected",
      ),
    ).toHaveTextContent("E 2.00");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison expected",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic leftover-map rank rank 1",
      ),
    ).toHaveTextContent("rank 1");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover-map rank rank 1",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison rank",
      ),
    ).toHaveTextContent("rank 1");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison rank",
      ),
    ).toHaveLength(1);
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic leftover-map distance d 0.12",
      ),
    ).toHaveTextContent("d 0.12");
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover-map distance d 0.12",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "leftover map comparison graphic leftover-map axis 1 tick +0.50 σ 1.84",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover-map axis 1 tick +0.50",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByText(
        "leftover map comparison leftover axis 1 tick +0.50 σ 1.84",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).queryByLabelText(
        "leftover map comparison leftover axis 1 tick +0.50 σ 1.84",
      ),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Grouping comparison")).getByLabelText(
        "Leftover map comparison coordinates",
      ),
    ).toHaveTextContent("ξ (+0.50, +0.10) ζ (+0.50, −0.02)");
    expect(
      within(screen.getByLabelText("Grouping comparison")).getAllByLabelText(
        "Leftover map comparison coordinates",
      ),
    ).toHaveLength(1);
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).toHaveTextContent("d 2.00");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("R̂");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("R̂²/R²");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("U²/R²");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("2R̂U/R²");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("U +");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).toHaveTextContent("R −1.10");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("Y ");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("E ");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("rank ");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: specification revision requested/i,
      }),
    ).not.toHaveTextContent("ξ");
    expect(
      screen.getByRole("button", { name: "Compare Business unit (PU): Demo Report High, mean θ 0.81" }),
    ).toHaveTextContent("mean θ 0.81");
    await userEvent.click(
      screen.getByRole("button", { name: "Compare Thread group: A-100, mean θ 0.81" }),
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "A-100 is the opened grouping. Read its mean θ and member posts below, then open a post.",
    );
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("Closest leftover: Public post · sales-lead");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("d 0.12");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("R̂ +0.25");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("R̂²/R² 0.76");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("U²/R² 0.02");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("2R̂U/R² 0.12");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("U +0.05");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("R +0.40");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("Y 2.40");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("E 2.00");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("rank 1");
    expect(
      screen.getByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    ).toHaveTextContent("ξ (+0.50, +0.10) ζ (+0.50, −0.02)");
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/reports/thread_group/2026-W02"),
        expect.anything(),
      ),
    );
  });

  it("selects a linked week from the FIPC trend strip", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: /open report period 2026-W03/i }));
    const periodInput = screen.getByLabelText("Report period");
    expect(periodInput).toHaveValue("2026-W03");
  });

  it("opens a leftover pair post from the comparison strip", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: /open leftover closest pair from comparison: public post/i,
      }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("opens a leftover pair post from the grouping comparison leftover-map graphic", async () => {
    stubBackend();
    render(<App showLabPanels />);

    const comparison = await screen.findByLabelText("Grouping comparison");
    await userEvent.click(
      await within(comparison).findByRole("button", {
        name: "Open leftover-map post Public post at ξ (+0.50, +0.10)",
      }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("opens a leftover pair post from the report panel", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: /open leftover closest pair: public post/i }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(await screen.findByRole("heading", { name: "Post quality (IRT)" })).toHaveFocus();
    expect(await screen.findByRole("status", { name: "Leftover criterion next action" })).toHaveTextContent(
      "sales-lead is the leftover criterion this post sat closest to after main effects. Read that Post quality score next.",
    );
    expect((await screen.findByText("Sales-lead specificity: 3")).closest("li")).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(screen.getByText("Constructive stance: 2").closest("li")).not.toHaveAttribute("aria-current");

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(
      await screen.findByRole("button", {
        name: /open leftover farthest pair: specification revision requested/i,
      }),
    );
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
    expect(await screen.findByRole("heading", { name: "Post quality (IRT)" })).toHaveFocus();
    expect(await screen.findByRole("status", { name: "Leftover criterion next action" })).toHaveTextContent(
      "negative is the leftover criterion this post sat farthest from after main effects. Read that Post quality score next.",
    );

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(await screen.findByRole("button", { name: /open report post: public post/i }));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.queryByRole("status", { name: "Leftover criterion next action" })).not.toBeInTheDocument();
    expect((await screen.findByText("Sales-lead specificity: 3")).closest("li")).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("opens Event Lineage, Keyman, and evaluation from a report member click", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: /open report post: public post/i }));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByText("Constructive stance: 2")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Leftover criterion next action" })).not.toBeInTheDocument();
    expect(screen.getAllByText(/Ada West/).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("A-100 lineage")).toHaveLength(1);
    expect(screen.getByRole("status", { name: "Event Lineage next action" })).toHaveTextContent(
      "Public post is current in Event Lineage. Read Keyman and evaluation next.",
    );
    expect(await screen.findByRole("status", { name: "Keyman next action" })).toHaveTextContent(
      "Ada West is the first Keyman. Read that person next.",
    );
    expect(await screen.findByRole("heading", { name: "Related to Ada West" })).toBeInTheDocument();
    expect(await screen.findByRole("status", { name: "Related next action" })).toHaveTextContent(
      "Priya Nair is the first related node. Read that person next.",
    );
    expect(await screen.findByRole("heading", { name: "Related to Priya Nair" })).toBeInTheDocument();
    expect(await screen.findByRole("status", { name: "Ask next action" })).toHaveTextContent(
      "Related nodes for Priya Nair are current. Ask about this lineage next.",
    );
    const popup = document.querySelector(".popup-panel");
    expect(popup).not.toBeNull();
    const ask = within(popup as HTMLElement).getByRole("heading", { name: "Ask about this lineage" });
    const affiliate = within(popup as HTMLElement).getByRole("heading", { name: "Affiliate tree" });
    const askNext = screen.getByRole("status", { name: "Ask next action" });
    expect(askNext.compareDocumentPosition(ask) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(ask.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    const askSeed = await screen.findByRole("status", { name: "Ask seed next action" });
    expect(askSeed).toHaveTextContent(
      "What happened between these events? is the first Ask. Read that answer next.",
    );
    const firstAskAnswer = within(popup as HTMLElement).getByText(
      "The seeded follow-up after the site visit.",
    );
    expect(
      askSeed.compareDocumentPosition(firstAskAnswer) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).not.toBe(0);
    expect(firstAskAnswer.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
      0,
    );
    const citedNext = await screen.findByRole("status", { name: "Ask citation next action" });
    expect(citedNext).toHaveTextContent(
      "Linked post is the first cited source. Open that evidence next.",
    );
    const citedEvidence = await screen.findByRole("complementary", { name: "Evidence" });
    expect(
      await within(citedEvidence).findByText("The evidence panel should show exactly this text."),
    ).toBeInTheDocument();
    expect(
      citedNext.compareDocumentPosition(citedEvidence) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).not.toBe(0);
    expect(
      citedEvidence.compareDocumentPosition(affiliate) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).not.toBe(0);
    expect(await screen.findByRole("status", { name: "Evidence next action" })).toHaveTextContent(
      "Linked post evidence is current. Read Event Lineage on that post next.",
    );
    await waitFor(() => expect(document.getElementById("post-ask")).toHaveFocus());
  });

  it("lets post_admin rebuild the period report", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: /rebuild report/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/reports/process_unit/2026-W02/rebuild"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("keeps advanced review tools out of the analyst board", async () => {
    stubBackend();
    render(<App />);

    const nav = await screen.findByRole("navigation", { name: "Workspace navigation" });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "게시판" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Dashboard",
      "게시판",
      "고객 마스터",
      "달력",
      "Ask Agent",
    ]);
    expect(nav.textContent).not.toMatch(/Buyer|Cubee|\bBoard\b|Customer master/i);
    expect(within(nav).queryByRole("button", { name: /Admin|관리자/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Advanced review tools")).not.toBeInTheDocument();
  });

  it("fails closed on the calendar destination when Naruon consume is unwired", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "달력" }));
    expect(screen.getByRole("heading", { name: "달력" })).toBeInTheDocument();
    expect(screen.getByText("이 범위의 일정을 아직 받을 수 없습니다")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /^Unavailable:/ }),
    ).toHaveTextContent("이 범위의 일정을 아직 받을 수 없습니다");
    expect(screen.getByRole("heading", { name: "Observed calendar events" })).toBeInTheDocument();
    expect(screen.queryByText(/CalDAV/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Buyer|Cubee/i)).not.toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /open commitment for: public post/i }),
    );
    expect(await screen.findByRole("button", { name: "게시판" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
