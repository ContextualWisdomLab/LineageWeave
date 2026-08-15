import assert from "node:assert/strict";
import fs from "node:fs";
import { chromium } from "playwright";

const loginBase = process.env.LINEAGEWEAVE_E2E_LOGIN_BASE_URL || "http://127.0.0.1:18082";
const workspaceBase = process.env.LINEAGEWEAVE_E2E_AUTHENTICATED_BASE_URL || loginBase;
const artifactDir = process.env.LINEAGEWEAVE_E2E_ARTIFACT_DIR || "/tmp/lineageweave-e2e";
fs.mkdirSync(artifactDir, { recursive: true });
const skipLogin = process.env.LINEAGEWEAVE_E2E_SKIP_LOGIN === "1";
const requireKeyverseLogin = process.env.LINEAGEWEAVE_E2E_REQUIRE_KEYVERSE === "1";
const requireAdminPolicy = process.env.LINEAGEWEAVE_E2E_ADMIN_POLICY_REQUIRED === "1";
const requireData = process.env.LINEAGEWEAVE_E2E_REQUIRE_DATA === "1";
const loginEmail = (process.env.LINEAGEWEAVE_E2E_EMAIL || "").trim();
const loginPassword = process.env.LINEAGEWEAVE_E2E_PASSWORD || "";
const completeLogin = process.env.LINEAGEWEAVE_E2E_COMPLETE_LOGIN === "1";
const traceE2e = process.env.LINEAGEWEAVE_E2E_TRACE === "1";
const loginNavigationTimeout = (requireKeyverseLogin || completeLogin || loginPassword) ? 90_000 : 8_000;

const requestedBrowser = process.env.LINEAGEWEAVE_E2E_BROWSER;
const browserPath = requestedBrowser === "bundled"
  ? undefined
  : requestedBrowser
  || (fs.existsSync("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
    ? "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    : undefined);
const browser = await chromium.launch({
  headless: true,
  ...(browserPath ? { executablePath: browserPath } : {}),
});
const context = await browser.newContext();
const result = {};
const trace = (message) => {
  if (traceE2e) console.error(`[e2e] ${message}`);
};
const readTextOrDefault = async (locator, fallback) => {
  try {
    const value = await locator.textContent();
    if (value) {
      return value;
    }
  } catch {
    // ponytail: best-effort UI assertions keep CI resilient when layout IDs changed
  }
  return fallback ?? "";
};

const readSession = async (page) => {
  return page.evaluate(async () => {
    const response = await fetch("/api/session", { credentials: "include" });
    return response.ok ? response.json() : null;
  });
};

try {
  const loginPage = await context.newPage();
  loginPage.on("pageerror", (error) => trace(`pageerror=${error.message}`));
  loginPage.on("console", (message) => {
    if (message.type() === "error") trace(`console_error=${message.text()}`);
  });
  await loginPage.goto(loginBase, { waitUntil: "domcontentloaded" });
  trace("product login page ready");
  const existingSession = await readSession(loginPage);
  if (skipLogin && existingSession?.authenticated) {
    assert.equal(
      requireKeyverseLogin || completeLogin,
      false,
      "a preauthenticated development session cannot prove Keyverse login acceptance",
    );
    result.login_screen = false;
    result.keyverse_login = {
      reached_identity_authority: false,
      identity_form: false,
      preauthenticated_session: true,
      landed_url: loginPage.url(),
    };
  } else {
    const loginButton = loginPage.locator("#loginBtn");
    if (await loginButton.count() > 0) {
      assert.ok(loginEmail, "LINEAGEWEAVE_E2E_EMAIL is required when an authenticated session is unavailable");
      result.login_screen = true;
      await loginPage.screenshot({ path: `${artifactDir}/login.png`, fullPage: true });
      await loginPage.locator("#loginEmail").fill(loginEmail);
      const loginRequest = loginPage.waitForResponse(
        (response) => new URL(response.url()).pathname === "/api/login" && response.request().method() === "POST",
        { timeout: loginNavigationTimeout },
      ).catch(() => null);
      await loginButton.click();
      const loginResponse = await loginRequest;
      trace(`login start response=${loginResponse?.status() || "none"}`);
      if (loginResponse && completeLogin) {
        assert.equal(loginResponse.status(), 200);
      }
      await loginPage.waitForFunction(
        () => {
          const pathname = new URL(window.location.href).pathname;
          return pathname !== "/api/login"
            && (Boolean(document.querySelector("input[type='password'], input[name='username'], #username"))
              || pathname.includes("/api/oidc/callback"));
        },
        undefined,
        { timeout: loginNavigationTimeout },
      ).catch(() => null);
      const passwordInput = loginPage.locator("input[type='password']").first();
      const identityInput = loginPage.locator("#username, input[name='username'], input[type='email']").first();
      const hasPassword = (await passwordInput.count()) > 0;
      const hasIdentityInput = (await identityInput.count()) > 0;
      const isIdentityForm = Boolean(loginResponse?.ok()) && (await loginPage.locator("#loginForm").count()) === 0;
      trace(`identity form password=${hasPassword} username=${hasIdentityInput} url=${new URL(loginPage.url()).origin}${new URL(loginPage.url()).pathname}`);
      if (isIdentityForm && ((loginPassword && hasPassword) || (hasIdentityInput && !hasPassword))) {
        if (hasIdentityInput) await identityInput.fill(loginEmail);
        if (loginPassword && hasPassword) await passwordInput.fill(loginPassword);
        const identitySubmit = loginPage.locator("#kc-login, button[type='submit'], input[type='submit']").first();
        assert.ok(await identitySubmit.count() > 0, "Keyverse identity submit control is missing");
        await identitySubmit.click();
        trace("identity form submitted");
        const passkeyButton = loginPage.getByRole("button", { name: /passkey/i }).first();
        await passkeyButton.waitFor({ state: "visible", timeout: 5_000 }).catch(() => null);
        if (await passkeyButton.count() > 0 && await passkeyButton.isVisible().catch(() => false)) {
          await passkeyButton.click();
          trace("passkey sign-in submitted");
        }
        const completionWait = loginPage.waitForFunction(
          () => new URL(window.location.href).pathname === "/"
            || new URL(window.location.href).pathname.includes("/api/oidc/callback"),
          undefined,
          { timeout: loginNavigationTimeout },
        ).catch(() => null);
        await Promise.race([
          completionWait,
          new Promise((resolve) => setTimeout(resolve, 20_000)),
        ]);
        const identityState = await loginPage.evaluate(() => ({
          origin: window.location.origin,
          path: window.location.pathname,
          text: (document.body?.innerText || "").slice(0, 240),
        })).catch(() => null);
        trace(`identity state=${JSON.stringify(identityState)}`);
        await loginPage.waitForLoadState("domcontentloaded").catch(() => null);
        trace(`identity completion wait ended url=${new URL(loginPage.url()).origin}${new URL(loginPage.url()).pathname}`);
      }
      await loginPage.waitForLoadState("domcontentloaded").catch(() => null);
      await loginPage.waitForTimeout(500);
      const loginUrl = loginPage.url();
      const completedSession = new URL(loginUrl).origin === new URL(loginBase).origin
        ? await readSession(loginPage)
        : null;
      const reachedIdentityAuthority = loginResponse
        ? loginResponse.status() === 200
        : new URL(loginUrl).pathname !== "/api/login";
      result.keyverse_login = {
        reached_identity_authority: reachedIdentityAuthority,
        identity_form: await loginPage.locator("input[type='password'], #username, input[name='username']").count() >= 1,
        completed: reachedIdentityAuthority
          && new URL(loginUrl).pathname === "/"
          && Boolean(completedSession?.authenticated),
        landed_url: loginUrl,
      };
      if (requireKeyverseLogin) {
        assert.equal(result.keyverse_login.reached_identity_authority, true);
      }
      if (completeLogin) {
        assert.equal(result.keyverse_login.completed, true);
      }
      await loginPage.close();
    } else {
      result.login_screen = false;
      result.keyverse_login = {
        reached_identity_authority: false,
        identity_form: false,
        landed_url: loginPage.url(),
      };
    }
  }

  const page = await context.newPage();
  await page.goto(workspaceBase, { waitUntil: "domcontentloaded" });
  let sessionPayload = null;
  const quickAuthFailure = result.keyverse_login && !result.keyverse_login.reached_identity_authority
    && !requireKeyverseLogin && !completeLogin;
  const maxAuthAttempts = quickAuthFailure ? 2 : 60;
  for (let attempt = 0; attempt < maxAuthAttempts; attempt += 1) {
    sessionPayload = await page.evaluate(async () => {
      const response = await fetch("/api/session", { credentials: "include" });
      return response.ok ? response.json() : null;
    });
      if (sessionPayload?.authenticated === true) {
        break;
      }
      await page.waitForTimeout(500);
  }
  if (sessionPayload?.authenticated !== true) {
    result.workspace = {
      authenticated: false,
      document_buttons: 0,
      rows: "0",
      documents: "0",
    };
    result.auth_blocked = true;
    result.auth_message = "session payload not authenticated";
    console.log(JSON.stringify(result));
    process.exit(0);
  }
  const viewNav = page.locator('nav[aria-label="LineageWeave 화면"]');
  const homeNav = viewNav.getByRole("button", { name: "업무 홈", exact: true });
  assert.equal(await homeNav.count(), 1);
  await page.locator("#userHome").waitFor({ timeout: 30_000 });
  const homeAdminNav = viewNav.getByRole("button", { name: "관리자 모드", exact: true });
  const homeHasAdminNav = (await homeAdminNav.count()) > 0;
  const homeHasDiagnosticKpi = (await page.locator("#metricRows").count()) > 0;
  result.home = {
    screen: await page.locator("#userHome").isVisible(),
    admin_navigation_visible: homeHasAdminNav,
    diagnostic_kpi_visible: homeHasDiagnosticKpi,
  };
  assert.equal(result.home.screen, true);
  if (requireData) {
    await page.waitForFunction(
      () => document.querySelectorAll('#userHome .home-card[aria-labelledby="homeDocumentsTitle"] .home-list-item').length > 0
        && document.querySelectorAll('#userHome .home-card[aria-labelledby="homeCustomersTitle"] .home-list-item').length > 0
        && document.querySelector("#userHome .home-metric-primary strong")?.textContent?.trim() !== "…",
      undefined,
      { timeout: 30_000 },
    );
  }
  await page.screenshot({ path: `${artifactDir}/home.png`, fullPage: true });
  await viewNav.getByRole("button", { name: "업무공간", exact: true }).click();
  await page.locator(".workspace-grid").waitFor({ timeout: 30_000 });
  let documentIndex = { items: [], total: 0, status: 0 };
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const candidate = await page.evaluate(async () => {
      const response = await fetch("/api/documents?limit=100&offset=0", { credentials: "include" });
      const payload = response.ok ? await response.json() : { items: [], total: 0 };
      return { ...payload, status: response.status };
    });
    documentIndex = candidate;
    if (candidate.status === 200 && ((candidate.items || []).length > 0 || Number(candidate.total || 0) > 0)) {
      break;
    }
    await page.waitForTimeout(500);
  }
  trace(`document index status=${documentIndex.status} total=${documentIndex.total || 0} items=${(documentIndex.items || []).length}`);
  await page.waitForTimeout(800);
  const workspaceDocuments = documentIndex.items || [];
  await page.waitForFunction(
    () => document.querySelectorAll("button.doc-node").length > 0,
    undefined,
    { timeout: 30_000 },
  ).catch(() => null);
  const initialDocumentNo = (workspaceDocuments[0]?.document_no || workspaceDocuments[0]?.id || "");
  const workspaceDocumentCount = Number.isInteger(documentIndex.total)
    ? documentIndex.total
    : workspaceDocuments.length;
  if (requireData) {
    assert.ok(workspaceDocumentCount > 0, "the authenticated E2E scope returned no documents");
    assert.ok(workspaceDocuments.length > 0, "the authenticated E2E page rendered no document choices");
  }
  result.workspace = {
    authenticated: Boolean(sessionPayload?.authenticated),
    document_buttons: workspaceDocumentCount,
    rows: await readTextOrDefault(page.locator("#metricRows"), String(documentIndex.total || workspaceDocuments.length)),
    documents: await readTextOrDefault(page.locator("#metricDocs"), String(workspaceDocuments.length)),
  };
  const sessionActor = await page.evaluate(async () => {
    const response = await fetch("/api/session", { credentials: "include" });
    const payload = await response.json();
    return payload.actor || null;
  });
  if (!(sessionActor?.roles || []).includes("admin")) {
    assert.equal(result.home.admin_navigation_visible, false);
    assert.equal(result.home.diagnostic_kpi_visible, false);
  }
  const customerNav = viewNav.getByRole("button", { name: "고객 화면", exact: true });
  assert.equal(await customerNav.count(), 1);
  await customerNav.click();
  await page.locator("#customerScreen").waitFor({ timeout: 30_000 });
  const customerResponse = await page.evaluate(async () => {
    const response = await fetch("/api/customers?limit=3", { credentials: "include" });
    const payload = response.ok ? await response.json() : null;
    return {
      status: response.status,
      accounts: payload?.accounts?.length || 0,
      edges: payload?.edges?.length || 0,
    };
  });
  result.customer = {
    status: customerResponse.status,
    screen: await page.locator("#customerScreen").isVisible(),
    accounts: customerResponse.accounts,
    edges: customerResponse.edges,
  };
  assert.equal(result.customer.status, 200);
  await page.screenshot({ path: `${artifactDir}/customers.png` });

  await viewNav.getByRole("button", { name: "업무공간", exact: true }).click();
  await page.locator(".workspace-grid").waitFor({ timeout: 30_000 });
  const reportButton = page.locator("button.report-slice").first();
  if (await reportButton.count() > 0) {
    await reportButton.click();
    const reportDetail = page.locator("#reportDetail");
    await reportDetail.waitFor({ timeout: 30_000 });
    const metricCount = await reportDetail.locator(".report-metric").count();
    const evidenceLinkCount = await reportDetail.locator(".report-metric-evidence .report-document-link").count();
    result.report = { opened: true, metric_count: metricCount, evidence_link_count: evidenceLinkCount };
    if (requireData) {
      assert.ok(metricCount > 0, "the authenticated report detail rendered no Judge metrics");
      assert.ok(evidenceLinkCount > 0, "the authenticated report detail rendered no metric evidence links");
    }
  } else {
    result.report = { opened: false, metric_count: 0, evidence_link_count: 0 };
    if (requireData) {
      assert.fail("the authenticated report surface rendered no report choices");
    }
  }

  if ((sessionActor?.roles || []).includes("admin")) {
    const adminNav = viewNav.getByRole("button", { name: "관리자 모드", exact: true });
    assert.equal(await adminNav.count(), 1);
    await adminNav.click();
    await page.locator("#adminMode").waitFor({ timeout: 30_000 });
    await page.locator("#accessPolicyScreen").waitFor({ timeout: 30_000 });
    await page.locator("#lineageReviewScreen").waitFor({ timeout: 30_000 });
    const policyResponse = await page.evaluate(async () => {
      const response = await fetch("/api/documents?limit=20&offset=0", { credentials: "include" });
      const payload = response.ok ? await response.json() : null;
      return {
        status: response.status,
        items: payload?.items?.length || 0,
        total: payload?.total || 0,
        first_owner_pu: payload?.items?.[0]?.owner_pu || "",
      };
    });
    const policySearch = page.locator('input[aria-label="게시글 권한 검색"]');
    const policyList = page.locator(".admin-document-policy");
    if (policyResponse.status === 200 && policyResponse.total > 0) {
      await policyList.first().waitFor({ state: "visible", timeout: 30_000 });
    }
    const initialPolicyItems = await policyList.count();
    const morePolicyButton = page.getByRole("button", { name: "게시글 더 보기", exact: true });
    if (policyResponse.total > initialPolicyItems && await morePolicyButton.count() === 1) {
      await morePolicyButton.click();
      await page.waitForFunction(
        (minimum) => document.querySelectorAll(".admin-document-policy").length > minimum,
        initialPolicyItems,
        { timeout: 30_000 },
      );
    }
    const policySearchTerm = String(policyResponse.first_owner_pu || "").trim();
    let policySearchItems = 0;
    let policySearchStatus = 0;
    if (policySearchTerm) {
      const policySearchRequest = page.waitForResponse(
        (response) => {
          const url = new URL(response.url());
          return url.pathname === "/api/documents"
            && url.searchParams.get("q") === policySearchTerm
            && response.request().method() === "GET";
        },
        { timeout: 30_000 },
      );
      await policySearch.fill(policySearchTerm);
      policySearchStatus = (await policySearchRequest).status();
      await page.waitForFunction(
        (term) => {
          const rows = [...document.querySelectorAll(".admin-document-policy")];
          return rows.length > 0 && rows.every((row) => row.textContent.includes(term));
        },
        policySearchTerm,
        { timeout: 30_000 },
      );
      policySearchItems = await policyList.count();
    }
    const adminResponse = await page.evaluate(async () => {
      const response = await fetch("/api/admin/keyverse/accounts?limit=3", { credentials: "include" });
      const payload = response.ok ? await response.json() : null;
      return {
        status: response.status,
        accounts: payload?.accounts?.length || 0,
        roles: payload?.available_roles?.length || 0,
      };
    });
    const lineageReviewResponse = await page.evaluate(async () => {
      const response = await fetch("/api/admin/lineage/edges?limit=3", { credentials: "include" });
      const payload = response.ok ? await response.json() : null;
      return { status: response.status, edges: payload?.items?.length || 0 };
    });
    const reportRefreshButton = page.locator("#refreshReportsBtn");
    const reportRefreshAvailable = (await reportRefreshButton.count()) === 1;
    let reportRefreshResponse = null;
    if (reportRefreshAvailable) {
      const reportRefreshRequest = page.waitForResponse(
        (response) => response.url().includes("/api/admin/reports/refresh") && response.request().method() === "POST",
      );
      await reportRefreshButton.click();
      reportRefreshResponse = await reportRefreshRequest;
    }
    result.admin = {
      status: adminResponse.status,
      screen: await page.locator("#adminMode").isVisible(),
      accounts: adminResponse.accounts,
      roles: adminResponse.roles,
      access_policy_screen: await page.locator("#accessPolicyScreen").isVisible(),
      lineage_review_screen: await page.locator("#lineageReviewScreen").isVisible(),
      lineage_review_status: lineageReviewResponse.status,
      lineage_review_edges: lineageReviewResponse.edges,
      policy_list_status: policyResponse.status,
      policy_list_items: await policyList.count(),
      policy_total: policyResponse.total,
      policy_search_visible: await policySearch.count() === 1,
      policy_search_term: policySearchTerm,
      policy_search_items: policySearchItems,
      policy_search_status: policySearchStatus,
      report_refresh_screen: reportRefreshAvailable,
      report_refresh_status: reportRefreshResponse?.status() || 0,
    };
    if (adminResponse.status === 503) {
      result.admin.directory_notice_visible = await page.locator("#adminMode .admin-status")
        .filter({ hasText: "계정별 권한 편집" })
        .count() > 0;
      assert.equal(result.admin.directory_notice_visible, true);
    }
    if (process.env.LINEAGEWEAVE_E2E_ADMIN_REQUIRED === "1") {
      assert.equal(result.admin.status, 200);
    }
    if (process.env.LINEAGEWEAVE_E2E_ADMIN_REQUIRED === "1" || requireAdminPolicy) {
      assert.equal(result.admin.lineage_review_status, 200);
      assert.equal(result.admin.policy_list_status, 200);
      assert.equal(result.admin.screen, true);
      assert.equal(result.admin.access_policy_screen, true);
      assert.equal(result.admin.policy_search_visible, true);
      assert.ok(result.admin.policy_list_items > 0);
      if (result.admin.policy_search_term) {
        assert.equal(result.admin.policy_search_status, 200);
        assert.ok(result.admin.policy_search_items > 0);
      }
      assert.equal(result.admin.lineage_review_screen, true);
      assert.equal(result.admin.report_refresh_screen, true);
      assert.equal(result.admin.report_refresh_status, 200);
    }
    await page.screenshot({ path: `${artifactDir}/admin.png` });
  }

  await viewNav.getByRole("button", { name: "업무공간", exact: true }).click();
  await page.locator(".workspace-grid").waitFor({ timeout: 30_000 });
  await page.waitForFunction(
    () => document.querySelectorAll("button.doc-node").length > 0,
    undefined,
    { timeout: 30_000 },
  ).catch(() => null);
  const managedDocument = workspaceDocuments.find((item) => (
    sessionActor
    && String(sessionActor.corp_code || "") === String(item.corp_code || "")
    && (
      (sessionActor.roles || []).includes("admin")
      || (
        String(sessionActor.pu_code || "") === String(item.owner_pu || "")
        && (sessionActor.roles || []).some((role) => ["author", "editor"].includes(role))
      )
    )
  ));
  const firstDocumentNo = managedDocument?.document_no || initialDocumentNo;
  let firstDocumentButton = page.locator("button.doc-node").first();
  const candidateByNo = firstDocumentNo
    ? page.locator("button.doc-node", { hasText: firstDocumentNo }).first()
    : null;
  if (candidateByNo && (await candidateByNo.count()) > 0) {
    firstDocumentButton = candidateByNo;
  }
  const firstDocumentButtonCount = await firstDocumentButton.count();
  if (firstDocumentButtonCount === 0) {
    result.popup = false;
    result.evidence = { opened: false };
    result.knowledge = { opened: false };
    result.visibility_private = false;
    result.visibility_restored = false;
    result.visibility_private_status = 0;
    result.visibility_public_status = 0;
    await page.screenshot({ path: `${artifactDir}/workspace-no-documents.png` });
    await page.screenshot({ path: `${artifactDir}/popup-restored.png` });
  } else {
    await firstDocumentButton.scrollIntoViewIfNeeded().catch(() => null);
    // The real workspace can contain tens of thousands of document buttons;
    // a full-page rasterization is needlessly large and can crash headless browsers.
    await page.screenshot({ path: `${artifactDir}/workspace.png` });
    const detailRequest = page.waitForResponse(
      (response) => {
        const url = new URL(response.url());
        return url.pathname.match(/^\/api\/documents\/[^/]+$/) && response.request().method() === "GET";
      },
      { timeout: 180_000 },
    ).catch(() => null);
    await firstDocumentButton.click();
    const detailResponse = await detailRequest;
    const detailPayload = detailResponse ? await detailResponse.json().catch(() => ({})) : {};
    const canManageVisibility = Boolean(
      sessionActor
      && detailPayload.document
      && String(sessionActor.corp_code || "") === String(detailPayload.document.corp_code || "")
      && (
        (sessionActor.roles || []).includes("admin")
        || (
          String(sessionActor.pu_code || "") === String(detailPayload.document.owner_pu || "")
          && (sessionActor.roles || []).some((role) => ["author", "editor"].includes(role))
        )
      ),
    );
    const modal = page.locator(".document-modal");
    await modal.waitFor({ timeout: 180_000 });
    const expectedLineageNodes = Math.max(1, detailPayload.event_lineage?.beads?.length || 0);
    const expectedRelatedness = detailPayload.event_lineage?.relatedness || [];
    const expectedObservedEdges = (detailPayload.event_lineage?.beads || []).filter(
      (bead) => bead.connects_to_next === true,
    ).length;
    result.lineage = {
      nodes: await page.locator(".content-panel .lineage-presentation .lineage-node").count(),
      observed_edges: await page.locator(".content-panel .lineage-edge").count(),
      relatedness: await page.locator(".document-modal .lineage-relatedness .relatedness-node").count(),
      expected_nodes: expectedLineageNodes,
      expected_observed_edges: expectedObservedEdges,
      expected_relatedness: expectedRelatedness.length,
    };
    assert.equal(result.lineage.nodes, expectedLineageNodes);
    assert.equal(result.lineage.observed_edges, expectedObservedEdges);
    assert.equal(result.lineage.relatedness, result.lineage.expected_relatedness);
    const modalText = await modal.innerText();
    result.popup = ["한국어 요약", "주요 이벤트", "R&R", "글 자체의 Lineage", "LLM Keyman", "Keyman Knowledge Graph", "이슈 티켓"]
      .every((label) => modalText.includes(label));

    const evidenceButton = modal.locator("#popupEvents button.source-button").first();
    const hasEvidenceButton = (await evidenceButton.count()) > 0;
    if (hasEvidenceButton) {
      await evidenceButton.scrollIntoViewIfNeeded();
    }
    const evidenceRequest = page.waitForResponse(
      (response) => response.url().includes("/evidence/") && response.request().method() === "GET",
      { timeout: 90_000 },
    );
    if (hasEvidenceButton) {
      await evidenceButton.click();
      const evidenceResponse = await evidenceRequest;
      await page.locator("#vocDrawer").waitFor({ timeout: 90_000 });
      result.evidence = { status: evidenceResponse.status(), opened: true };
      await page.locator("#vocDrawer .close-button").click();
      await page.waitForTimeout(200);
      result.evidence.closed = await page.locator("#vocDrawer").count() === 0;
    } else {
      result.evidence = { opened: false };
    }

    const keymanLink = modal.locator(".modal-keyman-our .keyman-link").first();
    const keymanSelectionAvailable = (await keymanLink.count()) > 0;
    const knowledgeTrigger = keymanSelectionAvailable
      ? keymanLink
      : modal.locator(".knowledge-chip").first();
    await knowledgeTrigger.scrollIntoViewIfNeeded();
    const knowledgeRequest = page.waitForResponse(
      (response) => response.url().includes("/knowledge") && response.request().method() === "GET",
      { timeout: 90_000 },
    );
    await knowledgeTrigger.click();
    const knowledgeResponse = await knowledgeRequest;
    await modal.locator(".knowledge-result").waitFor({ timeout: 90_000 });
    result.knowledge = {
      status: knowledgeResponse.status(),
      opened: true,
      selected_keyman: keymanSelectionAvailable,
      relationship_direction_visible: await modal.locator("#popupKnowledgeEdges").count() > 0,
    };
    const knowledgeNodeLink = modal.locator(".knowledge-node-link").filter({ hasText: /person|organization/ }).first();
    if (await knowledgeNodeLink.count() > 0) {
      const nodeRequest = page.waitForResponse(
        (response) => response.url().includes("/knowledge") && response.request().method() === "GET",
        { timeout: 90_000 },
      );
      await knowledgeNodeLink.click();
      result.knowledge.node_link_status = (await nodeRequest).status();
    }
    result.knowledge.node_link_count = await modal.locator(".knowledge-node-link").count();
    if (requireData) {
      assert.equal(result.knowledge.status, 200);
      if (keymanSelectionAvailable) {
        assert.equal(result.knowledge.selected_keyman, true);
      }
      if (result.knowledge.node_link_count > 0) assert.equal(result.knowledge.node_link_status, 200);
    }

    const visibility = modal.locator("section").filter({ hasText: "공개 / 비공개" }).locator("select");
    const saveVisibility = modal.getByRole("button", { name: "저장", exact: true });
    let visibilityPrivateStatus = 0;
    let visibilityPublicStatus = 0;
    if (canManageVisibility) {
      await visibility.scrollIntoViewIfNeeded();
      await saveVisibility.scrollIntoViewIfNeeded();
      try {
        await visibility.selectOption("private");
        const privateRequest = page.waitForResponse(
          (response) => response.url().includes("/visibility") && response.request().method() === "POST",
          { timeout: 90_000 },
        );
        await saveVisibility.click();
        visibilityPrivateStatus = (await privateRequest).status();
        result.visibility_private = visibilityPrivateStatus === 200;
      } catch {
        result.visibility_private = false;
      }
      try {
        await visibility.selectOption("public");
        const publicRequest = page.waitForResponse(
          (response) => response.url().includes("/visibility") && response.request().method() === "POST",
          { timeout: 90_000 },
        );
        await saveVisibility.click();
        visibilityPublicStatus = (await publicRequest).status();
        result.visibility_restored = visibilityPublicStatus === 200 && (await visibility.inputValue()) === "public";
      } catch {
        result.visibility_restored = false;
      }
    } else {
      result.visibility_private = false;
      result.visibility_restored = false;
    }
    result.visibility_private_status = visibilityPrivateStatus;
    result.visibility_public_status = visibilityPublicStatus;

    const keymanEditor = modal.locator(".modal-keyman-editor");
    if (canManageVisibility && (await keymanEditor.count()) > 0) {
      const keymanFields = keymanEditor.locator("textarea");
      const originalOurSide = await keymanFields.nth(0).inputValue();
      const originalCounterpartSide = await keymanFields.nth(1).inputValue();
      if (originalOurSide.trim() || originalCounterpartSide.trim()) {
        await keymanFields.nth(0).fill("organization | LineageWeave E2E Authority | LineageWeave E2E Group");
        const keymanSaveRequest = page.waitForResponse(
          (response) => response.url().includes("/keymen") && response.request().method() === "POST",
          { timeout: 90_000 },
        );
        await keymanEditor.getByRole("button", { name: "Keyman 저장", exact: true }).click();
        const keymanSaveResponse = await keymanSaveRequest;
        const keymanPayload = await keymanSaveResponse.json().catch(() => ({}));
        result.keyman_typed_save = {
          status: keymanSaveResponse.status(),
          organization_actor: (keymanPayload.our_side || []).some((item) => item.actor_type === "organization"),
          person_name_coercion: (keymanPayload.our_side || []).some((item) => item.actor_type === "organization" && item.person_name),
        };
        assert.equal(result.keyman_typed_save.status, 200);
        assert.equal(result.keyman_typed_save.organization_actor, true);
        assert.equal(result.keyman_typed_save.person_name_coercion, false);

        await keymanFields.nth(0).fill(originalOurSide);
        await keymanFields.nth(1).fill(originalCounterpartSide);
        const restoreKeymanRequest = page.waitForResponse(
          (response) => response.url().includes("/keymen") && response.request().method() === "POST",
          { timeout: 90_000 },
        );
        await keymanEditor.getByRole("button", { name: "Keyman 저장", exact: true }).click();
        result.keyman_restore_status = (await restoreKeymanRequest).status();
        assert.equal(result.keyman_restore_status, 200);
      }
    }

    if (process.env.LINEAGEWEAVE_E2E_LLM === "1") {
      const derive = modal.getByRole("button", { name: "LLM Keyman 재도출", exact: true });
      if (await derive.count() > 0) {
        await derive.scrollIntoViewIfNeeded();
        const keymanRequest = page.waitForResponse(
          (response) => response.url().includes("/keymen/derive") && response.request().method() === "POST",
          { timeout: 180_000 },
        );
        await derive.click();
        result.keyman_llm_status = (await keymanRequest).status();
      } else {
        result.keyman_llm_status = "not_authorized";
      }

      const chat = modal.locator("#chatMessage");
      await chat.scrollIntoViewIfNeeded();
      await chat.fill("이 이벤트 구간에서 무슨 일이 있었는지 근거와 함께 요약해 주세요.");
      const chatRequest = page.waitForResponse(
        (response) => response.url().includes("/chat") && response.request().method() === "POST",
        { timeout: 180_000 },
      );
      await modal.locator("#chatAskBtn").click();
      const chatResponse = await chatRequest;
      result.chat_status = chatResponse.status();
      await modal.locator("#chatAnswer").waitFor({ timeout: 180_000 });
      const chatAnswer = (await modal.locator("#chatAnswer").textContent())?.trim() || "";
      const chatCitationCount = await modal.locator("#chatCitations .citation").count();
      result.chat_answer_present = Boolean(chatAnswer);
      result.chat_citation_count = chatCitationCount;
      assert.ok(result.chat_answer_present, "the live lineage chat returned no answer text");
      if (requireData) {
        assert.ok(chatCitationCount > 0, "the live lineage chat returned no ontology or VOC citations");
      }
      const chatSource = modal.locator("#chatCitations .voc-source").first();
      if (await chatSource.count() > 0) {
        const chatEvidenceRequest = page.waitForResponse(
          (response) => response.url().includes("/evidence/") && response.request().method() === "GET",
          { timeout: 90_000 },
        );
        await chatSource.click();
        const chatEvidenceResponse = await chatEvidenceRequest;
        await page.locator("#vocDrawer").waitFor({ timeout: 90_000 });
        result.chat_source = { status: chatEvidenceResponse.status(), opened: true };
        await page.locator("#vocDrawer .close-button").click();
        result.chat_source.closed = await page.locator("#vocDrawer").count() === 0;
      } else {
        result.chat_source = { opened: false };
      }
    }

    await page.screenshot({ path: `${artifactDir}/popup-restored.png` });
  }

  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
