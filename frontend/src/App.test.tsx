import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { setLocale } from "./i18n";

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
  // Post navigation now pushes real history entries (browser back should
  // close the popup); reset between tests so one test's opened post doesn't
  // leak into the next test's initial render via a stale `?post=` query.
  window.history.replaceState({}, "", "/");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App, unauthenticated", () => {
  it("shows the authentication loading state", () => {
    mockAuth = { ...mockAuth, isLoading: true };

    render(<App />);

    expect(screen.getByText("Loading authentication state...")).toBeInTheDocument();
  });

  it("shows a login button that starts the real OIDC redirect", async () => {
    render(<App showLabPanels />);
    const button = screen.getByRole("button", { name: /log in/i });
    await userEvent.click(button);
    expect(signinRedirect).toHaveBeenCalledTimes(1);
    expect(signinRedirect).toHaveBeenCalledWith(
      expect.objectContaining({
        state: expect.objectContaining({ returnUrl: expect.stringMatching(/^\//) }),
      }),
    );
    expect(window.sessionStorage.getItem("lineageweave.oidc.returnUrl")).toMatch(/^\//);
  });

  it("does not render raw OIDC error text and names a log-in next action", async () => {
    mockAuth = {
      ...mockAuth,
      error: { message: "invalid_grant: AADSTS70000 TypeError at oidc-client" },
    };
    render(<App showLabPanels />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Sign-in could not be completed.");
    expect(alert).toHaveTextContent("Log in again to open the workspace.");
    expect(screen.queryByText(/invalid_grant|AADSTS70000|TypeError|oidc-client/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(signinRedirect).toHaveBeenCalledTimes(1);
  });

  it("offers a new login when authentication returns no access token", async () => {
    mockAuth = {
      ...mockAuth,
      isAuthenticated: true,
      user: { profile: { preferred_username: "demo.analyst" } },
    };

    render(<App />);

    expect(screen.getByRole("alert")).toHaveTextContent("Authenticated, but no access token was returned.");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(signinRedirect).toHaveBeenCalledWith(
      expect.objectContaining({ state: expect.objectContaining({ returnUrl: "/" }) }),
    );
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
    calendarEvents?: unknown[];
    calendarUnavailable?: boolean;
    caldavAvailable?: boolean;
    reportsUnavailable?: boolean;
    reportRebuildUnavailable?: boolean;
    rankings?: {
      status?: "accepted" | "unavailable";
      status_reason?: string | null;
      rankings?: {
        post_id: string;
        post_title: string;
        fused_rank: number;
      }[];
    };
    rankingsUnavailable?: boolean;
    relatedUnavailable?: "all" | "entity" | "person" | "team";
    chatUnavailable?: boolean;
    chatNoCitations?: boolean;
    evidenceUnavailable?: boolean;
    legacyChatCitations?: boolean;
    postChatConversationUnavailable?: boolean;
    postChatHistoryUnavailable?: boolean;
    preferenceUnavailable?: boolean;
    searchUnavailable?: boolean;
    askUnavailable?: boolean;
    askConversationFailsAfterFirst?: boolean;
    askConversationId?: boolean;
    askHistory?: boolean;
    askHistoryMoreUnavailable?: boolean;
    askHistoryPages?: boolean;
    askHistoryUnavailable?: boolean;
    askOlderTurnsUnavailable?: boolean;
    postAskHistory?: boolean;
    verificationEvidenceUrl?: string | null;
    failedLineageRun?: boolean;
    analysisRunCreateStatus?: 409 | 500;
    analysisRunOpenStatus?: 404 | 500;
    analysisRunsUnavailable?: boolean;
    analysisRunStartUnavailable?: boolean;
    runningLineageRun?: boolean;
    failedReportRun?: boolean;
    succeededReportRun?: boolean;
    succeededTeppRun?: boolean;
    pendingTeppRun?: boolean;
    pluralAffiliations?: boolean;
    manyAffiliations?: boolean;
    noAffiliations?: boolean;
    postUnavailable?: boolean;
    contentUnavailable?: boolean;
    derivedUnavailable?: boolean;
    bookmarkLoadUnavailable?: boolean;
    postsUnavailable?: boolean;
    rebuildUnavailable?: boolean;
    focusedLineageUnavailable?: boolean;
    deferMe?: boolean;
    deferPosts?: boolean;
    directLineage?: boolean;
    deriveNoCommitment?: boolean;
    emptyLineage?: boolean;
    meFailed?: boolean;
    postBody?: string;
    boardTotalCount?: number;
    manyBoardPosts?: boolean;
    vocTypeOptions?: { code: string; label: string }[];
    visibilityOptions?: { code: string; label: string }[];
    sourceDetailStateCode?: string;
    sourceDetailStateOptions?: { code: string; label: string }[];
    manyCustomerHints?: number;
    customerEntityHierarchy?: boolean;
    emptyCustomerMaster?: boolean;
    customerMasterUnavailable?: boolean;
    customerResolveUnavailable?: boolean;
    customerScopeFacets?: boolean;
    customerRelatedPost?: boolean;
    rrOrgWithMembers?: boolean;
    groupedKeyEvents?: boolean;
    semanticRelationships?: boolean;
    staleSummary?: boolean;
    contentAfterSummary?: boolean;
    contentProcessing?: boolean;
    summaryPending?: boolean;
    summaryUnavailable?: boolean;
    activityUnavailable?: boolean;
    ticketCreateUnavailable?: boolean;
    ticketListUnavailable?: boolean;
    ticketUpdateUnavailable?: boolean;
    lineageIsolationReason?: "no_relation_found" | "no_comparison_group";
    bookmarkUnavailable?: boolean;
  }): ReturnType<typeof vi.fn> & { releaseMe: () => void; releasePosts: () => void } {
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
    let askConversationRequests = 0;
    let bookmarked = false;
    const authorizedAffiliations = options?.noAffiliations
      ? []
      : options?.manyAffiliations
      ? [
          {
            corporate_entity_id: "corp-demo",
            corporate_entity_code: "DEMO-CORP",
            entity_name: "Demo Corp",
            process_unit_id: "pu-demo",
            process_unit_code: "DEMO-PU",
            process_unit_name: "Demo PU",
          },
          {
            corporate_entity_id: "corp-north",
            corporate_entity_code: "NORTH-CORP",
            entity_name: "North Corp",
            process_unit_id: "pu-north",
            process_unit_code: "NORTH-PU",
            process_unit_name: "North PU",
          },
          {
            corporate_entity_id: "corp-south",
            corporate_entity_code: "SOUTH-CORP",
            entity_name: "South Corp",
            process_unit_id: "pu-south",
            process_unit_code: "SOUTH-PU",
            process_unit_name: "South PU",
          },
          {
            corporate_entity_id: "corp-west",
            corporate_entity_code: "WEST-CORP",
            entity_name: "West Corp",
            process_unit_id: "pu-west",
            process_unit_code: "WEST-PU",
            process_unit_name: "West PU",
          },
          {
            corporate_entity_id: "corp-hq",
            corporate_entity_code: "HQ-CORP",
            entity_name: "HQ Corp",
            process_unit_id: null,
            process_unit_code: null,
            process_unit_name: null,
          },
        ]
      : [
          {
            corporate_entity_id: "corp-demo",
            corporate_entity_code: "DEMO-CORP",
            entity_name: "Demo Corp",
            process_unit_id: "pu-demo",
            process_unit_code: "DEMO-PU",
            process_unit_name: "Demo PU",
          },
        ];

    let releaseMe = () => {};
    let releasePosts = () => {};
    const meReady = options?.deferMe
      ? new Promise<void>((resolve) => {
          releaseMe = resolve;
        })
      : Promise.resolve();
    const postsReady = options?.deferPosts
      ? new Promise<void>((resolve) => {
          releasePosts = resolve;
        })
      : Promise.resolve();

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/settings")) {
        return Promise.resolve(jsonResponse({ brandName: "LineageWeave" }));
      }
      if (url.endsWith("/api/me/preferences") && method === "PATCH") {
        if (options?.preferenceUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
            account_affiliations: authorizedAffiliations,
          });
        });
      }
      if (url.endsWith("/api/posts/post-1/bookmark")) {
        if (method === "GET" && options?.bookmarkLoadUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        if (method === "POST") {
          if (options?.bookmarkUnavailable) {
            return Promise.resolve(
              new Response(JSON.stringify({ detail: "bookmark unavailable" }), {
                status: 503,
                headers: { "Content-Type": "application/json" },
              }),
            );
          }
          bookmarked = Boolean(JSON.parse(String(init?.body)).bookmarked);
        }
        return Promise.resolve(jsonResponse({ post_id: "post-1", bookmarked }));
      }
      if (url.endsWith("/api/lineage/rebuild") && method === "POST") {
        if (options?.rebuildUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
        return Promise.resolve(jsonResponse({ edge_count: 4 }));
      }
      if (url.endsWith("/api/posts/post-1/tickets") && method === "GET") {
        if (options?.ticketListUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(jsonResponse({ tickets }));
      }
      if (url.endsWith("/api/posts/post-1/tickets") && method === "POST") {
        if (options?.ticketCreateUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
        if (options?.ticketUpdateUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
        if (options?.activityUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
        if (options?.deriveNoCommitment) {
          return Promise.resolve(jsonResponse({ post_id: "post-1", has_commitment: false, ticket: null }));
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
        if (options?.analysisRunOpenStatus) {
          return Promise.resolve(new Response(null, { status: options.analysisRunOpenStatus }));
        }
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
        if (options?.analysisRunStartUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
        if (options?.analysisRunCreateStatus) {
          return Promise.resolve(new Response(null, { status: options.analysisRunCreateStatus }));
        }
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
        if (options?.analysisRunsUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
        if (options?.calendarUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            events: options?.calendarEvents ?? [],
            calendar_sources: { caldav_available: options?.caldavAvailable ?? false },
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
          }),
        );
      }
      if (url.endsWith("/api/rankings")) {
        if (options?.rankingsUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
      if (options?.reportsUnavailable && url.includes("/api/reports/") && method === "GET") {
        return Promise.resolve(new Response(null, { status: 503 }));
      }
      if (options?.reportRebuildUnavailable && url.includes("/api/reports/") && method === "POST") {
        return Promise.resolve(new Response(null, { status: 503 }));
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
                    observed_response: 2.4,
                    expected_response: 2.0,
                  },
                  {
                    pair_kind: "farthest",
                    post_id: "post-2",
                    post_title: "Specification revision requested",
                    criterion_code: "general_sentiment_negative",
                    leftover_distance: 1.84,
                    leftover_residual: -1.1,
                    observed_response: 0.9,
                    expected_response: 2.0,
                  },
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
        if (options?.focusedLineageUnavailable && url.includes("post_id=")) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        if ((options?.lineageIsolationReason || options?.emptyLineage) && url.includes("post_id=")) {
          return Promise.resolve(
            jsonResponse({
              nodes: [],
              edges: [],
              truncated: false,
              ...(options.lineageIsolationReason
                ? { isolation_reason: options.lineageIsolationReason }
                : {}),
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
        if (options?.postsUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
        return postsReady.then(() =>
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
                      source_detail_state_code: options?.sourceDetailStateCode,
                      visibility_code: "public",
                      visibility_label: "Public",
                      source_lineage_hints: {
                        combination_code: "1000",
                        commercial_context_code: "customer_only_candidate",
                        inference_status_code: "inferred_from_field_presence",
                        present_fields: ["customer"],
                        missing_fields: ["order_pool", "sales_order", "sales_order_item"],
                        lifecycle_vector: "Z-A-I-ALIVE",
                        deleted_marker_present: false,
                      },
                      created_at: "2026-01-01T00:00:00Z",
                    },
                    ...(options?.manyBoardPosts
                      ? [
                          {
                            post_id: "post-2",
                            post_title: "Earlier partner post",
                            voc_type_code: "vop",
                            voc_type_label: "Voice of Partner",
                            source_detail_state_code: "A",
                            visibility_code: "private",
                            visibility_label: "Private",
                            created_at: "2025-12-31T00:00:00Z",
                          },
                        ]
                      : []),
                  ],
                  total_count: options?.boardTotalCount ?? (options?.manyBoardPosts ? 2 : 1),
                  limit: 50,
                  offset: 0,
                  voc_type_options: [
                    ...(options?.vocTypeOptions ?? [
                      { code: "voc", label: "Voice of Customer" },
                      { code: "vop", label: "Voice of Partner" },
                    ]),
                  ],
                  source_detail_state_options: options?.sourceDetailStateOptions ?? [],
                  visibility_options: options?.visibilityOptions ?? [{ code: "public", label: "Public" }],
                },
          ),
        );
      }
      const postOneUrl = new URL(url, "https://backend.test");
      if (postOneUrl.pathname === "/api/posts/post-1") {
        if (options?.postUnavailable) {
          return Promise.resolve(new Response(JSON.stringify({ detail: "synthetic backend detail" }), { status: 503 }));
        }
        const asOf = postOneUrl.searchParams.get("as_of");
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            post_title: "Public post",
            post_body: options?.postBody ?? "The full body text.",
            voc_type_code: "voc",
            voc_type_label: "Voice of Customer",
            source_detail_state_code: options?.sourceDetailStateCode,
            visibility_code: "public",
            visibility_label: "Public",
            source_lineage_hints: {
              combination_code: "1000",
              commercial_context_code: "customer_only_candidate",
              inference_status_code: "inferred_from_field_presence",
              present_fields: ["customer"],
              missing_fields: ["order_pool", "sales_order", "sales_order_item"],
              lifecycle_vector: "Z-A-I-ALIVE",
              deleted_marker_present: false,
            },
            project_evidence: [
              {
                project_key: "source-project",
                project_name: "Semantic project",
                evidence: "project was described in the body",
                confidence: 0.9,
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Project",
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
        if (options?.contentUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        contentRequests += 1;
        return Promise.resolve(
          jsonResponse({
            status: options?.contentProcessing && contentRequests === 1 ? "processing" : "ready",
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
        if (options?.derivedUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
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
        if (options?.summaryPending) return new Promise<Response>(() => undefined);
        if (options?.summaryUnavailable) {
          return Promise.resolve(
            new Response(JSON.stringify({ detail: "summary unavailable" }), {
              status: 503,
              headers: { "Content-Type": "application/json" },
            }),
          );
        }
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            korean_summary: "이것은 요약입니다.",
            ...(options?.staleSummary
              ? { summary_status: "stale", summary_contract_version: 4 }
              : {}),
            key_events: ["첫 번째 이벤트"],
            ...(options?.groupedKeyEvents
              ? {
                  key_event_details: [
                    {
                      event_text: "1st milestone discussed",
                      project_name: "Case Facility Plan",
                      evidence_text: null,
                    },
                    {
                      event_text: "2nd milestone discussed",
                      project_name: "Case Facility Plan",
                      evidence_text: null,
                    },
                    {
                      event_text: "Unrelated standalone event",
                      project_name: null,
                      evidence_text: null,
                    },
                  ],
                }
              : {}),
            roles_and_responsibilities: options?.rrOrgWithMembers
              ? [
                  {
                    actor_name: "Case Institute",
                    responsibility: "연구 수행 기관",
                    actor_type_code: "prov_organization",
                    affiliated_organization_name: null,
                  },
                  {
                    actor_name: "Case Researcher One",
                    responsibility: "상담 고객 연구원",
                    actor_type_code: "prov_person",
                    affiliated_organization_name: "Case Institute",
                  },
                  {
                    actor_name: "Case Researcher Two",
                    responsibility: "상담 고객 연구원",
                    actor_type_code: "prov_person",
                    affiliated_organization_name: "Case Institute",
                  },
                ]
              : [
              {
                actor_name: "Ada West",
                responsibility: "우리 측 후속",
                actor_type_code: "prov_person",
                affiliated_organization_name: "Demo Corp",
                affiliated_organization_catalog_id: "corp-1",
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
                actor_name: "Northridge Grid Devices",
                responsibility: "부품 납품",
                actor_type_code: "prov_organization",
                affiliated_organization_name: "Northridge Grid",
                affiliation_catalog_unresolved_reason_code: "reason_no_live_client",
              },
              {
                actor_name: "당사",
                responsibility: "출하 일정 확정",
                actor_type_code: "prov_organization",
                affiliated_organization_name: null,
                catalog_unresolved_reason_code: "reason_not_corroborated",
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
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Project",
                extraction_method: "contextual_orchestrator_semantic",
              },
            ],
            ...(options?.semanticRelationships
              ? {
                  semantic_relationships: [
                    {
                      relation_ordinal: 0,
                      subject_name: "Design team",
                      subject_type: "prov:Agent",
                      predicate_code: "lw_responsible_for",
                      object_name: "Synthetic launch",
                      object_type: "lw:Project",
                      evidence_text: "The design team owns the synthetic launch.",
                      confidence: 0.91,
                      extraction_method: "contextual_orchestrator_semantic",
                    },
                    {
                      relation_ordinal: 1,
                      subject_name: "Prototype Alpha",
                      subject_type: "prov:Entity",
                      predicate_code: "lw_precedes",
                      ontology_label: "Precedes",
                      object_name: "Prototype Beta",
                      object_type: "prov:Entity",
                      evidence_text: "Alpha was completed before Beta.",
                      confidence: 0.84,
                      extraction_method: null,
                    },
                    {
                      relation_ordinal: 2,
                      subject_name: "Synthetic note",
                      subject_type: "prov:Entity",
                      predicate_code: "synthetic_relation",
                      object_name: "Synthetic record",
                      object_type: "prov:Entity",
                      evidence_text: "The source states this synthetic relation.",
                      confidence: 0.75,
                    },
                  ],
                }
              : {}),
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/keymen")) {
        if (options?.derivedUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
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
                affiliations: [{ organization_name: "Demo Corp", corporate_entity_id: "corp-1", role_title: null }],
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
        if (options?.relatedUnavailable === "all" || options?.relatedUnavailable === "person") {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Person",
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
        if (options?.relatedUnavailable === "all" || options?.relatedUnavailable === "person") {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
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
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Person",
                ontology_label: "Person",
                label: "Priya Nair",
                person_side_code: "counterparty",
                person_side_label: "Counterparty",
                relevance: 0.4,
              },
              {
                node_id: "post-2",
                node_type_code: "node_post",
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Post",
                ontology_label: "Post",
                label: "Linked post",
                relevance: 0.3,
              },
              {
                node_id: "corp-1",
                node_type_code: "node_corporate_entity",
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Organization",
                ontology_label: "Organization",
                label: "Demo Corp",
                relevance: 0.2,
              },
              {
                node_id: "team-1",
                node_type_code: "node_team",
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Team",
                ontology_label: "Team",
                label: "설계팀",
                relevance: 0.15,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/teams/team-1/related")) {
        if (options?.relatedUnavailable === "all" || options?.relatedUnavailable === "team") {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            team_id: "team-1",
            team_name: "설계팀",
            related: [
              {
                node_id: "post-2",
                node_type_code: "node_post",
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Post",
                ontology_label: "Post",
                label: "Linked post",
                relevance: 0.6,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/corporate-entities/corp-1/related")) {
        if (options?.relatedUnavailable === "all" || options?.relatedUnavailable === "entity") {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            corporate_entity_id: "corp-1",
            entity_name: "Demo Corp",
            related: [
              {
                node_id: "person-ada",
                node_type_code: "node_person",
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Person",
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
      if (url.endsWith("/api/corporate-entities/corp-demo/related") && options?.customerRelatedPost) {
        return Promise.resolve(
          jsonResponse({
            corporate_entity_id: "corp-demo",
            entity_name: "Demo Corp",
            related: [
              {
                node_id: "post-2",
                node_type_code: "node_post",
                ontology_iri: "https://contextualwisdomlab.github.io/lineageweave/ontology#Post",
                ontology_label: "Post",
                label: "Linked post",
                post_body_excerpt: "Linked body preview",
                post_body_truncated: true,
                relevance: 0.6,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/affiliate-tree")) {
        if (options?.derivedUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
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
        if (options?.derivedUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
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
        if (options?.derivedUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
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
        if (options?.derivedUnavailable) return Promise.resolve(new Response(null, { status: 503 }));
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            direct: options?.directLineage
              ? [{ post_id: "post-2", post_title: "Linked post" }]
              : [],
            indirect: options?.lineageIsolationReason || options?.emptyLineage || options?.directLineage
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
                ...(options?.legacyChatCitations
                  ? {}
                  : { cited_posts: [{ post_id: "post-2", post_title: "Linked post" }] }),
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
        let conversationId = "conversation-post-new";
        try {
          const body: unknown = JSON.parse(String(init?.body));
          if (
            body &&
            typeof body === "object" &&
            "conversation_id" in body &&
            typeof body.conversation_id === "string" &&
            body.conversation_id
          ) {
            conversationId = body.conversation_id;
          }
        } catch {
          conversationId = "conversation-post-new";
        }
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            conversation_id: conversationId,
            answer_text: "Here is what happened, drawing on the linked post.",
            cited_post_ids: options?.chatNoCitations ? [] : ["post-2"],
            ...(options?.legacyChatCitations || options?.chatNoCitations
              ? {}
              : { cited_posts: [{ post_id: "post-2", post_title: "Linked post" }] }),
            source_post_ids: ["post-1", "post-2"],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/chat/conversations") && method === "GET") {
        if (options?.postChatHistoryUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        if (options?.postAskHistory) {
          return Promise.resolve(
            jsonResponse({
              conversations: [
                {
                  conversation_id: "conversation-post-1",
                  title: "Saved post question",
                  updated_at: "2026-08-21T00:00:00Z",
                  turn_count: 1,
                },
              ],
            }),
          );
        }
        return Promise.resolve(jsonResponse({ conversations: [] }));
      }
      if (url.endsWith("/api/posts/post-1/chat/conversations/conversation-post-1") && method === "GET") {
        if (options?.postChatConversationUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            conversation_id: "conversation-post-1",
            title: "Saved post question",
            exchanges: [
              {
                turn_id: "turn-1",
                question_text: "Which site visit was saved?",
                answer_text: "The saved post answer stays grounded in the linked source.",
                cited_post_ids: ["post-2"],
                cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
                source_post_ids: ["post-1", "post-2"],
              },
            ],
          }),
        );
      }
      if (url.includes("/chat/conversations") && method === "GET") {
        return Promise.resolve(jsonResponse({ conversations: [] }));
      }
      if (url.endsWith("/api/ask/conversations") && method === "GET") {
        if (options?.askHistoryUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        if (options?.askHistory) {
          return Promise.resolve(
            jsonResponse({
              conversations: [
                {
                  conversation_id: "conversation-1",
                  title: "Saved project question",
                  updated_at: "2026-08-21T00:00:00Z",
                  turn_count: 1,
                },
              ],
              ...(options?.askHistoryPages
                ? {
                    next_cursor: {
                      updated_at: "2026-08-21T00:00:00Z",
                      conversation_id: "conversation-1",
                    },
                  }
                : {}),
            }),
          );
        }
        return Promise.resolve(jsonResponse({ conversations: [] }));
      }
      if (options?.askHistoryPages && url.includes("/api/ask/conversations?") && method === "GET") {
        if (options?.askHistoryMoreUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            conversations: [
              {
                conversation_id: "conversation-2",
                title: "Older saved question",
                updated_at: "2026-08-20T00:00:00Z",
                turn_count: 2,
              },
            ],
            next_cursor: null,
          }),
        );
      }
      if (options?.askHistoryPages && url.includes("/api/ask/conversations/conversation-1?") && method === "GET") {
        if (options?.askOlderTurnsUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            conversation_id: "conversation-1",
            title: "Saved project question",
            older_cursor: null,
            exchanges: [
              {
                turn_id: "turn-0",
                question_text: "Older saved turn",
                answer_text: "The older saved answer is still grounded in evidence.",
                cited_post_ids: [],
                cited_posts: [],
                cited_post_evidence: [],
                source_post_ids: [],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/ask/conversations/conversation-1") && method === "GET") {
        askConversationRequests += 1;
        if (options?.askConversationFailsAfterFirst && askConversationRequests > 1) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        return Promise.resolve(
          jsonResponse({
            conversation_id: "conversation-1",
            title: "Saved project question",
            ...(options?.askHistoryPages ? { older_cursor: "2" } : {}),
            exchanges: [
              {
                turn_id: "turn-1",
                question_text: "Which project was saved?",
                answer_text: "The saved answer is grounded in the linked source.",
                cited_post_ids: ["post-2"],
                cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
                cited_post_evidence: [],
                source_post_ids: ["post-1", "post-2"],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/ask") && method === "POST") {
        if (options?.askUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ detail: "Ask Agent is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY" }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return Promise.resolve(
          jsonResponse({
            ...(options?.askConversationId ? { conversation_id: "conversation-live" } : {}),
            answer_text: "The cited project is supported by the stored semantic evidence.",
            ...(options?.askConversationId ? { next_action: "Read the cited source next." } : {}),
            cited_post_ids: ["post-2"],
            cited_posts: [{ post_id: "post-2", post_title: "Linked post" }],
            cited_post_evidence: [
              {
                post_id: "post-2",
                facts: [
                  { kind: "semantic_project", text: "project: Semantic project | evidence: Body evidence" },
                  { kind: "semantic_keyman", text: "Keyman mention: Ada West | context: account lead" },
                  { kind: "semantic_event", text: "event: Quote revised | evidence: Customer request" },
                ],
              },
            ],
            source_post_ids: ["post-1", "post-2"],
          }),
        );
      }
      const customerMasterUrl = new URL(url, "https://backend.test");
      if (customerMasterUrl.pathname === "/api/customer-master" && method === "GET") {
        if (options?.customerMasterUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        const requestedCustomerHint = customerMasterUrl.searchParams.get("hint_code");
        return Promise.resolve(
          jsonResponse({
            corporate_entities: options?.emptyCustomerMaster
              ? []
              : options?.customerScopeFacets
              ? [
                  {
                    corporate_entity_id: "corp-own",
                    corporate_entity_code: "OWN-CORP-01",
                    entity_name: "Own Scope Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: null,
                    scope_facets: ["authorized_own"],
                  },
                  {
                    corporate_entity_id: "corp-granted",
                    corporate_entity_code: "GRANTED-CORP-01",
                    entity_name: "Granted Scope Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: null,
                    scope_facets: ["authorized_granted"],
                  },
                  {
                    corporate_entity_id: "corp-observed",
                    corporate_entity_code: "OBSERVED-CORP-01",
                    entity_name: "Observed Scope Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: null,
                    scope_facets: ["observed_organization"],
                  },
                  {
                    corporate_entity_id: "corp-observed-hierarchy",
                    corporate_entity_code: "OBSERVED-HIERARCHY-01",
                    entity_name: "Observed Hierarchy Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: null,
                    scope_facets: ["observed_hierarchy"],
                  },
                  {
                    corporate_entity_id: "corp-unclassified",
                    corporate_entity_code: "UNCLASSIFIED-CORP-01",
                    entity_name: "Unclassified Scope Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    parent_entity_id: null,
                    scope_facets: ["scope_unclassified"],
                  },
                ]
              : options?.customerEntityHierarchy
                ? [
                    {
                      corporate_entity_id: "corp-group",
                      corporate_entity_code: "DEMO-GROUP-01",
                      entity_name: "Demo Group",
                      entity_level_code: "group",
                      entity_level_label: "Group",
                      parent_entity_id: null,
                      scope_facets: ["authorized_own"],
                    },
                    {
                      corporate_entity_id: "corp-demo",
                      corporate_entity_code: "DEMO-CORP-01",
                      entity_name: "Demo Corp",
                      entity_level_code: "company",
                      entity_level_label: "Company",
                      parent_entity_id: "corp-group",
                      scope_facets: ["authorized_own"],
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
                      scope_facets: ["authorized_own"],
                      name_history: [
                        {
                          entity_name: "Demo Industries",
                          name_role_code: "entity_name_former",
                          observed_from: "2024-01-01T00:00:00Z",
                          observed_to: "2026-01-01T00:00:00Z",
                        },
                      ],
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
            source_customer_hints: options?.manyCustomerHints
              ? Array.from({ length: options.manyCustomerHints }, (_, index) => ({
                  source_system_code: "synthetic-crm",
                  customer_code: `CUST-${index}`,
                  customer_name: resolvedHintCode === `CUST-${index}` ? "Southfield Utilities" : null,
                  post_count: options.manyCustomerHints! - index,
                  related_posts: [],
                  resolution_status: resolvedHintCode === `CUST-${index}` ? "customer_identity_promoted" : "hint_only",
                  corporate_entity_id: resolvedHintCode === `CUST-${index}` ? "corp-southfield" : null,
                  resolved_entity_name: resolvedHintCode === `CUST-${index}` ? "Southfield Utilities" : null,
                  customer_identity_judgment_id: resolvedHintCode === `CUST-${index}` ? "judgment-southfield" : null,
                  hint_trust: "normal",
                  provenance: "source_post.source_customer_code",
                })).filter((hint) => !requestedCustomerHint || hint.customer_code === requestedCustomerHint)
              : [],
            source_author_hints: [],
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
        if (options?.customerResolveUnavailable) {
          return Promise.resolve(new Response(null, { status: 503 }));
        }
        const body = JSON.parse(String(init?.body));
        resolvedHintCode = body.hint_code;
        return Promise.resolve(
          jsonResponse({
            corporate_entity_id: "corp-southfield",
            entity_name: "Southfield Utilities",
            linked_post_count: 3,
            verification_evidence_url: "https://example.org/southfield",
            customer_identity_judgment_id: "judgment-southfield",
            resolution_status: "customer_identity_promoted",
            cached: false,
          }),
        );
      }
      if (url.includes("/source-research") && method === "GET") {
        const postId = new URL(url, "https://backend.test").pathname.split("/")[3] ?? "post-1";
        return Promise.resolve(jsonResponse({ post_id: postId, research: [] }));
      }
      if (url.includes("/source-research") && method === "POST") {
        const postId = new URL(url, "https://backend.test").pathname.split("/")[3] ?? "post-1";
        return Promise.resolve(jsonResponse({ post_id: postId, researched_count: 0 }));
      }
      return Promise.reject(new Error(`unexpected fetch: ${method} ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    return Object.assign(fetchMock, { releaseMe, releasePosts });
  }

  it("renders safe Ask Agent evidence under each cited post", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(screen.getByRole("log", { name: "Conversation" })).toBeInTheDocument();
    expect(screen.getByText("Which project?", { exact: true })).toBeInTheDocument();
    expect(await screen.findByRole("list", { name: "Evidence facts" })).toBeInTheDocument();
    expect(screen.getByText("Semantic project", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("Semantic event", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/project: Semantic project \| evidence: Body evidence/)).toBeInTheDocument();
    expect(screen.queryByText(/ontology_iri|contextual_orchestrator/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Linked post.*Open source/ }));
    expect(await screen.findByRole("dialog", { name: "Linked post" })).toBeInTheDocument();
  });

  it("adds a live Ask conversation and its next action to history", async () => {
    stubBackend({ askConversationId: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));

    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Which project?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Read the cited source next.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Which project\?/ })).toHaveAttribute("aria-current", "page");
  });

  it("renders the conversation empty state and submits an Ask Agent question with Enter", async () => {
    const fetchMock = stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));

    expect(screen.getByRole("log", { name: "Conversation" })).toHaveAttribute("aria-busy", "false");
    expect(screen.getByText("Start with a question about the evidence")).toBeInTheDocument();
    expect(screen.getByText("Evidence workspace")).toBeInTheDocument();
    expect(screen.getByText("Authorized evidence")).toBeInTheDocument();
    expect(screen.getByText("Switch between saved questions and source links.")).toBeInTheDocument();
    const input = screen.getByRole("textbox", { name: "Ask a question" });
    const send = screen.getByRole("button", { name: "Ask" });
    expect(send).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Who is involved?" }));
    expect(input).toHaveValue("Who is involved?");
    fireEvent.change(input, { target: { value: "작성 중" } });
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) => String(url).endsWith("/api/ask") && init?.method === "POST",
      ),
    ).toBe(false);
    fireEvent.change(input, { target: { value: "" } });
    await userEvent.type(input, "Which project?{Enter}");

    expect(await screen.findByText("Which project?", { selector: ".ask-agent-user-message p:last-child" })).toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("opens Ask from a post and can clear the starting evidence", async () => {
    const fetchMock = stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ask about this lineage" }));
    expect(screen.getByRole("status")).toHaveTextContent("Starting evidence: Public post");

    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "What preceded it?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      const askCall = fetchMock.mock.calls.find(
        ([input, init]) => String(input).endsWith("/api/ask") && init?.method === "POST",
      );
      expect(JSON.parse(String(askCall?.[1]?.body))).toMatchObject({ anchor_post_id: "post-1" });
    });

    await userEvent.click(screen.getByRole("button", { name: "Use all authorized evidence" }));
    expect(screen.queryByText(/Starting evidence:/)).not.toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "What else is related?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      const askCalls = fetchMock.mock.calls.filter(
        ([input, init]) => String(input).endsWith("/api/ask") && init?.method === "POST",
      );
      expect(askCalls).toHaveLength(2);
      expect(JSON.parse(String(askCalls[1][1]?.body))).not.toHaveProperty("anchor_post_id");
    });
  });

  it("fails closed when the selected source post is unavailable", async () => {
    stubBackend({ postUnavailable: true });
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const dialog = await screen.findByRole("dialog", { name: "Post details" });
    expect(await within(dialog).findByRole("alert")).toBeInTheDocument();
    expect(dialog).not.toHaveTextContent("synthetic backend detail");
    expect(within(dialog).queryByText("The full body text.")).not.toBeInTheDocument();
  });

  it("keeps the source readable when optional post evidence is unavailable", async () => {
    stubBackend({ contentUnavailable: true, derivedUnavailable: true, bookmarkLoadUnavailable: true });
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    expect(await within(dialog).findByText("The full body text.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Bookmark" })).toBeDisabled();
    expect(
      within(dialog).getByText("Related posts is temporarily unavailable. Saved evidence is still available."),
    ).toBeInTheDocument();
    expect(within(dialog).queryByText("Loading related posts...")).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Loading lineage...")).not.toBeInTheDocument();
  });

  it("shares, prints, and toggles a post bookmark from the popup actions", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const browserNavigator = Object.create(navigator);
    Object.defineProperty(browserNavigator, "clipboard", { value: { writeText } });
    vi.stubGlobal("navigator", browserNavigator);
    const print = vi.fn();
    vi.stubGlobal("print", print);
    const fetchMock = stubBackend();
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Share" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
    expect(new URL(String(writeText.mock.calls[0][0])).searchParams.get("post")).toBe("post-1");
    expect(within(dialog).getByText("Permanent link copied.", { selector: ".post-action-status" })).toBeVisible();

    fireEvent.click(within(dialog).getByRole("button", { name: "Print" }));
    expect(print).toHaveBeenCalledOnce();

    const bookmark = within(dialog).getByRole("button", { name: "Bookmark" });
    await waitFor(() => expect(bookmark).toBeEnabled());
    fireEvent.click(bookmark);
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Bookmarked" })).toBeEnabled());
    fireEvent.click(within(dialog).getByRole("button", { name: "Bookmarked" }));
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Bookmark" })).toBeEnabled());
    const bookmarkBodies = fetchMock.mock.calls
      .filter(([input, init]) => String(input).endsWith("/api/posts/post-1/bookmark") && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)).bookmarked);
    expect(bookmarkBodies).toEqual([true, false]);
  });

  it("uses the native share sheet when it is available", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    const browserNavigator = Object.create(navigator);
    Object.defineProperty(browserNavigator, "share", { value: share });
    vi.stubGlobal("navigator", browserNavigator);
    stubBackend();
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Share" }));

    await waitFor(() =>
      expect(share).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Public post", url: expect.stringContaining("post=post-1") }),
      ),
    );
    expect(dialog.querySelector(".post-action-status")).not.toBeInTheDocument();
  });

  it("keeps share cancellation quiet and reports share or bookmark failures", async () => {
    const share = vi
      .fn()
      .mockRejectedValueOnce(new DOMException("cancelled", "AbortError"))
      .mockRejectedValueOnce(new Error("share failed"));
    const browserNavigator = Object.create(navigator);
    Object.defineProperty(browserNavigator, "share", { value: share });
    Object.defineProperty(browserNavigator, "clipboard", { value: undefined });
    vi.stubGlobal("navigator", browserNavigator);
    stubBackend({ bookmarkUnavailable: true });
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Share" }));
    await waitFor(() => expect(share).toHaveBeenCalledOnce());
    expect(dialog.querySelector(".post-action-status")).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Share" }));
    expect(await within(dialog).findByText("Share unavailable.", { selector: ".post-action-status" })).toBeVisible();

    const bookmark = within(dialog).getByRole("button", { name: "Bookmark" });
    await waitFor(() => expect(bookmark).toBeEnabled());
    fireEvent.click(bookmark);
    await waitFor(() =>
      expect(within(dialog).getByText("Bookmark unavailable.", { selector: ".post-action-status" })).toBeVisible(),
    );
    expect(bookmark).toHaveAttribute("aria-pressed", "false");
  });

  it("explains when neither native share nor clipboard is available", async () => {
    const browserNavigator = Object.create(navigator);
    Object.defineProperty(browserNavigator, "share", { value: undefined });
    Object.defineProperty(browserNavigator, "clipboard", { value: undefined });
    vi.stubGlobal("navigator", browserNavigator);
    stubBackend();
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Share" }));

    expect(await within(dialog).findByText("Share unavailable.", { selector: ".post-action-status" })).toBeVisible();
  });

  it("clears a post anchor before continuing a saved conversation", async () => {
    const fetchMock = stubBackend({ askHistory: true });
    window.history.replaceState({}, "", "/?workspace=ask&post=post-1");
    render(<App />);

    expect(await screen.findByText("Starting evidence: post-1")).toBeInTheDocument();
    expect(screen.getByText("Start with a question about the evidence")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: /Saved project question/ }));
    expect(screen.queryByText(/Starting evidence:/)).not.toBeInTheDocument();

    await userEvent.type(screen.getByRole("textbox", { name: "Ask a question" }), "Continue saved context");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => {
      const askCall = fetchMock.mock.calls.find(
        ([input, init]) => String(input).endsWith("/api/ask") && init?.method === "POST",
      );
      expect(JSON.parse(String(askCall?.[1]?.body))).not.toHaveProperty("anchor_post_id");
    });
  }, 10_000);

  it("restores saved Ask Agent history and can start a new conversation", async () => {
    stubBackend({ askHistory: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));

    expect(await screen.findByText("Which project was saved?", { exact: true })).toBeInTheDocument();
    const savedConversation = screen.getByRole("button", { name: /Saved project question/ });
    expect(savedConversation).toHaveAttribute("aria-current", "page");
    expect(savedConversation).not.toHaveAttribute("aria-pressed");

    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(screen.getByText("Start with a question about the evidence")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Ask a question" })).toHaveFocus();
    await userEvent.click(savedConversation);
    expect(await screen.findByText("Which project was saved?", { exact: true })).toBeInTheDocument();
  });

  it("restores saved per-post Ask history and can start a new conversation", async () => {
    stubBackend({ postAskHistory: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument(),
    );
    const savedConversation = await screen.findByRole("button", { name: /Saved post question/ });
    expect(savedConversation).not.toHaveAttribute("aria-current");
    expect(savedConversation).not.toHaveAttribute("aria-pressed");

    const popup = document.querySelector(".popup-panel") as HTMLElement;
    const askInput = within(popup).getByPlaceholderText(/what happened/i);
    await userEvent.type(askInput, "What preceded the site visit?");
    await userEvent.click(within(popup).getByRole("button", { name: /^ask$/i }));
    expect(
      await screen.findByText("Here is what happened, drawing on the linked post."),
    ).toBeInTheDocument();
    const liveThread = screen.getByRole("button", { name: /What preceded the site visit/ });
    expect(liveThread).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("The seeded follow-up after the site visit.")).not.toBeInTheDocument();

    await userEvent.click(within(popup).getByRole("button", { name: "New conversation" }));
    expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument();
    expect(screen.queryByText("Here is what happened, drawing on the linked post.")).not.toBeInTheDocument();
    expect(
      [...popup.querySelectorAll(".chat-question")].map((node) => node.textContent),
    ).not.toContain("What preceded the site visit?");
    expect(liveThread).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: /What preceded the site visit/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Saved post question/ })).toBeInTheDocument();

    await userEvent.click(savedConversation);
    expect(
      await screen.findByText("The saved post answer stays grounded in the linked source."),
    ).toBeInTheDocument();
    expect(savedConversation).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("The seeded follow-up after the site visit.")).not.toBeInTheDocument();

    await userEvent.click(within(popup).getByRole("button", { name: "New conversation" }));
    expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument();
    expect(savedConversation).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: /Saved post question/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /What preceded the site visit/ })).toBeInTheDocument();
  });

  it("keeps the Ask Agent conversation visible when the orchestrator is unavailable", async () => {
    stubBackend({ askUnavailable: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));
    const input = screen.getByRole("textbox", { name: "Ask a question" });
    await userEvent.type(input, "Which project?{Enter}");

    expect(
      await screen.findByText("Ask Agent is temporarily unavailable. Saved evidence is still available."),
    ).toBeInTheDocument();
    expect(screen.getByText("Which project?", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("log", { name: "Conversation" })).toHaveAttribute("aria-busy", "false");
  });

  it("retries an unavailable Ask conversation registry", async () => {
    const fetchMock = stubBackend({ askHistoryUnavailable: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));

    expect(await screen.findAllByText("Conversation history could not be loaded.")).toHaveLength(2);
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/ask/conversations")).length;
    await userEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/ask/conversations")))
        .toHaveLength(attempts + 1),
    );
  });

  it("keeps saved Ask history when selecting its conversation fails", async () => {
    stubBackend({ askConversationFailsAfterFirst: true, askHistory: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));

    const saved = await screen.findByRole("button", { name: /Saved project question/ });
    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await userEvent.click(saved);

    expect(await screen.findByText("Conversation history could not be loaded.")).toBeInTheDocument();
    expect(saved).toBeInTheDocument();
  });

  it("loads older conversations and turns from their scroll boundaries", async () => {
    const fetchMock = stubBackend({ askHistory: true, askHistoryPages: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));
    expect(await screen.findByText("Which project was saved?", { exact: true })).toBeInTheDocument();

    const historyList = document.querySelector(".ask-agent-history-list") as HTMLUListElement;
    Object.defineProperties(historyList, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, value: 760 },
    });
    fireEvent.scroll(historyList);
    expect(await screen.findByText("Older saved question", { exact: true })).toBeInTheDocument();

    const thread = document.querySelector(".ask-agent-thread") as HTMLDivElement;
    Object.defineProperties(thread, {
      scrollTop: { configurable: true, value: 0, writable: true },
      scrollHeight: { configurable: true, value: 1000, writable: true },
      clientHeight: { configurable: true, value: 500 },
    });
    fireEvent.scroll(thread);
    expect(await screen.findByText("Older saved turn", { exact: true })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("before_turn=2"))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("before_updated_at"))).toBe(true);
  });

  it("retries failed older Ask conversation pages", async () => {
    const fetchMock = stubBackend({ askHistory: true, askHistoryMoreUnavailable: true, askHistoryPages: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));
    await screen.findByText("Which project was saved?", { exact: true });

    const historyList = document.querySelector(".ask-agent-history-list") as HTMLUListElement;
    Object.defineProperties(historyList, {
      scrollHeight: { configurable: true, value: 1000 },
      clientHeight: { configurable: true, value: 300 },
      scrollTop: { configurable: true, value: 760 },
    });
    fireEvent.scroll(historyList);
    const retry = await screen.findByRole("button", { name: "Retry loading history" });
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).includes("before_updated_at")).length;
    await userEvent.click(retry);
    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("before_updated_at")))
        .toHaveLength(attempts + 1),
    );
  });

  it("retries failed older Ask turns", async () => {
    const fetchMock = stubBackend({ askHistory: true, askHistoryPages: true, askOlderTurnsUnavailable: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Ask Agent" }));
    await screen.findByText("Which project was saved?", { exact: true });

    const thread = document.querySelector(".ask-agent-thread") as HTMLDivElement;
    Object.defineProperties(thread, {
      scrollTop: { configurable: true, value: 0, writable: true },
      scrollHeight: { configurable: true, value: 1000, writable: true },
      clientHeight: { configurable: true, value: 500 },
    });
    fireEvent.scroll(thread);
    const retry = await screen.findByRole("button", { name: "Retry loading older questions" });
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).includes("before_turn=2")).length;
    await userEvent.click(retry);
    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("before_turn=2")))
        .toHaveLength(attempts + 1),
    );
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
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    expect(await screen.findByText("Demo Corp")).toBeInTheDocument();
    expect(screen.getByText("DEMO-CORP-01 · Company")).toBeInTheDocument();
    expect(screen.getByText("Ada West")).toBeInTheDocument();
    expect(screen.getByText("Our side")).toBeInTheDocument();
    expect(screen.queryByText("company", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("our_side", { exact: true })).not.toBeInTheDocument();
  });

  it("shows governed former names when a customer entity is expanded", async () => {
    const fetchMock = stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));
    await userEvent.click((await screen.findByText("Demo Corp")).closest("button")!);

    expect(screen.getByText("Former name: Demo Industries")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/corporate-entities/corp-demo/related")),
      ).toHaveLength(1),
    );
    await userEvent.click(screen.getByText("Demo Corp").closest("button")!);
    expect(screen.queryByText("Former name: Demo Industries")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Demo Corp").closest("button")!);
    expect(screen.getByText("Former name: Demo Industries")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/corporate-entities/corp-demo/related")),
    ).toHaveLength(1);
  });

  it("opens a linked post from an expanded customer entity", async () => {
    stubBackend({ customerRelatedPost: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));
    await userEvent.click((await screen.findByText("Demo Corp")).closest("button")!);

    const relatedPost = await screen.findByRole("button", { name: "Open related post: Linked post" });
    expect(relatedPost).toHaveTextContent("Linked body preview ...");
    await userEvent.click(relatedPost);
    expect(await screen.findByRole("dialog", { name: "Linked post" })).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    expect(await screen.findByText("Demo Group")).toBeInTheDocument();
    const subsidiaryRow = screen.getByText("Demo Corp").closest("li");
    expect(subsidiaryRow).not.toBeNull();
    const parentRow = screen.getByText("Demo Group").closest("li");
    expect(parentRow).not.toBeNull();
    // The subsidiary's <li> is nested inside the parent's <li>, not a
    // sibling at the same top level.
    expect(parentRow?.contains(subsidiaryRow)).toBe(true);
  });

  it("filters the customer master tree by scope facet", async () => {
    // ADR 0125: 자사 속성은 필터로 접근해야 한다 -- an entity's own-company,
    // granted-customer, observed, or unclassified facet must be a real
    // filter, not just a label. All four buckets are on by default.
    stubBackend({ customerScopeFacets: true });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    expect(await screen.findByText("Own Scope Corp")).toBeInTheDocument();
    expect(screen.getByText("Granted Scope Corp")).toBeInTheDocument();
    expect(screen.getByText("Observed Scope Corp")).toBeInTheDocument();
    expect(screen.getByText("Observed Hierarchy Corp")).toBeInTheDocument();
    expect(screen.getByText("Unclassified Scope Corp")).toBeInTheDocument();
    expect(screen.getByText("Observed hierarchy")).toBeInTheDocument();
    expect(screen.getByText("Scope not classified")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("checkbox", { name: "Own company" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Granted customer" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Observed in posts" }));

    expect(screen.queryByText("Own Scope Corp")).not.toBeInTheDocument();
    expect(screen.queryByText("Granted Scope Corp")).not.toBeInTheDocument();
    expect(screen.queryByText("Observed Scope Corp")).not.toBeInTheDocument();
    expect(screen.queryByText("Observed Hierarchy Corp")).not.toBeInTheDocument();
    expect(screen.getByText("Unclassified Scope Corp")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("checkbox", { name: "Unclassified" }));
    expect(screen.getByText("No entities match the current scope filter.")).toBeInTheDocument();
  });

  it("nests R&R rows under their affiliated organization instead of repeating the affiliation as flat text", async () => {
    // UI/UX feedback: two researchers at the same institute should read
    // as a tree (institute -> its researchers), not three unrelated
    // bullets that each separately say "· 소속: Case Institute".
    stubBackend({ rrOrgWithMembers: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const instituteRow = await screen.findByText("Case Institute", { selector: "li *" });
    const instituteItem = instituteRow.closest("li") as HTMLLIElement;
    const researcherOne = screen.getByText("Case Researcher One").closest("li") as HTMLLIElement;
    const researcherTwo = screen.getByText("Case Researcher Two").closest("li") as HTMLLIElement;
    expect(instituteItem.contains(researcherOne)).toBe(true);
    expect(instituteItem.contains(researcherTwo)).toBe(true);
    // Nesting itself conveys the affiliation -- repeating "· 소속: Case
    // Institute" text on every nested row would be redundant.
    expect(researcherOne.textContent).not.toContain("소속");
    expect(researcherTwo.textContent).not.toContain("소속");
  });

  it("nests key events sharing a project name instead of repeating the project name as a flat prefix", async () => {
    // UI/UX feedback: four key events that all began with the same
    // "{project}: " prefix read as flat, disconnected bullets even
    // though they clearly belong to one shared plan.
    stubBackend({ groupedKeyEvents: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const projectHeading = await screen.findByText("Case Facility Plan", { selector: "li > strong" });
    const projectItem = projectHeading.closest("li") as HTMLLIElement;
    const firstMilestone = screen.getByText("1st milestone discussed").closest("li") as HTMLLIElement;
    const secondMilestone = screen.getByText("2nd milestone discussed").closest("li") as HTMLLIElement;
    expect(projectItem.contains(firstMilestone)).toBe(true);
    expect(projectItem.contains(secondMilestone)).toBe(true);
    // An event with no shared project stays a flat, ungrouped bullet.
    const standalone = screen.getByText("Unrelated standalone event", { exact: false }).closest("li") as HTMLLIElement;
    expect(projectItem.contains(standalone)).toBe(false);
  });

  it("renders explicit semantic relationships with direction, evidence, and provenance", async () => {
    stubBackend({ semanticRelationships: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const relationships = await screen.findByRole("heading", { name: "Explicit semantic relationships" });
    const list = relationships.nextElementSibling as HTMLUListElement;
    expect(within(list).getByText("Responsible for")).toBeInTheDocument();
    expect(within(list).getByText("Precedes")).toBeInTheDocument();
    expect(within(list).getByText("synthetic_relation")).toBeInTheDocument();
    expect(within(list).getByText(/Alpha was completed before Beta\. · Confidence: 84%/)).toBeInTheDocument();

    const temporalRelation = within(list).getByText("Prototype Alpha").closest("li")!;
    await userEvent.click(within(temporalRelation).getByText("Evidence provenance"));
    expect(within(temporalRelation).getByText("Extraction source: Recorded extraction")).toBeInTheDocument();
  });

  it("shows every observed relationship role for a counterparty, flagging multi-role names", async () => {
    // Feature request (2026-08-19): a real counterparty is not limited
    // to one role -- a customer in one post can be a competitor,
    // supplier, or partner in another. The Customer Master screen must
    // surface the whole observed network per name, not just one role.
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

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
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    expect(await screen.findByText("CUST-0")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Resolve" }));

    expect(await screen.findByText("Southfield Utilities")).toBeInTheDocument();
    expect(screen.getByText("Managed customer")).toBeInTheDocument();
  });

  it("restores customer hint resolution after a failed corroboration", async () => {
    stubBackend({ admin: true, customerResolveUnavailable: true, manyCustomerHints: 1 });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Customer master" }));

    await userEvent.click(await screen.findByRole("button", { name: "Resolve" }));

    expect(
      await screen.findByText("This hint could not be resolved to a corroborated organization name."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resolve" })).toBeEnabled();
  });

  it("shows a customer-master load failure", async () => {
    stubBackend({ customerMasterUnavailable: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Customer master" }));
    expect(await screen.findByText("Customer master could not be loaded.")).toBeInTheDocument();
  });

  it("shows when no customer entities are connected", async () => {
    stubBackend({ emptyCustomerMaster: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Customer master" }));

    expect(
      await screen.findByText("No customer entities are connected to this account."),
    ).toBeInTheDocument();
  });

  it("hides the resolve action from an account without post_admin", async () => {
    stubBackend({ manyCustomerHints: 1 });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    expect(await screen.findByText("CUST-0")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resolve" })).not.toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    expect(await screen.findByText("CUST-0")).toBeInTheDocument();
    expect(screen.getByText(/Showing the first 30 of 45 observed customer identifiers/)).toBeInTheDocument();
    expect(screen.getByText("CUST-29")).toBeInTheDocument();
    expect(screen.queryByText("CUST-30")).not.toBeInTheDocument();
    expect(screen.queryByText("CUST-44")).not.toBeInTheDocument();
  });

  it("finds an observed customer code outside the ranked first page", async () => {
    const fetchMock = stubBackend({ manyCustomerHints: 45 });
    render(<App />);
    expect(await screen.findByRole("button", { name: "View post: Public post" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));

    await userEvent.type(screen.getByRole("searchbox", { name: "Find source customer code" }), "CUST-44");
    await userEvent.click(screen.getByRole("button", { name: "Find" }));

    expect(await screen.findByText("CUST-44")).toBeInTheDocument();
    expect(screen.queryByText("CUST-0")).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("hint_code=CUST-44"))).toBe(true);
  });

  it("shows a no-match state for an observed customer code", async () => {
    stubBackend({ manyCustomerHints: 2 });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Customer master" }));

    await userEvent.type(screen.getByRole("searchbox", { name: "Find source customer code" }), "CUST-99");
    await userEvent.click(screen.getByRole("button", { name: "Find" }));

    expect(await screen.findByText("No source customer evidence matches CUST-99.")).toBeInTheDocument();
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
    expect(
      screen.getByLabelText("Open post: Pricing renegotiation follow-up (Branch point)"),
    ).toHaveClass("lineage-dag-branch");
    expect(
      screen.getByLabelText("Open post: Unrelated: annual account review (Root record)"),
    ).toHaveClass("lineage-dag-root");
  });

  it("renders the board landmark and functional post controls", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    const board = await screen.findByRole("region", { name: "Board" });
    expect(within(board).getByRole("search", { name: "Search and filter posts" })).toBeInTheDocument();
    expect(within(board).getByLabelText("Search semantic evidence")).toHaveAttribute("type", "search");
    expect(within(board).getByRole("list", { name: "Board posts" })).toBeInTheDocument();
    expect(within(board).getByText(/Posts shown:/)).toBeInTheDocument();
    expect(within(board).getByRole("checkbox", { name: /VOP.*Voice of Partner/ })).toBeInTheDocument();

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

  it("derives missing board facets and applies every client-side sort and filter", async () => {
    stubBackend({
      manyBoardPosts: true,
      sourceDetailStateCode: "D",
      sourceDetailStateOptions: [],
      visibilityOptions: [],
      vocTypeOptions: [],
    });
    render(<App showLabPanels />);

    const board = await screen.findByRole("region", { name: "Board" });
    const titles = () =>
      within(board).getAllByRole("button", { name: /View post:/ }).map((button) => button.getAttribute("aria-label"));

    await userEvent.selectOptions(within(board).getByLabelText("Sort posts"), "title");
    expect(titles()).toEqual(["View post: Earlier partner post", "View post: Public post"]);
    await userEvent.selectOptions(within(board).getByLabelText("Sort posts"), "oldest");
    expect(titles()[0]).toContain("Earlier partner post");
    await userEvent.selectOptions(within(board).getByLabelText("Sort posts"), "newest");
    expect(titles()[0]).toContain("Public post");

    const voc = within(board).getByRole("checkbox", { name: "VOC — Voice of Customer" });
    await userEvent.click(voc);
    expect(within(board).queryByRole("button", { name: "View post: Earlier partner post" })).not.toBeInTheDocument();
    await userEvent.click(voc);

    const approved = within(board).getByRole("checkbox", { name: "A — Approved" });
    await userEvent.click(approved);
    expect(within(board).queryByRole("button", { name: "View post: Public post" })).not.toBeInTheDocument();
    await userEvent.click(approved);

    await userEvent.selectOptions(within(board).getByLabelText("Filter by visibility"), "private");
    expect(within(board).queryByRole("button", { name: "View post: Public post" })).not.toBeInTheDocument();
  });

  it("navigates compact board pagination without losing the current-page state", async () => {
    const fetchMock = stubBackend({ boardTotalCount: 400 });
    render(<App showLabPanels />);

    const pages = await screen.findByRole("navigation", { name: "Board pages" });
    expect(within(pages).getByRole("button", { name: "Page 1" })).toHaveAttribute("aria-current", "page");
    expect(within(pages).getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(within(pages).getByText("...")).toBeInTheDocument();

    await userEvent.click(within(pages).getByRole("button", { name: "Page 8" }));
    await waitFor(() =>
      expect(within(pages).getByRole("button", { name: "Page 8" })).toHaveAttribute("aria-current", "page"),
    );
    expect(within(pages).getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("offset=350"))).toBe(true);

    await userEvent.click(within(pages).getByRole("button", { name: "Previous page" }));
    await waitFor(() =>
      expect(within(pages).getByRole("button", { name: "Page 7" })).toHaveAttribute("aria-current", "page"),
    );
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("offset=300"))).toBe(true);

    await userEvent.click(within(pages).getByRole("button", { name: "Page 1" }));
    await waitFor(() =>
      expect(within(pages).getByRole("button", { name: "Page 1" })).toHaveAttribute("aria-current", "page"),
    );
    await userEvent.click(within(pages).getByRole("button", { name: "Next page" }));
    await waitFor(() =>
      expect(within(pages).getByRole("button", { name: "Page 2" })).toHaveAttribute("aria-current", "page"),
    );
  });

  it("uses canonical VOC acronyms with explanatory accessible names", async () => {
    stubBackend({
      vocTypeOptions: [
        { code: "voc", label: "legacy customer label" },
        { code: "vocc", label: "legacy customer-customer label" },
        { code: "voco", label: "legacy competitor label" },
        { code: "vom", label: "legacy market label" },
        { code: "vop", label: "legacy partner label" },
      ],
    });
    render(<App showLabPanels />);

    const board = await screen.findByRole("region", { name: "Board" });
    for (const code of ["VOC", "VOCC", "VOCO", "VOM", "VOP"]) {
      expect(within(board).getByText(code, { selector: ".board-voc-type-code" })).toBeInTheDocument();
    }
    expect(within(board).getByRole("checkbox", { name: "VOC — Voice of Customer" })).toBeInTheDocument();
    expect(
      within(board).getByRole("checkbox", { name: "VOCC — Voice of Customer's Customer" }),
    ).toBeInTheDocument();

    setLocale("ko");
    await waitFor(() =>
      expect(
        within(board).getByRole("checkbox", { name: "VOC — 고객의 소리 (Voice of Customer)" }),
      ).toBeInTheDocument(),
    );
  });

  it("explains and filters source detail state codes", async () => {
    const fetchMock = stubBackend({
      sourceDetailStateCode: "D",
      sourceDetailStateOptions: [
        { code: "W", label: "W" },
        { code: "D", label: "D" },
        { code: "A", label: "A" },
      ],
    });
    render(<App showLabPanels />);

    const board = await screen.findByRole("region", { name: "Board" });
    expect(
      within(board).getByRole("group", { name: "Filter by source detail state" }),
    ).toBeInTheDocument();
    expect(
      within(board).getByRole("checkbox", { name: "W — Writing in progress" }),
    ).toBeInTheDocument();
    expect(
      within(board).getByRole("checkbox", { name: "D — Pending approval" }),
    ).toBeInTheDocument();
    expect(
      within(board).getByRole("checkbox", { name: "A — Approved" }),
    ).toBeInTheDocument();
    expect(within(board).getByText("D", { selector: ".board-source-detail-state-code" })).toBeInTheDocument();
    expect(within(board).getByText("Pending approval", { selector: ".board-source-detail-state-description" })).toBeInTheDocument();

    await userEvent.click(within(board).getByRole("checkbox", { name: "D — Pending approval" }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes("source_detail_state=D"))).toBe(true),
    );

    setLocale("ko");
    await waitFor(() =>
      expect(
        within(board).getByRole("checkbox", { name: "D — 결재 중 (Pending approval)" }),
      ).toBeInTheDocument(),
    );
  });

  it("does not request derived analysis for a writing-state post", async () => {
    const fetchMock = stubBackend({ sourceDetailStateCode: " w " });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    expect(await screen.findByText("Summary is not created for writing posts.")).toBeInTheDocument();

    const requestedPaths = fetchMock.mock.calls.map(([url]) =>
      new URL(String(url), "https://backend.test").pathname,
    );
    expect(requestedPaths).not.toContain("/api/posts/post-1/summary");
    expect(requestedPaths).not.toContain("/api/posts/post-1/evaluation");
    expect(requestedPaths).not.toContain("/api/posts/post-1/five-w1h");
    expect(requestedPaths).not.toContain("/api/posts/post-1/keymen");
    expect(requestedPaths).not.toContain("/api/posts/post-1/counterparties");
    expect(requestedPaths).not.toContain("/api/posts/post-1/lineage");
    expect(requestedPaths).not.toContain("/api/posts/post-1/knowledge-graph");
    expect(requestedPaths).not.toContain("/api/posts/post-1/affiliate-tree");
    expect(requestedPaths).not.toContain("/api/posts/post-1/voc-evidence");
    expect(requestedPaths).not.toContain("/api/posts/post-1/content");
    expect(requestedPaths).not.toContain("/api/posts/post-1/source-research");
  });

  it("does not show an empty source detail state filter", async () => {
    const fetchMock = stubBackend({ sourceDetailStateOptions: [] });
    render(<App />);

    const board = await screen.findByRole("region", { name: "Board" });
    expect(
      within(board).queryByRole("group", { name: "Filter by source detail state" }),
    ).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalled();
  });

  it("does not request derived panels for writing posts", async () => {
    const fetchMock = stubBackend({
      sourceDetailStateCode: " w ",
      sourceDetailStateOptions: [{ code: "W", label: "W" }],
    });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await screen.findByText("The full body text.");

    const urls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(
      urls.some((url) =>
        /\/api\/posts\/[^/]+\/(five-w1h|keymen|counterparties|lineage|knowledge-graph|affiliate-tree|voc-evidence|evaluation)(?:\?|$)/.test(url),
      ),
    ).toBe(false);
  });

  it("opens a post from a DAG node click", async () => {
    stubBackend();
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByLabelText("Open post: Linked post"));
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

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
    expect(listButton).toHaveTextContent("Combination code");
    expect(listButton).toHaveTextContent("1000");
    expect(within(listButton).getByLabelText("Field combination: 1000, Customer only candidate")).toBeInTheDocument();

    await userEvent.click(listButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByText(/Voice of Customer ·/)).toBeInTheDocument();
    expect(screen.getByText("Constructive stance: 2")).toBeInTheDocument();
    expect(screen.getByText("Sales-lead specificity: 3")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Related posts" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open related post: Linked post" })).toBeInTheDocument();
    expect(screen.queryByText("Not yet evaluated.")).not.toBeInTheDocument();
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

    fireEvent.change(language, { target: { value: "unsupported" } });
    expect(document.documentElement.lang).toBe("ja");
  });

  it("keeps the selected language when preference persistence is unavailable", async () => {
    stubBackend({ preferenceUnavailable: true });
    render(<App showLabPanels />);

    const language = await screen.findByRole("combobox", {
      name: /language|언어|言語|语言|ngôn ngữ/i,
    });
    await userEvent.selectOptions(language, "ja");

    await waitFor(() => expect(document.documentElement.lang).toBe("ja"));
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

  it("reports a lineage rebuild failure and restores the action", async () => {
    stubBackend({ admin: true, rebuildUnavailable: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByText("Advanced review tools"));
    const rebuild = await screen.findByRole("button", { name: /rebuild lineage/i });

    await userEvent.click(rebuild);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(rebuild).toBeEnabled();
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
    const provenance = screen.getByText("Evidence provenance").closest("details");
    expect(provenance).not.toBeNull();
    expect(provenance).not.toHaveAttribute("open");
    await userEvent.click(screen.getByText("Evidence provenance"));
    expect(screen.getByText(/Ontology class:/)).toBeInTheDocument();
    expect(screen.getByText(/Extraction source: Semantic extraction/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence field: Stored semantic evidence/)).toBeInTheDocument();
    expect(screen.queryByText("contextual_orchestrator_semantic")).not.toBeInTheDocument();
    expect(screen.queryByText("https://contextualwisdomlab.github.io/lineageweave/ontology#Project")).not.toBeInTheDocument();
    expect(screen.getByText("첫 번째 이벤트")).toBeInTheDocument();
    expect(screen.getByText(/우리 측 후속/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "R&R Keyman: Ada West" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "R&R affiliation: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "R&R person: Priya Nair" })).toBeInTheDocument();
    expect(screen.getByText("당사").closest("li")).toHaveTextContent("Organization");
    expect(screen.queryByRole("button", { name: "R&R Keyman: 당사" })).not.toBeInTheDocument();
    // R&R groups by affiliated organization, then orders each group
    // organization-first, then team, then person (ADR 0004's PROV-O
    // broader/narrower direction) -- not raw extraction order. "Northridge
    // Grid Devices" is itself an organization row, but it is affiliated
    // with "Northridge Grid" and must cluster with Priya Nair under that
    // parent, not stand as its own separate group.
    const rrList = screen.getByText("당사").closest("ul");
    const rrOrder = within(rrList as HTMLElement)
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    const demoCorpGroup = rrOrder.slice(
      rrOrder.findIndex((text) => text?.includes("설계팀")),
      rrOrder.findIndex((text) => text?.includes("Ada West")) + 1,
    );
    expect(demoCorpGroup[0]).toContain("설계팀");
    expect(demoCorpGroup[1]).toContain("Ada West");
    const northridgeGroupStart = rrOrder.findIndex((text) => text?.includes("Northridge Grid Devices"));
    expect(rrOrder[northridgeGroupStart]).toContain("Northridge Grid Devices");
    expect(rrOrder[northridgeGroupStart + 1]).toContain("Priya Nair");
    // ADR 0141: an unresolved affiliation shows the specific reason instead
    // of the generic "Not linked to catalog" label when the reason is known.
    expect(screen.getByText("(No live enrichment service configured)")).toBeInTheDocument();
    // ADR 0141: an unresolved primary actor (organization/person) also gets
    // a specific reason note, where it previously showed nothing at all.
    expect(screen.getByText("(Checked, not independently corroborated)")).toBeInTheDocument();
    const relatedPosts = screen.getByRole("heading", { name: "Related posts", level: 3 }).closest(
      ".related-posts-section",
    );
    expect(relatedPosts).not.toBeNull();
    expect(within(relatedPosts as HTMLElement).getByText("Indirect relation")).toBeInTheDocument();
    expect(relatedPosts).toHaveTextContent("Linked post");
    // The Event Lineage DAG belongs to the opened post, not the list surface.
    expect(screen.getAllByLabelText("A-100 lineage")).toHaveLength(1);
    expect(
      screen.getAllByLabelText("Open post: Pricing renegotiation follow-up (Branch point)"),
    ).toHaveLength(1);
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
    expect(screen.getByRole("dialog", { name: "Public post" })).toBe(popup);
    expect(popup).toHaveAttribute("aria-modal", "true");
    expect(popup).toHaveAttribute("aria-labelledby", "post-detail-title");
    const evaluation = within(popup as HTMLElement).getByRole("heading", {
      name: "Post quality (IRT)",
    });
    const eventLineage = within(popup as HTMLElement).getByRole("heading", { name: "Event Lineage" });
    const affiliate = within(popup as HTMLElement).getByRole("heading", { name: "Affiliate tree" });
    const keyman = within(popup as HTMLElement).getByRole("heading", { name: "Keymen" });
    expect(within(popup as HTMLElement).getByText("Lineage evidence")).toBeInTheDocument();
    expect(within(popup as HTMLElement).getByText("Inference boundary")).toBeInTheDocument();
    expect(within(popup as HTMLElement).getByRole("table", { name: /Evidence trail/ })).toBeInTheDocument();
    expect(evaluation.compareDocumentPosition(eventLineage) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(
      0,
    );
    expect(affiliate.compareDocumentPosition(keyman) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    const ask = within(popup as HTMLElement).getByRole("heading", { name: "Ask about this lineage" });
    expect(keyman.compareDocumentPosition(ask) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it.each([
    [
      "no_relation_found" as const,
      "Compared against other posts in its group; none were found related.",
    ],
    [
      "no_comparison_group" as const,
      "No other posts share this record's group yet, so nothing was available to compare it against.",
    ],
  ])(
    "shows the specific isolation reason %s instead of the generic empty-lineage message",
    async (isolationReason, expectedMessage) => {
      stubBackend({ lineageIsolationReason: isolationReason });
      render(<App showLabPanels />);

      await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

      const popup = await screen.findByRole("dialog", { name: "Public post" });
      await waitFor(() => expect(within(popup).getByText(expectedMessage)).toBeInTheDocument());
      expect(within(popup).queryByText("No linked posts yet.")).not.toBeInTheDocument();
    },
  );

  it("keeps the generic empty-lineage copy for historical graph responses", async () => {
    stubBackend({ emptyLineage: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const popup = await screen.findByRole("dialog", { name: "Public post" });
    expect(await within(popup).findByText("No linked posts yet.")).toBeInTheDocument();
    expect(
      within(popup).getByText("No linked posts have been established for this record."),
    ).toBeInTheDocument();
  });

  it("labels a direct related post", async () => {
    stubBackend({ directLineage: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const relatedPosts = screen.getByRole("heading", { name: "Related posts", level: 3 }).closest(
      ".related-posts-section",
    );
    expect(relatedPosts).not.toBeNull();
    expect(within(relatedPosts as HTMLElement).getByText("Direct relation")).toBeInTheDocument();
  });

  it("keeps the post popup keyboard-contained and restores the opener after Escape", async () => {
    const user = userEvent.setup();
    stubBackend();
    render(<App showLabPanels />);

    const opener = await screen.findByRole("button", { name: "View post: Public post" });
    await user.click(opener);
    const dialog = await screen.findByRole("dialog", { name: "Public post" });
    await waitFor(() => expect(dialog).toHaveFocus());

    await user.keyboard("{Tab}");
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    const evidenceSummary = screen.getByText("Evidence provenance");
    for (let step = 0; step < 40 && document.activeElement !== evidenceSummary; step += 1) {
      await user.keyboard("{Tab}");
    }
    expect(evidenceSummary).toHaveFocus();
    const ariaHiddenTabStop = document.createElement("button");
    ariaHiddenTabStop.setAttribute("aria-hidden", "true");
    dialog.insertBefore(ariaHiddenTabStop, screen.getByRole("button", { name: "Close" }).nextSibling);
    await user.keyboard("{Tab}");
    expect(ariaHiddenTabStop).not.toHaveFocus();
    const ariaHiddenGroup = document.createElement("div");
    ariaHiddenGroup.setAttribute("aria-hidden", "true");
    const nestedAriaHiddenTabStop = document.createElement("button");
    ariaHiddenGroup.append(nestedAriaHiddenTabStop);
    dialog.insertBefore(ariaHiddenGroup, screen.getByRole("button", { name: "Close" }).nextSibling);
    await user.keyboard("{Tab}");
    expect(nestedAriaHiddenTabStop).not.toHaveFocus();
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(dialog).toContainElement(document.activeElement as HTMLElement);
    expect((document.activeElement as HTMLElement).closest("details:not([open])")).toBeNull();
    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(opener).toHaveFocus();
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

  it("shows processing instead of an empty summary while the request is pending", async () => {
    stubBackend({ summaryPending: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const processing = await screen.findByText("Summary is being prepared.");
    expect(processing.closest('[role="status"]')).toBeInTheDocument();
    expect(screen.queryByText("No summary is available for this record yet.")).not.toBeInTheDocument();
  }, 15_000);

  it("separates an unavailable summary from a missing saved summary", async () => {
    stubBackend({ summaryUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const summaryHeading = await screen.findByText("Summary could not be generated.");
    expect(summaryHeading.closest('[role="alert"]')).toBeInTheDocument();
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Retry summary refresh" })).toBeInTheDocument();
    expect(screen.queryByText("No saved summary exists for this record.")).not.toBeInTheDocument();
  });

  it("refreshes newly processed source content after summary generation", async () => {
    stubBackend({ contentAfterSummary: true, contentProcessing: true });
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

  it("keeps linked records readable when the focused graph is unavailable", async () => {
    stubBackend({ focusedLineageUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    expect(
      await screen.findByText("The linked records are listed above. The graph is not available for this view."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open related post: Linked post" })).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("button", { name: "Close evidence panel" }));
    expect(screen.queryByText("The evidence panel should show exactly this text.")).not.toBeInTheDocument();
  });

  it("stops loading and gives the reader a next action when cited evidence is unavailable", async () => {
    const fetchMock = stubBackend({ evidenceUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.type(await screen.findByPlaceholderText(/what happened/i), "What happened?");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));
    const evidenceChips = await screen.findAllByRole("button", { name: "Open evidence: Linked post" });
    await userEvent.click(evidenceChips[evidenceChips.length - 1]);

    const alertTitle = await screen.findByText(
      "Source evidence is unavailable. Continue with the saved answer.",
    );
    const alert = alertTitle.closest('[role="alert"]');
    expect(alert).toHaveTextContent("Source evidence is unavailable. Continue with the saved answer.");
    expect(alert).toHaveTextContent("Retry opening this source, or keep reading the saved answer.");
    expect(screen.getByRole("button", { name: "Retry evidence" })).toBeInTheDocument();
    expect(screen.queryByText("Loading source post...")).not.toBeInTheDocument();
    const attempts = fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/api/posts/post-2")).length;
    await userEvent.click(screen.getByRole("button", { name: "Retry evidence" }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.filter(([input]) => String(input).endsWith("/api/posts/post-2")),
      ).toHaveLength(attempts + 1),
    );
  }, 15_000);

  it("shows post chat history failures without hiding saved evidence", async () => {
    stubBackend({ postChatHistoryUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    expect(await screen.findByText("Conversation history could not be loaded.")).toBeInTheDocument();
    expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument();
  });

  it("keeps seeded post chat visible when a saved conversation cannot be loaded", async () => {
    stubBackend({ postAskHistory: true, postChatConversationUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /Saved post question/ }));

    expect(await screen.findByText("Conversation history could not be loaded.")).toBeInTheDocument();
    expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument();
  });

  it("renders legacy citation identifiers and ignores an empty Enter ask", async () => {
    const fetchMock = stubBackend({ legacyChatCitations: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const input = await screen.findByPlaceholderText(/what happened/i);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(
      fetchMock.mock.calls.filter(
        ([url, init]) => String(url).endsWith("/api/posts/post-1/chat") && init?.method === "POST",
      ),
    ).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Open evidence: post-2" })).toBeInTheDocument();
  });

  it("submits a saved question from the seeded suggestion chips", async () => {
    const fetchMock = stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ask seeded question: Who is involved?" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) => String(url).endsWith("/api/posts/post-1/chat") && init?.method === "POST",
      );
      expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({ question: "Who is involved?" });
    });
  });

  it("renders a grounded chat answer without inventing source chips", async () => {
    stubBackend({ chatNoCitations: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.type(screen.getByPlaceholderText(/what happened/i), "Summarize this record");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));

    const answer = await screen.findByText("Here is what happened, drawing on the linked post.");
    expect(answer.closest(".chat-answer")?.querySelector(".chat-citations")).toBeNull();
  });

  it("shows a clear empty state when chat is 503 without an orchestrator", async () => {
    const fetchMock = stubBackend({ chatUnavailable: true });
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
    const postAttempts = fetchMock.mock.calls.filter(
      ([url, init]) => String(url).endsWith("/api/posts/post-1/chat") && init?.method === "POST",
    ).length;
    await userEvent.click(screen.getAllByRole("button", { name: /ask seeded question/i })[0]);
    expect(
      fetchMock.mock.calls.filter(
        ([url, init]) => String(url).endsWith("/api/posts/post-1/chat") && init?.method === "POST",
      ),
    ).toHaveLength(postAttempts);
  });

  it("shows a clear empty state when evaluate is 503 without an orchestrator", async () => {
    stubBackend({ admin: true, chatUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    expect(await screen.findByText("Constructive stance: 2")).toBeInTheDocument();
    expect(screen.getByText("Sales-lead specificity: 3")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: /evaluate post/i }));

    await waitFor(() =>
      expect(screen.getByText("Evaluation is temporarily unavailable. Saved evidence is still available.")).toBeInTheDocument(),
    );
    expect(screen.getByText(/This analysis channel is unavailable/)).toBeInTheDocument();
    expect(screen.getByText(/A missing signal is not a negative fact/)).toBeInTheDocument();
    expect(screen.getByText("Constructive stance: 2")).toBeInTheDocument();
    expect(screen.getByText("Sales-lead specificity: 3")).toBeInTheDocument();
    expect(document.getElementById("post-quality-criterion-general_sentiment_positive")).not.toBeNull();
    expect(document.getElementById("post-quality-criterion-sales_lead_specificity")).not.toBeNull();
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
      expect(screen.getByText("Verification unavailable (search is not configured).")).toBeInTheDocument(),
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
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for 설계팀" }));
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
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(screen.getByText("Related to Demo Corp").closest(".related-keymen")).toHaveTextContent(
      "Ada West (Our side)",
    );
  });

  it.each([
    ["person" as const, "Ada West", null],
    ["entity" as const, "Demo Corp", "Related nodes for Demo Corp"],
    ["team" as const, "설계팀", "Related nodes for 설계팀"],
  ])("fails closed when a %s related-node lookup is unavailable", async (kind, name, nestedAction) => {
    stubBackend({ relatedUnavailable: kind });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    if (nestedAction) {
      await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
      await userEvent.click(await screen.findByRole("button", { name: nestedAction }));
    } else {
      await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    }

    const panel = await screen.findByText(`Related to ${name}`);
    expect(panel.closest(".related-keymen")).toHaveTextContent("No related nodes in the visible graph.");
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

  it("fails closed when tickets cannot be loaded and ignores an empty Enter", async () => {
    const fetchMock = stubBackend({ ticketListUnavailable: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    expect(await screen.findByText("No tickets yet.")).toBeInTheDocument();
    fireEvent.keyDown(screen.getByPlaceholderText(/new ticket title/i), { key: "Enter" });
    expect(
      fetchMock.mock.calls.filter(
        ([url, init]) => String(url).endsWith("/api/posts/post-1/tickets") && init?.method === "POST",
      ),
    ).toHaveLength(0);
  });

  it("restores ticket creation after a request failure", async () => {
    stubBackend({ ticketCreateUnavailable: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await userEvent.type(screen.getByPlaceholderText(/new ticket title/i), "Synthetic ticket");
    await userEvent.click(screen.getByRole("button", { name: /create ticket/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create ticket/i })).toBeEnabled();
  });

  it("keeps a ticket's saved status when an update fails", async () => {
    stubBackend({ ticketUpdateUnavailable: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.type(screen.getByPlaceholderText(/new ticket title/i), "Synthetic ticket");
    await userEvent.click(screen.getByRole("button", { name: /create ticket/i }));

    const status = await screen.findByLabelText(/status for synthetic ticket/i);
    await userEvent.selectOptions(status, "closed");

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(status).toHaveValue("open");
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

  it("retries an unavailable activity feed", async () => {
    const fetchMock = stubBackend({ activityUnavailable: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    const heading = await screen.findByRole("heading", { name: "Activity" });
    const section = heading.closest("section")!;
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/posts/post-1/activity")).length;
    await userEvent.click(within(section).getAllByRole("button", { name: "Refresh" })[0]);
    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/posts/post-1/activity")))
        .toHaveLength(attempts + 1),
    );
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

  it("explains when no commitment can be derived", async () => {
    stubBackend({ admin: true, deriveNoCommitment: true });
    render(<App showLabPanels />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await userEvent.click(await screen.findByRole("button", { name: /derive commitment/i }));

    expect(await screen.findByText("No customer commitment found in this post.")).toBeInTheDocument();
  });

  it("tells the reader how to populate an empty calendar", async () => {
    stubBackend({ calendarCommitments: [] });
    render(<App showLabPanels />);

    await waitFor(() =>
      expect(
        screen.getByText(/no upcoming commitments\. derive one from a post/i),
      ).toBeInTheDocument(),
    );
  });

  it("renders CalDAV availability and events", async () => {
    stubBackend({
      calendarCommitments: [],
      calendarEvents: [
        {
          event_id: "event-synthetic",
          summary: "Synthetic design review",
          starts_at: "2026-01-15T09:00:00Z",
        },
      ],
      caldavAvailable: true,
    });
    render(<App showLabPanels />);

    expect(await screen.findByText("Synthetic design review")).toBeInTheDocument();
    expect(screen.getByText("2026-01-15T09:00:00Z")).toBeInTheDocument();
  });

  it("opens a commitment from the Calendar workspace", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Calendar" }));
    await userEvent.click(await screen.findByRole("button", { name: /open commitment for: public post/i }));

    expect(await screen.findByRole("dialog", { name: "Public post" })).toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.has("workspace")).toBe(false);
  });

  it("retries calendar loading failures", async () => {
    const fetchMock = stubBackend({ calendarUnavailable: true });
    render(<App showLabPanels />);

    const calendarAlert = (await screen.findAllByRole("alert"))[0];
    const retry = within(calendarAlert).getByRole("button", { name: "Retry" });
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/calendar")).length;
    await userEvent.click(retry);

    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/calendar")))
        .toHaveLength(attempts + 1),
    );
  });

  it("names RankWeave unavailability on home rankings instead of inventing a fused score", async () => {
    stubBackend();
    render(<App />);

    expect(await screen.findByText("Rankings · RankWeave not available")).toBeInTheDocument();
    expect(screen.queryByText("Pricing renegotiation: revised quote sent")).not.toBeInTheDocument();
  });

  it("names an accepted empty RankWeave result", async () => {
    stubBackend({ rankings: { status: "accepted", rankings: [] } });
    render(<App />);

    expect(await screen.findByText("No fused rankings from RankWeave.")).toBeInTheDocument();
  });

  it("retries ranking loading failures", async () => {
    const fetchMock = stubBackend({ rankingsUnavailable: true });
    render(<App />);

    const rankings = await screen.findByRole("region", { name: "Rankings" });
    const retry = within(rankings).getByRole("button", { name: "Retry" });
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/rankings")).length;
    await userEvent.click(retry);

    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/rankings")))
        .toHaveLength(attempts + 1),
    );
  });

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
          },
          {
            post_id: "post-2",
            post_title: "Pricing renegotiation: revised quote sent",
            fused_rank: 2,
          },
        ],
      },
    });
    render(<App />);

    const rankingButton = await screen.findByRole("button", {
      name: /open ranking: public post/i,
    });
    expect(rankingButton).toHaveTextContent("Public post");
    expect(rankingButton).toHaveTextContent("Rankings · rankweave");
    expect(rankingButton).toHaveTextContent("rank 1");
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
      "Open this run to see why it failed, then connect the measurement service and re-run.",
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
      "Refresh this run. Reconstruction is already queued on the durable outbox.",
    );
    await userEvent.click(lineageButton);
    expect(screen.queryByRole("button", { name: "Start reconstruction" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh this run" })).toBeInTheDocument();
    expect(
      screen.getAllByText("Refresh this run. Reconstruction is already queued on the durable outbox."),
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
      "Open this run to see why it failed, then connect the measurement service and re-run.",
    );
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
      const currentNode = within(popup as HTMLElement).getByLabelText(
        "Open post: Public post (Current record, Root record)",
      );
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
      screen.getByRole("button", { name: "Open period report 2026-W02" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "No posts were available at this cutoff for the period report. Open a later run, or ask an administrator to capture a newer snapshot.",
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

  it("retries the analysis-run registry after a load failure", async () => {
    const fetchMock = stubBackend({ analysisRunsUnavailable: true });
    render(<App showLabPanels />);

    const retry = await screen.findByRole("button", { name: "Retry" });
    const attempts = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/analysis-runs")).length;
    await userEvent.click(retry);

    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/api/analysis-runs")))
        .toHaveLength(attempts + 1),
    );
  });

  it("explains an analysis-run idempotency conflict", async () => {
    stubBackend({ analysisRunCreateStatus: 409 });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Request a lineage reconstruction" }),
    );

    expect(
      await screen.findByText(
        "This request key already names a different reconstruction. Request again to start a new run.",
      ),
    ).toBeInTheDocument();
  });

  it("shows a generic analysis-run request failure", async () => {
    stubBackend({ analysisRunCreateStatus: 500 });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Request a lineage reconstruction" }),
    );

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request a lineage reconstruction" })).toBeEnabled();
  });

  it.each([
    [404 as const, "This analysis run is not visible."],
    [500 as const, null],
  ])("handles an analysis-run detail failure %s", async (status, expected) => {
    stubBackend({ analysisRunOpenStatus: status });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", {
        name: "Open analysis run: Lineage reconstruction · Succeeded · Demo Corp",
      }),
    );

    if (expected) {
      expect(await screen.findByText(expected)).toBeInTheDocument();
    } else {
      expect(await screen.findByRole("alert")).toBeInTheDocument();
    }
  });

  it("restores the start action after reconstruction fails", async () => {
    stubBackend({ analysisRunStartUnavailable: true });
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Request a lineage reconstruction" }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Start reconstruction" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start reconstruction" })).toBeEnabled();
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
    expect(screen.getByLabelText("Leftover pairs")).toBeInTheDocument();
    const closestPair = screen.getByRole("button", { name: /open leftover closest pair: public post/i });
    const farthestPair = screen.getByRole("button", {
      name: /open leftover farthest pair: specification revision requested/i,
    });
    expect(closestPair).toHaveTextContent("Closest leftover: Public post · sales-lead");
    expect(closestPair).toHaveTextContent(
      "Open Public post, then read Post quality criterion sales-lead.",
    );
    expect(closestPair).not.toHaveTextContent(/sat closest to after main effects/);
    expect(closestPair).toHaveTextContent("d 0.12");
    expect(farthestPair).toHaveTextContent("Farthest leftover: Specification revision requested · negative");
    expect(farthestPair).toHaveTextContent(
      "Open Specification revision requested, then read Post quality criterion negative.",
    );
    expect(farthestPair).not.toHaveTextContent(/sat farthest from after main effects/);
    expect(farthestPair).toHaveTextContent("d 1.84");
    const memberButton = screen.getByRole("button", { name: /open report post: public post/i });
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
      screen.getByRole("button", { name: "Compare Business unit (PU): Demo Report High, mean θ 0.81" }),
    ).toHaveTextContent("mean θ 0.81");
    await userEvent.click(
      screen.getByRole("button", { name: "Compare Thread group: A-100, mean θ 0.81" }),
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "A-100 is the opened grouping. Read its mean θ and member posts below, then open a post.",
    );
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

  it("opens a leftover pair post from the report panel", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(
      await screen.findByRole("button", { name: /open leftover closest pair: public post/i }),
    );
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    const criterion = await waitFor(() => {
      const landed = document.getElementById("post-quality-criterion-sales_lead_specificity");
      expect(landed).not.toBeNull();
      return landed as HTMLElement;
    });
    expect(criterion).toHaveAttribute("aria-current", "true");
    expect(criterion).toHaveTextContent(/Sales-lead specificity: 3/);
    await waitFor(() => expect(criterion).toHaveFocus());
    expect(screen.queryByRole("status", { name: "Event Lineage next action" })).not.toBeInTheDocument();
  });

  it("opens Event Lineage, Keyman, and evaluation from a report member click", async () => {
    stubBackend();
    render(<App showLabPanels />);

    await userEvent.click(await screen.findByRole("button", { name: /open report post: public post/i }));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByText("Constructive stance: 2")).toBeInTheDocument();
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

  it("shows an explicit period-report load failure", async () => {
    stubBackend({ reportsUnavailable: true });
    render(<App showLabPanels />);

    const heading = await screen.findByRole("heading", { name: "Period reports" });
    expect(await within(heading.closest("section")!).findByRole("alert")).toBeInTheDocument();
  });

  it("reports a period-report rebuild failure and restores the action", async () => {
    stubBackend({ admin: true, reportRebuildUnavailable: true });
    render(<App showLabPanels />);
    const rebuild = await screen.findByRole("button", { name: "Rebuild report" });

    await userEvent.click(rebuild);

    const heading = screen.getByRole("heading", { name: "Period reports" });
    expect(await within(heading.closest("section")!).findByRole("alert")).toBeInTheDocument();
    expect(rebuild).toBeEnabled();
  });

  it("keeps advanced review tools out of the workspace board", async () => {
    stubBackend();
    render(<App />);

    expect(await screen.findByRole("navigation", { name: "Workspace navigation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Board" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("Authorized scope")).toHaveTextContent("DEMO-CORP / DEMO-PU");
    expect(screen.queryByText("Advanced review tools")).not.toBeInTheDocument();
    const mobileMenu = screen.getByRole("button", { name: "Open navigation" });
    expect(mobileMenu).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(mobileMenu);
    expect(screen.getByRole("dialog", { name: "Workspace navigation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close Workspace navigation" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Workspace navigation" })).not.toBeInTheDocument();
    expect(mobileMenu).toHaveFocus();
    await userEvent.click(mobileMenu);
    expect(screen.getAllByRole("button", { name: "Close" })).toHaveLength(1);
    expect(document.getElementById("mobile-workspace-navigation")).toBeInTheDocument();
    const drawerClose = document.querySelector<HTMLButtonElement>(".mobile-drawer-close");
    expect(drawerClose).not.toBeNull();
    await userEvent.click(drawerClose as HTMLButtonElement);
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    const appHeader = document.querySelector<HTMLElement>("header.app-header");
    expect(appHeader).not.toBeNull();
    expect(within(appHeader as HTMLElement).getByLabelText("Language")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Workspace navigation" })).not.toHaveTextContent("Language");
    await userEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const mobileNavigation = document.getElementById("mobile-workspace-navigation");
    expect(mobileNavigation).not.toBeNull();
    await userEvent.click(within(mobileNavigation as HTMLElement).getByRole("button", { name: "Customer master" }));
    expect(await screen.findByRole("heading", { name: "Customer master" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    await userEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getByRole("button", { name: "Close Workspace navigation" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Workspace navigation" })).not.toBeInTheDocument();
    await userEvent.click(
      within(appHeader as HTMLElement).getByRole("button", { name: "Search" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("searchbox", { name: "Search semantic evidence" })).toHaveFocus(),
    );
  });

  it("logs out through the OIDC client", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Log out" }));

    expect(signoutRedirect).toHaveBeenCalledOnce();
  });

  it("opens Board operations from the Admin workspace", async () => {
    stubBackend({ admin: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Admin" }));
    await userEvent.click(await screen.findByRole("button", { name: "Open post operations" }));

    const board = await screen.findByRole("region", { name: "Board" });
    const advanced = await within(board).findByText("Advanced review tools");
    expect(advanced.closest("details")).toHaveAttribute("open");
    expect(new URL(window.location.href).searchParams.has("workspace")).toBe(false);
  });

  it("discloses every authorized corporation and business unit code", async () => {
    stubBackend({ manyAffiliations: true });
    render(<App />);

    const scope = await screen.findByLabelText("Authorized scope");
    const summary = scope.querySelector("summary");
    expect(summary).not.toBeNull();
    expect(summary).toHaveTextContent("DEMO-CORP / DEMO-PU");
    expect(summary).toHaveTextContent("+2");
    expect(scope).not.toHaveAttribute("open");

    await userEvent.click(summary as HTMLElement);

    expect(scope).toHaveAttribute("open", "");
    expect(within(scope).getByText("NORTH-CORP / NORTH-PU")).toBeVisible();
    expect(within(scope).getByText("HQ-CORP")).toBeVisible();
  });

  it("does not derive GNB scope from an unrelated entity list", async () => {
    stubBackend({ noAffiliations: true, pluralAffiliations: true });
    render(<App />);

    await screen.findByRole("region", { name: "Board" });
    expect(screen.queryByLabelText("Authorized scope")).not.toBeInTheDocument();
  });

  it("opens the site map utility and closes it after navigation or Escape", async () => {
    stubBackend();
    render(<App />);

    const siteMapButton = await screen.findByRole("button", { name: "Site map" });
    expect(siteMapButton).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(siteMapButton);
    expect(screen.getByRole("region", { name: "Site map" })).toBeInTheDocument();
    expect(siteMapButton).toHaveAttribute("aria-expanded", "true");

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("region", { name: "Site map" })).not.toBeInTheDocument();

    await userEvent.click(siteMapButton);
    const siteMap = screen.getByRole("region", { name: "Site map" });
    await userEvent.click(within(siteMap).getByRole("button", { name: "Customer master" }));
    expect(await screen.findByRole("heading", { name: "Customer master" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Site map" })).not.toBeInTheDocument();
  });

  it("lets a keyboard user skip the header and GNB to reach main content", async () => {
    stubBackend();
    render(<App />);

    await screen.findByRole("navigation", { name: "Workspace navigation" });
    const skipLink = screen.getByRole("link", { name: "Skip to main content" });
    expect(skipLink).toHaveAttribute("href", "#main-content");
    const main = document.getElementById("main-content");
    expect(main).not.toBeNull();
    await userEvent.click(skipLink);
    expect(main).toHaveFocus();
  });

  it("keeps the current workspace while global search is open", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Customer master" }));
    expect(await screen.findByRole("heading", { name: "Customer master" })).toBeInTheDocument();
    const searchButton = screen.getByRole("button", { name: "Search" });
    await userEvent.click(searchButton);

    const searchInput = await screen.findByRole("searchbox", { name: "Search semantic evidence" });
    expect(screen.getByRole("heading", { name: "Customer master" })).toBeInTheDocument();
    expect(searchButton).toHaveAttribute("aria-expanded", "true");
    expect(searchInput).toHaveFocus();

    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("heading", { name: "Customer master" })).toBeInTheDocument();
    expect(searchButton).toHaveFocus();
    expect(screen.queryByRole("searchbox", { name: "Search semantic evidence" })).not.toBeInTheDocument();
  });

  it("restores the workspace from the URL and responds to browser navigation", async () => {
    stubBackend();
    window.history.replaceState({}, "", "/?workspace=calendar");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Calendar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Calendar" })).toHaveAttribute("aria-current", "page");

    await userEvent.click(screen.getByRole("button", { name: "Ask Agent" }));
    expect(new URL(window.location.href).searchParams.get("workspace")).toBe("ask");

    window.history.replaceState({}, "", "/?workspace=ask&post=post-1");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByText("Starting evidence: post-1")).toBeInTheDocument();

    window.history.replaceState({}, "", "/?workspace=ask");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() =>
      expect(screen.queryByText(/Starting evidence:/)).not.toBeInTheDocument(),
    );

    window.history.replaceState({}, "", "/?workspace=calendar");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(await screen.findByRole("heading", { name: "Calendar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Calendar" })).toHaveAttribute("aria-current", "page");
  });

  it("does not expose the admin workspace from an unauthorized deep link", async () => {
    stubBackend();
    window.history.replaceState({}, "", "/?workspace=admin");
    render(<App />);

    expect(await screen.findByRole("region", { name: "Board" })).toBeInTheDocument();
    await waitFor(() => expect(new URL(window.location.href).searchParams.has("workspace")).toBe(false));
    expect(screen.queryByText("Admin endpoint catalog")).not.toBeInTheDocument();
  });

  it("submits global search only after an explicit query", async () => {
    const fetchMock = stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Customer master" }));
    await screen.findByRole("heading", { name: "Customer master" });
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    const globalSearchInput = await screen.findByRole("searchbox", { name: "Search semantic evidence" });

    await userEvent.type(globalSearchInput, "not found{Enter}");

    const board = await screen.findByRole("region", { name: "Board" });
    expect(within(board).getByLabelText("Search semantic evidence")).toHaveValue("not found");
    expect(await screen.findByText("No posts match the current filters.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("search=not+found"))).toBe(true);
  });

  it("retries a failed Board load without leaving the workspace", async () => {
    const fetchMock = stubBackend({ postsUnavailable: true });
    render(<App />);

    const board = await screen.findByRole("region", { name: "Board" });
    const alert = await within(board).findByRole("alert");
    const attempts = fetchMock.mock.calls.filter(([url]) => new URL(String(url)).pathname === "/api/posts").length;
    await userEvent.click(within(alert).getByRole("button", { name: "Retry" }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([url]) => new URL(String(url)).pathname === "/api/posts"))
        .toHaveLength(attempts + 1),
    );
    expect(screen.getByRole("region", { name: "Board" })).toBeInTheDocument();
  });

  it("does not navigate when the global search is opened before posts load", async () => {
    const fetchMock = stubBackend({ deferPosts: true });
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    await userEvent.click(screen.getByRole("button", { name: "Customer master" }));
    expect(await screen.findByRole("heading", { name: "Customer master" })).toBeInTheDocument();

    fetchMock.releasePosts();
    await userEvent.click(screen.getByRole("button", { name: "Board" }));
    const searchInput = await screen.findByRole("searchbox", { name: "Search semantic evidence" });
    expect(searchInput).not.toHaveFocus();
  });

  it("closes a post popup when browser history moves back", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    expect(await screen.findByRole("heading", { name: "Public post" })).toBeInTheDocument();
    expect(new URL(window.location.href).searchParams.get("post")).toBe("post-1");

    window.history.replaceState({}, "", "/");
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => expect(screen.queryByRole("heading", { name: "Public post" })).not.toBeInTheDocument());
  });
});
