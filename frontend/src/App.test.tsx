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

  function stubBackend(options?: { admin?: boolean; calendarCommitments?: unknown[] }) {
    const tickets: {
      issue_ticket_id: string;
      post_id: string;
      ticket_status_code: string;
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
        events.unshift({
          event_id: `event-${nextEventId++}`,
          event_type: "ticket_status_changed",
          actor_account_id: "acct-admin",
          summary: `Ticket status changed to ${body.ticket_status_code}`,
        });
        return Promise.resolve(jsonResponse(ticket));
      }
      if (url.endsWith("/api/posts/post-1/activity") && method === "GET") {
        return Promise.resolve(jsonResponse({ events }));
      }
      if (url.endsWith("/api/posts/post-1/derive-commitment") && method === "POST") {
        const ticket = {
          issue_ticket_id: `ticket-${nextTicketId++}`,
          post_id: "post-1",
          ticket_status_code: "open",
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
        return Promise.resolve(jsonResponse({ commitments: options?.calendarCommitments ?? [] }));
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
              visibility_code: "public",
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
            visibility_code: "public",
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
      if (url.endsWith("/api/posts/post-1/summary")) {
        return Promise.resolve(
          jsonResponse({
            post_id: "post-1",
            korean_summary: "이것은 요약입니다.",
            key_events: ["첫 번째 이벤트"],
            roles_and_responsibilities: [{ person_name: "Jordan", responsibility: "일정 안내" }],
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
        return Promise.resolve(jsonResponse({ extracted_count: 1 }));
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
            ],
            counterparties: [
              {
                counterparty_entity_name: "Northridge Grid",
                relationship_type_code: "rel_voc",
                relationship_label: "Voice of Customer",
                evidence_excerpt:
                  "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
                verification_status_code: "verify_pending",
                verification_evidence_url: null,
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
                counterparty_entity_name: "Northridge Grid",
                relationship_type_code: "rel_voc",
                relationship_label: "Voice of Customer",
                verification_status_code: "verify_pending",
                verification_evidence_url: null,
              },
            ],
          }),
        );
      }
      if (url.endsWith("/api/posts/post-1/verify-relations") && method === "POST") {
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
      if (url.endsWith("/api/posts/post-1/chat") && method === "POST") {
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

    await userEvent.click(listButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
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
    expect(screen.getByText(/일정 안내/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("간접")).toBeInTheDocument());
    expect(screen.getByText("간접").closest("li")).toHaveTextContent("Linked post");
    // The popup Event Lineage is the same A-100 reconstruct DAG as the home
    // page, not a flat list -- two SVGs (home + popup) share the fork.
    expect(screen.getAllByLabelText("A-100 lineage").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByLabelText("Open post: Pricing renegotiation follow-up").length).toBeGreaterThanOrEqual(2);
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

    await userEvent.click(screen.getByRole("button", { name: "Open evidence: Linked post" }));

    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

  it("shows the affiliate tree, VOC excerpt, and related Keyman nodes on click", async () => {
    stubBackend();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));

    await waitFor(() => expect(screen.getByText("Demo Group")).toBeInTheDocument());
    expect(screen.getByText("Demo Corp")).toBeInTheDocument();
    expect(screen.getByText("(Company)")).toBeInTheDocument();
    expect(screen.getByText(/Ada West \(Our side\)/)).toBeInTheDocument();
    expect(screen.queryByText(/our_side/)).not.toBeInTheDocument();
    expect(screen.getByText("unresolved")).toBeInTheDocument();
    expect(screen.getByText(/Voice of Customer\s*\(voc\)/)).toBeInTheDocument();
    expect(
      screen.getByText(
        "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid about the delayed shipment.",
      ),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Related nodes for Ada West" }));
    await waitFor(() => expect(screen.getByText("Related to Ada West")).toBeInTheDocument());
    expect(screen.getByText("Priya Nair (Person)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open related post: Linked post" }));
    await waitFor(() =>
      expect(screen.getByText("The evidence panel should show exactly this text.")).toBeInTheDocument(),
    );
  });

  it("lets post_admin verify pending counterparties against web search", async () => {
    const fetchMock = stubBackend({ admin: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "View post: Public post" }));
    await waitFor(() => expect(screen.getByText("Not yet checked")).toBeInTheDocument());
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

    await userEvent.selectOptions(statusSelect, "closed");

    await waitFor(() => expect(statusSelect).toHaveValue("closed"));
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
    expect(screen.getByText("ticket_created")).toBeInTheDocument();
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
    stubBackend();
    render(<App />);

    await waitFor(() =>
      expect(
        screen.getByText(/no upcoming commitments\. derive one from a post/i),
      ).toBeInTheDocument(),
    );
  });

  it("shows upcoming commitments on the home page calendar and opens the post on click", async () => {
    stubBackend({
      calendarCommitments: [
        {
          issue_ticket_id: "ticket-9",
          post_id: "post-1",
          ticket_status_code: "open",
          ticket_title: "Send the revised delivery schedule",
          assigned_account_id: null,
          due_date: "2026-01-09",
          commitment_summary: "Send the revised delivery schedule",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          post_title: "Public post",
        },
      ],
    });
    render(<App />);

    await waitFor(() =>
      expect(screen.getByText("Send the revised delivery schedule")).toBeInTheDocument(),
    );
    const calendarButton = screen.getByRole("button", { name: /open commitment for: public post/i });
    expect(calendarButton).toHaveTextContent("Public post");
    expect(calendarButton).toHaveTextContent("due 2026-01-09");

    await userEvent.click(calendarButton);

    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
  });
});
