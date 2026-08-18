import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const signinRedirect = vi.fn();
const signoutRedirect = vi.fn();
let mockAuth: Record<string, unknown>;

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuth,
}));

beforeEach(() => {
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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App, unauthenticated", () => {
  it("shows a login button that starts the real OIDC redirect", async () => {
    render(<App />);
    const button = screen.getByRole("button", { name: /log in/i });
    await userEvent.click(button);
    expect(signinRedirect).toHaveBeenCalledTimes(1);
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
      }[];
    };
    chatUnavailable?: boolean;
    searchUnavailable?: boolean;
    verificationEvidenceUrl?: string | null;
    failedLineageRun?: boolean;
    runningLineageRun?: boolean;
    failedReportRun?: boolean;
    succeededReportRun?: boolean;
    succeededTeppRun?: boolean;
    acceptedTeppRun?: boolean;
    distinctTeppClocks?: boolean;
    omitTeppRecordedAt?: boolean;
    pendingTeppRun?: boolean;
    hiddenAnalysisRun?: boolean;
    pluralAffiliations?: boolean;
    deferMe?: boolean;
    meFailed?: boolean;
    postBody?: string;
    emptyPosts?: boolean;
    emptyLineage?: boolean;
    emptyRoles?: boolean;
  }): ReturnType<typeof vi.fn> & { releaseMe: () => void } {
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
    let analysisRunListCalls = 0;

    let releaseMe = () => {};
    const meReady = options?.deferMe
      ? new Promise<void>((resolve) => {
          releaseMe = resolve;
        })
      : Promise.resolve();

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

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
        const teppEvidence = options?.acceptedTeppRun
          ? {
              tepp_evidence_kind: "aggregate transport evidence",
              tepp_contract_version: 1,
              tepp_accepted_run_id: "demo-tepp-accepted-opaque",
              tepp_run_state: "accepted",
              tepp_idempotency_key: "demo-tepp-seed-2026-w02-succeeded",
              tepp_evidence_sha256: "a".repeat(64),
              tepp_received_at: "2026-01-12T12:45:00Z",
              ...(options?.omitTeppRecordedAt
                ? {}
                : {
                    tepp_recorded_at: options?.distinctTeppClocks
                      ? "2026-01-12T12:46:00Z"
                      : "2026-01-12T12:45:00Z",
                  }),
              tepp_completed_artifact_available: false,
            }
          : {};
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
            ...teppEvidence,
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
                      : {
                          failure_code: options?.acceptedTeppRun
                            ? "tepp_completed_result_unsupported"
                            : "tepp_not_available",
                        }),
                  },
                ],
          }),
        );
      }
      if (url.endsWith("/api/analysis-runs/run-demo-lineage")) {
        if (options?.hiddenAnalysisRun) {
          return Promise.resolve(
            new Response(JSON.stringify({ detail: "Not found" }), {
              status: 404,
              headers: { "Content-Type": "application/json" },
            }),
          );
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
        analysisRunListCalls += 1;
        const includeStaleLineageRow = !(
          options?.hiddenAnalysisRun && analysisRunListCalls > 1
        );
        return Promise.resolve(
          jsonResponse({
            analysis_runs: [
              ...(createdPendingLineage ? [createdPendingLineage] : []),
              ...(createdPendingTepp ? [createdPendingTepp] : []),
              ...(includeStaleLineageRow
                ? [
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
                  ]
                : []),
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
                ...(options?.acceptedTeppRun
                  ? {
                      tepp_evidence_kind: "aggregate transport evidence",
                      tepp_contract_version: 1,
                      tepp_accepted_run_id: "demo-tepp-accepted-opaque",
                      tepp_run_state: "accepted",
                      tepp_evidence_sha256: "a".repeat(64),
                      tepp_received_at: "2026-01-12T12:45:00Z",
                      ...(options?.omitTeppRecordedAt
                        ? {}
                        : {
                            tepp_recorded_at: options?.distinctTeppClocks
                              ? "2026-01-12T12:46:00Z"
                              : "2026-01-12T12:45:00Z",
                          }),
                      tepp_completed_artifact_available: false,
                    }
                  : {}),
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
      if (url.endsWith("/api/customer-group-tree")) {
        return Promise.resolve(
          jsonResponse({
            trees: [
              {
                entity_id: "group-1",
                entity_name: "Demo Group",
                entity_level_code: "group",
                entity_level_label: "Group",
                abbreviations: [],
                children: [
                  {
                    entity_id: "corp-1",
                    entity_name: "Demo Corp",
                    entity_level_code: "company",
                    entity_level_label: "Company",
                    abbreviations: [
                      {
                        raw_organization_name: "DC",
                        verification_status_code: "verify_corroborated",
                        verification_evidence_url: "https://example.test/demo-corp-dc",
                      },
                    ],
                    children: [
                      {
                        entity_id: "plant-1",
                        entity_name: "Demo Plant",
                        entity_level_code: "plant",
                        entity_level_label: "Plant",
                        abbreviations: [],
                        children: [],
                      },
                    ],
                  },
                ],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/abbreviation-tree-matches")) {
        return Promise.resolve(
          jsonResponse({
            matches: [
              {
                raw_organization_name: "DC",
                corporate_entity_id: "corp-1",
                verification_status_code: "verify_corroborated",
                verification_evidence_url: "https://example.test/demo-corp-dc",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/corroborate-abbreviations") && method === "POST") {
        if (options?.searchUnavailable) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Abbreviation tree corroboration is unavailable: set SEARXNG_BASE_URL",
              }),
              { status: 503, headers: { "Content-Type": "application/json" } },
            ),
          );
        }
        return Promise.resolve(
          jsonResponse({
            matches: [
              {
                raw_organization_name: "DC",
                corporate_entity_id: "corp-1",
                verification_status_code: "verify_corroborated",
                verification_evidence_url: "https://example.test/demo-corp-dc",
              },
            ],
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
                  },
                  {
                    pair_kind: "farthest",
                    post_id: "post-2",
                    post_title: "Specification revision requested",
                    criterion_code: "general_sentiment_negative",
                    leftover_distance: 1.84,
                    leftover_residual: -1.1,
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
      if (url.endsWith("/api/lineage")) {
        if (options?.emptyLineage) {
          return Promise.resolve(jsonResponse({ nodes: [], edges: [] }));
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
      if (url.endsWith("/api/posts")) {
        if (options?.emptyPosts) {
          return Promise.resolve(jsonResponse([]));
        }
        return Promise.resolve(
          jsonResponse([
            {
              post_id: "post-1",
              post_title: "Public post",
              voc_type_code: "voc",
              voc_type_label: "Voice of Customer",
              visibility_code: "public",
              visibility_label: "Public",
              created_at: "2026-01-01T00:00:00Z",
            },
          ]),
        );
      }
      const postOneUrl = new URL(url, "https://backend.test");
      if (postOneUrl.pathname === "/api/posts/post-1") {
        const asOf = postOneUrl.searchParams.get("as_of");
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            post_title: "Public post",
            post_body: options?.postBody ?? "The full body text.",
            voc_type_code: "voc",
            voc_type_label: "Voice of Customer",
            visibility_code: "public",
            visibility_label: "Public",
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
      if (url.endsWith("/api/posts/post-2")) {
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
      if (url.endsWith("/api/posts/post-1/five-w1h")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            slots: [
              {
                slot_code: "who",
                slot_label: "누가",
                values: options?.emptyRoles ? [] : ["Ada West", "당사", "설계팀"],
                empty_next_action: options?.emptyRoles ? "이 사건의 누가 아직 없습니다" : null,
              },
              {
                slot_code: "what",
                slot_label: "무엇을",
                values: ["첫 번째 이벤트"],
                empty_next_action: null,
              },
              {
                slot_code: "when",
                slot_label: "언제",
                values: ["2026-01-01"],
                empty_next_action: null,
              },
              {
                slot_code: "where",
                slot_label: "어디서",
                values: ["Demo Corp", "Northridge Grid"],
                empty_next_action: null,
              },
              {
                slot_code: "why",
                slot_label: "왜",
                values: [],
                empty_next_action: "이 사건의 왜가 아직 없습니다",
              },
              {
                slot_code: "how",
                slot_label: "어떻게",
                values: [],
                empty_next_action: "이 사건의 어떻게가 아직 없습니다",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/lineage-qa") && method === "POST") {
        const body = JSON.parse(String(init?.body));
        const question = String(body.question ?? "");
        if (question.includes("왜") || question.toLowerCase().includes("why")) {
          return Promise.resolve(
            jsonResponse({
              post_id: "post-1",
              question,
              slot_code: "why",
              values: [],
              grounded: false,
              empty_next_action: "이 사건의 왜가 아직 없습니다",
            }),
          );
        }
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            question,
            slot_code: "who",
            values: ["Ada West", "당사", "설계팀"],
            grounded: true,
            empty_next_action: null,
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/summary")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            korean_summary: "이것은 요약입니다.",
            key_events: ["첫 번째 이벤트"],
            roles_and_responsibilities: options?.emptyRoles
              ? []
              : [
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
                detail: "Keyman extraction is unavailable: set ORCHESTRATOR_BASE_URL / ORCHESTRATOR_API_KEY",
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
        return Promise.resolve(
          jsonResponse({
            person_id: "person-ada",
            person_name: "Ada West",
            person_side_code: "our_side",
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
        if (options?.emptyLineage) {
          return Promise.resolve(jsonResponse({ post_id: "post-1", direct: [], indirect: [] }));
        }
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            direct: [],
            indirect: [{ post_id: "post-2", post_title: "Linked post" }],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-2/summary")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-2",
            korean_summary: "연결된 사건의 요약입니다.",
            key_events: [],
            roles_and_responsibilities: [
              {
                actor_name: "Priya Nair",
                responsibility: "고객 측 수신",
                actor_type_code: "prov_person",
                affiliated_organization_name: "Northridge Grid",
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-2/lineage")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-2",
            direct: [],
            indirect: [{ post_id: "post-1", post_title: "Public post" }],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-2/five-w1h")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-2",
            slots: [
              {
                slot_code: "who",
                slot_label: "누가",
                values: ["Priya Nair"],
                empty_next_action: null,
              },
              {
                slot_code: "what",
                slot_label: "무엇을",
                values: ["Linked post"],
                empty_next_action: null,
              },
              {
                slot_code: "when",
                slot_label: "언제",
                values: ["2026-01-02"],
                empty_next_action: null,
              },
              {
                slot_code: "where",
                slot_label: "어디서",
                values: ["Northridge Grid"],
                empty_next_action: null,
              },
              {
                slot_code: "why",
                slot_label: "왜",
                values: [],
                empty_next_action: "이 사건의 왜가 아직 없습니다",
              },
              {
                slot_code: "how",
                slot_label: "어떻게",
                values: [],
                empty_next_action: "이 사건의 어떻게가 아직 없습니다",
              },
            ],
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
      return Promise.reject(new Error(`unexpected fetch: ${method} ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    return Object.assign(fetchMock, { releaseMe });
  }


  it("lets Demo Analyst walk 주간 VOC to 사건 lineage to 역할·책임 after seed-shaped data", async () => {
    stubBackend();
    render(<App />);

    expect(await screen.findByRole("heading", { name: "주간 VOC" })).toBeInTheDocument();
    const voc = await screen.findByRole("button", { name: "Open VOC item: Public post" });
    expect(voc).toHaveTextContent("Voice of Customer");
    expect(screen.queryByText("Rankings · RankWeave not available")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Open analysis run/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/leftover/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/mean θ/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Request a lineage/)).not.toBeInTheDocument();

    await userEvent.click(voc);

    expect(await screen.findByRole("heading", { name: "사건 lineage" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "원문" })).toBeInTheDocument();
    expect(screen.getByText("The full body text.")).toBeInTheDocument();
    expect(screen.getByLabelText("A-100 lineage")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "5W1H" })).toBeInTheDocument();
    expect(screen.getByText("누가").closest("div")).toHaveTextContent("Ada West");
    expect(screen.getByText("이 사건의 왜가 아직 없습니다")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "이 사건 lineage에 묻기" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "역할·책임" })).toBeInTheDocument();
    const roles = screen.getByRole("region", { name: "역할·책임" });
    expect(roles).toHaveTextContent("Person");
    expect(roles).toHaveTextContent("Ada West");
    expect(roles).toHaveTextContent("Organization");
    expect(roles).toHaveTextContent("당사");
    expect(roles).toHaveTextContent("Team");
    expect(roles).toHaveTextContent("설계팀");
    expect(roles).toHaveTextContent("우리 측 후속");
    expect(screen.getByLabelText("R&R next decision")).toHaveTextContent(
      "다음 사람 조치를 이 행위자에서 결정하세요.",
    );

    expect(screen.queryByRole("heading", { name: "Ask about this lineage" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Event Lineage next action" })).not.toBeInTheDocument();
    expect(screen.queryByText(/is current in Event Lineage/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Read Keyman and evaluation next/)).not.toBeInTheDocument();
    expect(screen.queryByText(/TEPP/)).not.toBeInTheDocument();
  });

  it("selects a lineage node and shows that node's R&R", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open VOC item: Public post" }));
    await userEvent.click(await screen.findByLabelText("Open post: Linked post"));
    expect(await screen.findByRole("heading", { name: "Linked post" })).toBeInTheDocument();
    const roles = screen.getByRole("region", { name: "역할·책임" });
    expect(roles).toHaveTextContent("Person");
    expect(roles).toHaveTextContent("Priya Nair");
  });

  it("renders the A-100 fork on the opened VOC item, not as a home module", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByRole("heading", { name: "주간 VOC" })).toBeInTheDocument();
    expect(screen.queryByLabelText("A-100 lineage")).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Open VOC item: Public post" }));
    expect(await screen.findByLabelText("A-100 lineage")).toBeInTheDocument();
    expect(screen.getByLabelText("Open post: Pricing renegotiation follow-up")).toHaveClass(
      "lineage-dag-branch",
    );
    expect(screen.queryByRole("button", { name: /rebuild lineage/i })).not.toBeInTheDocument();
  });

  it("shows the source picture instead of dumping raw base64", async () => {
    const tinyPng =
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";
    stubBackend({
      postBody: `<p>Quote attached.</p><img src="data:image/png;base64,${tinyPng}" alt=""><p>Please confirm.</p>`,
    });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open VOC item: Public post" }));
    const image = await screen.findByRole("img", { name: /embedded image at character offset/i });
    expect(image).toHaveAttribute("src", `data:image/png;base64,${tinyPng}`);
    expect(screen.getByText("Quote attached.")).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(tinyPng))).not.toBeInTheDocument();
  });

  it("answers a 5W1H question from the semantic-layer query and fail-closes why", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open VOC item: Public post" }));
    await userEvent.type(await screen.findByLabelText("Lineage question"), "누가 관련되었나요?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByLabelText("Grounded lineage answer")).toHaveTextContent("Ada West");
    expect(screen.getByLabelText("A-100 lineage")).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Lineage question"));
    await userEvent.type(screen.getByLabelText("Lineage question"), "왜 이 일이 일어났나요?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByLabelText("Ungrounded lineage answer")).toHaveTextContent(
      "이 사건의 왜가 아직 없습니다",
    );
  });

  it("shows fail-closed empty copy on the three screens", async () => {
    stubBackend({ emptyPosts: true });
    render(<App />);
    expect(await screen.findByText("이번 주 감사할 VOC가 없습니다")).toBeInTheDocument();
  });

  it("shows fail-closed empty lineage and R&R on an opened item", async () => {
    stubBackend({ emptyLineage: true, emptyRoles: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Open VOC item: Public post" }));
    expect(await screen.findByText("연결된 사건이 없습니다")).toBeInTheDocument();
    expect(screen.getByText("역할·책임이 아직 없습니다")).toBeInTheDocument();
    expect(screen.getByText("이 사건의 누가 아직 없습니다")).toBeInTheDocument();
  });
});
