import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    chatUnavailable?: boolean;
    searchUnavailable?: boolean;
    verificationEvidenceUrl?: string | null;
  }) {
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

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/me")) {
        return Promise.resolve(
          jsonResponse({
            user_account_id: options?.admin ? "acct-admin" : "acct-1",
            display_name: options?.admin ? "Demo Admin" : "Demo Analyst",
            permission_codes: options?.admin ? ["post_read", "post_admin"] : ["post_read"],
          }),
        );
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
                grouping_label: "Test Corp",
                mean_theta: 0.01,
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
      if (url.endsWith("/api/posts/post-1")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            post_title: "Public post",
            post_body: "The full body text.",
            voc_type_code: "voc",
            voc_type_label: "Voice of Customer",
            visibility_code: "public",
            visibility_label: "Public",
            created_at: "2026-01-01T00:00:00Z",
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
      if (url.endsWith("/api/posts/post-1/summary")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            korean_summary: "이것은 요약입니다.",
            key_events: ["첫 번째 이벤트"],
            roles_and_responsibilities: [
              { person_name: "Ada West", responsibility: "우리 측 후속" },
              { person_name: "Priya Nair", responsibility: "고객 측 수신" },
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
                affiliation_organization_name: "Demo Corp",
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
                affiliation_organization_name: "Northridge Grid",
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
                entity_level_code: "company",
                entity_level_label: "Company",
                relevance: 0.2,
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
                affiliation_organization_name: "Demo Corp",
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
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            direct: [],
            indirect: [{ post_id: "post-2", post_title: "Linked post" }],
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
    return fetchMock;
  }

  it("renders the A-100 fork as a git-style DAG, not a flat edge list", async () => {
    stubBackend();
    render(<App />);
    expect(await screen.findByLabelText("A-100 lineage")).toBeInTheDocument();
    expect(screen.getByLabelText("Open post: Pricing renegotiation follow-up")).toHaveClass(
      "lineage-dag-branch",
    );
    expect(screen.getByLabelText("Open post: Unrelated: annual account review")).toHaveClass(
      "lineage-dag-root",
    );
    expect(screen.queryByText("Public post → Linked post")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /rebuild lineage/i })).not.toBeInTheDocument();
  });

  it("opens a post from a DAG node click", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByLabelText("Open post: Public post"));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });

  it("fetches and renders the post list, then opens a detail popup on click", async () => {
    const fetchMock = stubBackend();

    render(<App />);

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
    expect(screen.queryByText("Not yet evaluated.")).not.toBeInTheDocument();
  });

  it("rebuilds lineage when the account has post_admin", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /rebuild lineage/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/lineage/rebuild"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("renders the Korean summary, key events, R&R, and Event Lineage panels", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() => expect(screen.getByText("이것은 요약입니다.")).toBeInTheDocument());
    expect(screen.getByText("첫 번째 이벤트")).toBeInTheDocument();
    expect(screen.getByText(/우리 측 후속/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "R&R Keyman: Ada West" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("간접")).toBeInTheDocument());
    expect(screen.getByText("간접").closest("li")).toHaveTextContent("Linked post");
    // The popup Event Lineage is the same A-100 reconstruct DAG as the home
    // page, not a flat list -- two SVGs (home + popup) share the fork.
    expect(screen.getAllByLabelText("A-100 lineage").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByLabelText("Open post: Pricing renegotiation follow-up").length).toBeGreaterThanOrEqual(2);
  });

  it("shows a seeded Ask exchange without an orchestrator round-trip", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByText("The seeded follow-up after the site visit.")).toBeInTheDocument(),
    );
    expect(screen.getByText("Ada West and Priya Nair are the Keymen on this thread.")).toBeInTheDocument();
    expect(
      screen.getByText("The next commitment is Send Northridge Grid the revised quote, due 2026-01-12."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask seeded question: what happened between these events/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask seeded question: who is involved/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask seeded question: what is the next commitment/i })).toBeInTheDocument();
  });

  it("asks a chat question and slides in the evidence panel for a cited source on click", async () => {
    stubBackend();
    render(<App />);

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

  it("shows a clear empty state when chat is 503 without an orchestrator", async () => {
    stubBackend({ chatUnavailable: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByPlaceholderText(/what happened/i)).toBeInTheDocument());
    await userEvent.type(screen.getByPlaceholderText(/what happened/i), "What happened?");
    await userEvent.click(screen.getByRole("button", { name: /^ask$/i }));

    await waitFor(() =>
      expect(screen.getByText("Chat unavailable (LLM orchestrator not configured).")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/what happened/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^ask$/i })).not.toBeInTheDocument();
    expect(
      screen.getByText("Only seeded questions can be answered without an orchestrator."),
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
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /evaluate post/i }));

    await waitFor(() =>
      expect(screen.getByText("Evaluation unavailable (LLM orchestrator not configured).")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /evaluate post/i })).not.toBeInTheDocument();
  });

  it("shows a clear empty state when extract Keymen is 503 without an orchestrator", async () => {
    stubBackend({ admin: true, chatUnavailable: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /extract keymen/i }));

    await waitFor(() =>
      expect(screen.getByText("Keyman extraction unavailable (LLM orchestrator not configured).")).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /extract keymen/i })).not.toBeInTheDocument();
  });

  it("shows a clear empty state when derive commitment is 503 without an orchestrator", async () => {
    stubBackend({ admin: true, chatUnavailable: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: /derive commitment/i }));

    await waitFor(() =>
      expect(
        screen.getByText("Commitment derivation unavailable (LLM orchestrator not configured)."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText(/HTTP 503/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /derive commitment/i })).not.toBeInTheDocument();
  });

  it("shows a clear empty state when verify is 503 without search", async () => {
    stubBackend({ admin: true, searchUnavailable: true });
    render(<App />);

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
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() => expect(screen.getByText("Demo Group")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Affiliate org: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Counterparty org: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Keyman affiliation: Demo Corp" })).toBeInTheDocument();
    expect(screen.getByText("(Company)")).toBeInTheDocument();
    expect(screen.getAllByText(/Ada West \(Our side\)/).length).toBeGreaterThanOrEqual(1);
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
    expect(
      screen.getByRole("button", { name: "Related nodes for Priya Nair, Northridge Grid (Counterparty)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).not.toHaveTextContent(
      "Priya Nair (Person)",
    );
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).not.toHaveTextContent(
      "Priya Nair (Counterparty)",
    );
    const relatedPanel = screen.getByText("Related to Ada West").closest(".related-keymen");
    expect(relatedPanel).toHaveTextContent("Linked post");
    expect(relatedPanel).not.toHaveTextContent("Linked post (Post)");
    await userEvent.click(screen.getByRole("button", { name: "Open related post: Linked post" }));
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

  it("opens related Keyman nodes from an R&R person", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "R&R Keyman: Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Priya Nair, Northridge Grid (Counterparty)" }),
    ).toBeInTheDocument();
  });

  it("opens related nodes from a related corporate entity", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Demo Corp (Company)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Related to Ada West").closest(".related-keymen")).not.toHaveTextContent(
      "Demo Corp (Organization)",
    );
    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Demo Corp (Company)" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    ).toBeInTheDocument();
  });

  it("shows the VOC excerpt under its counterparty, not a detached list", async () => {
    stubBackend();
    render(<App />);
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
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "VOC Keyman: Northridge Grid" }));
    await waitFor(() => expect(screen.getByText("Related to Priya Nair")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    ).toBeInTheDocument();
  });

  it("opens related Keyman nodes from an affiliate-tree person", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Affiliate Keyman: Priya Nair" }));
    await waitFor(() => expect(screen.getByText("Related to Priya Nair")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    ).toBeInTheDocument();
  });

  it("opens related nodes from a Keyman affiliation organization", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Keyman affiliation: Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    ).toBeInTheDocument();
  });

  it("opens related nodes from an affiliate-tree organization", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Affiliate org: Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Affiliate org: Northridge Grid" })).not.toBeInTheDocument();
  });

  it("opens related nodes from a classified counterparty organization", async () => {
    stubBackend();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await userEvent.click(await screen.findByRole("button", { name: "Counterparty org: Demo Corp" }));
    await waitFor(() => expect(screen.getByText("Related to Demo Corp")).toBeInTheDocument());
    expect(
      screen.getByRole("button", { name: "Related nodes for Ada West, Demo Corp (Our side)" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Counterparty org: Northridge Grid" })).not.toBeInTheDocument();
  });

  it("links a verification badge only for http(s) evidence URLs", async () => {
    stubBackend({ verificationEvidenceUrl: "https://example.test/searxng?q=Northridge" });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    const badge = await screen.findByRole("link", { name: "VOC verification: Northridge Grid" });
    expect(badge).toHaveAttribute("href", "https://example.test/searxng?q=Northridge");
  });

  it("does not turn a javascript: evidence URL into a verification link", async () => {
    stubBackend({ verificationEvidenceUrl: "javascript:alert(1)" });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() =>
      expect(screen.getByLabelText("VOC verification: Northridge Grid")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("link", { name: "VOC verification: Northridge Grid" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("VOC verification: Northridge Grid").tagName).toBe("SPAN");
  });

  it("lets post_admin verify pending counterparties against web search", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App />);

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
    render(<App />);

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
    render(<App />);

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
    render(<App />);

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
    render(<App />);

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
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("No tickets yet.")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /derive commitment/i })).not.toBeInTheDocument();
  });

  it("derives a customer commitment and shows its due date on the ticket list", async () => {
    stubBackend({ admin: true });
    render(<App />);

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
    render(<App />);

    await waitFor(() =>
      expect(
        screen.getByText(/no upcoming commitments\. derive one from a post/i),
      ).toBeInTheDocument(),
    );
  });

  it("shows upcoming commitments on the home page calendar and opens the post on click", async () => {
    stubBackend();
    render(<App />);

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

  it("shows the calibrated period-report mean theta on the home page", async () => {
    stubBackend();
    render(<App />);

    expect(await screen.findByText(/mean θ 0.42/)).toBeInTheDocument();
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
    render(<App />);

    expect(await screen.findByLabelText("Grouping comparison")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /compare process_unit: demo report high/i })).toHaveTextContent(
      "mean θ 0.81",
    );
    await userEvent.click(screen.getByRole("button", { name: /compare thread_group: a-100/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/reports/thread_group/2026-W02"),
        expect.anything(),
      ),
    );
  });

  it("selects a linked week from the FIPC trend strip", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /open report period 2026-W03/i }));
    const periodInput = screen.getByLabelText("Report period");
    expect(periodInput).toHaveValue("2026-W03");
  });

  it("opens Event Lineage, Keyman, and evaluation from a report member click", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /open report post: public post/i }));
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByText("Constructive stance: 2")).toBeInTheDocument();
    expect(screen.getAllByText(/Ada West/).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("A-100 lineage").length).toBeGreaterThanOrEqual(2);
  });

  it("lets post_admin rebuild the period report", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /rebuild report/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/reports/process_unit/2026-W02/rebuild"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
