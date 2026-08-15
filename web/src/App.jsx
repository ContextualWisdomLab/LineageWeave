import { useEffect, useRef, useState } from "react";
import {
  canPreviewAsset,
  customerTreeRows,
  emailValidationMessage,
  formatNumber,
  isInspectableAsset,
  knowledgeEdgeRows,
  lineageRelationLabel,
  parseSide,
  partitionLineageBeads,
  semanticValue,
  sideLabel,
  sideRows,
  sideText,
} from "./ui-model.js";

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
    headers: {
      accept: "application/json",
      ...(options.body ? { "content-type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let value = {};
  try {
    value = text ? JSON.parse(text) : {};
  } catch {
    value = { error: text || "invalid_response" };
  }
  if (!response.ok) {
    const error = new Error(value.error || `request_failed_${response.status}`);
    error.status = response.status;
    throw error;
  }
  return value;
}

function keymanSourceLabel(source) {
  return {
    llm: "자동 도출",
    user_override: "사용자 관리",
    unavailable: "도출 보류",
    pending: "도출 대기",
  }[source] || "확인 필요";
}

function keymanStatusLabel(status) {
  return {
    orchestrator: "자동 분석 완료",
    managed: "사용자 관리 완료",
    unavailable: "도출 보류",
    not_run: "아직 분석하지 않음",
  }[status] || "확인 필요";
}

function reportPeriodLabel(periodKind) {
  return { weekly: "주간", monthly: "월간" }[periodKind] || "기간";
}

function reportSliceLabel(sliceKind) {
  return { pu: "PU", team: "팀", project: "프로젝트" }[sliceKind] || "업무 범위";
}

function reportVerdictLabel(verdict) {
  return {
    pass: "검토 완료",
    fail: "추가 확인",
    abstain: "판정 보류",
    unavailable: "평가 대기",
  }[verdict] || "평가 대기";
}

function reportLinkingLabel(method) {
  return {
    fipc: "문항 연결",
    cat: "적응형 평가",
    linked: "연결 점수",
  }[String(method || "").toLowerCase()] || "연결 점수";
}

function reportJudgeSourceLabel(source) {
  return { llm_judge: "자동 평가", llm: "자동 평가" }[String(source || "").toLowerCase()] || "평가 출처 확인";
}

function reportBusinessTitle(report) {
  const sliceLabel = String(report?.slice_label || "").trim();
  if (sliceLabel) return `${reportPeriodLabel(report?.period_kind)} ${reportSliceLabel(report?.slice_kind)} · ${sliceLabel}`;
  const title = String(report?.title || "").trim();
  if (title && !/^(weekly|monthly)\s+(pu|team|project)\b/i.test(title)) return title;
  return `${reportPeriodLabel(report?.period_kind)} ${reportSliceLabel(report?.slice_kind)} 보고서`;
}

function customerTierLabel(tier) {
  return { group: "그룹", national: "법인", hq: "본사", plant: "사업장", team: "팀" }[tier] || "조직";
}

function customerRelationSourceLabel(source) {
  return {
    llm: "자동 분석",
    observed: "관측 근거",
    user_override: "관리자 확인",
  }[String(source || "").toLowerCase()] || "근거 연결";
}

export default function App() {
  const documentDialog = useRef(null);
  const emailInput = useRef(null);
  const [session, setSession] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [summary, setSummary] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [documentLoadState, setDocumentLoadState] = useState("loading");
  const [semanticSearch, setSemanticSearch] = useState(null);
  const [selectedNo, setSelectedNo] = useState("");
  const [detail, setDetail] = useState(null);
  const [content, setContent] = useState(null);
  const [knowledge, setKnowledge] = useState(null);
  const [semanticRelated, setSemanticRelated] = useState(null);
  const [knowledgeDepth, setKnowledgeDepth] = useState("");
  const [evidence, setEvidence] = useState(null);
  const [chat, setChat] = useState(null);
  const [inferenceVerification, setInferenceVerification] = useState(null);
  const [organizationAlias, setOrganizationAlias] = useState("");
  const [aliasResolution, setAliasResolution] = useState(null);
  const [message, setMessage] = useState("이 이벤트 구간에서 무슨 일이 있었나?");
  const [keymanForm, setKeymanForm] = useState({ our: "", counterpart: "" });
  const [ticketTitle, setTicketTitle] = useState("");
  const [visibility, setVisibility] = useState("public");
  const [filter, setFilter] = useState("");
  const [imageQuery, setImageQuery] = useState("");
  const [imageResults, setImageResults] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [emailAddress, setEmailAddress] = useState("");
  const [emailError, setEmailError] = useState("");
  const [activeView, setActiveView] = useState("home");
  const [customerSurface, setCustomerSurface] = useState(null);
  const [customerLoadState, setCustomerLoadState] = useState("loading");
  const [customerFilter, setCustomerFilter] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [adminAccounts, setAdminAccounts] = useState([]);
  const [adminRoles, setAdminRoles] = useState([]);
  const [adminFilter, setAdminFilter] = useState("");
  const [selectedAdminId, setSelectedAdminId] = useState("");
  const [adminForm, setAdminForm] = useState({ org: "", workspace: "", roles: [] });
  const [adminStatus, setAdminStatus] = useState("");
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminDocuments, setAdminDocuments] = useState([]);
  const [adminDocumentTotal, setAdminDocumentTotal] = useState(0);
  const [adminDocumentLoadState, setAdminDocumentLoadState] = useState("idle");
  const [adminDocumentFilter, setAdminDocumentFilter] = useState("");
  const [lineageReviewEdges, setLineageReviewEdges] = useState([]);
  const [lineageFilter, setLineageFilter] = useState("");
  const [lineageReviewStatus, setLineageReviewStatus] = useState("");
  const [lineageReviewBusy, setLineageReviewBusy] = useState(false);
  const [enrichmentStatus, setEnrichmentStatus] = useState(null);
  const [enrichmentTask, setEnrichmentTask] = useState("all");
  const [enrichmentLimit, setEnrichmentLimit] = useState("16");
  const [enrichmentStatusMessage, setEnrichmentStatusMessage] = useState("");
  const [enrichmentBusy, setEnrichmentBusy] = useState(false);
  const [reportRefreshStatus, setReportRefreshStatus] = useState("");
  const [reportRefreshBusy, setReportRefreshBusy] = useState(false);
  const [teppStatus, setTeppStatus] = useState(null);
  const [teppSnapshotId, setTeppSnapshotId] = useState("");
  const [teppKnowledgeCutoff, setTeppKnowledgeCutoff] = useState("");
  const [teppIdempotencyKey, setTeppIdempotencyKey] = useState("");
  const [teppStatusMessage, setTeppStatusMessage] = useState("");
  const [teppBusy, setTeppBusy] = useState(false);
  const canManage = (session?.roles || []).some((role) => ["author", "editor", "admin"].includes(role));
  const canAdmin = (session?.roles || []).includes("admin");

  useEffect(() => {
    api("/api/session")
      .then((value) => setSession(value.actor))
      .catch(() => setSession(null))
      .finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    if (!session) return;
    setError("");
    Promise.all([
      api("/api/analytics"),
      api("/api/queue/health").catch(() => null),
    ])
      .then(([analytics, queueHealth]) => {
        setSummary({ ...analytics, queue_health: queueHealth });
        return api("/api/reports")
          .then((reports) => {
            setSummary((current) => ({
              ...current,
              period_reports: reports.reports || current?.period_reports || [],
              factor_definitions: reports.factor_definitions || current?.factor_definitions || [],
            }));
          })
          .catch(() => null);
      })
      .catch((caught) => setError(caught.message));
  }, [session]);

  useEffect(() => {
    if (!session) return undefined;
    let current = true;
    setCustomerLoadState("loading");
    const timer = window.setTimeout(() => {
      const query = customerFilter.trim() ? `&q=${encodeURIComponent(customerFilter.trim())}` : "";
      api(`/api/customers?limit=100${query}`)
        .then((value) => {
          if (!current) return;
          setCustomerSurface(value);
          setSelectedCustomer((selected) => (
            value.accounts?.some((account) => account.account_name === selected)
              ? selected
              : value.accounts?.[0]?.account_name || ""
          ));
          setCustomerLoadState("ready");
        })
        .catch((caught) => {
          if (current) {
            setCustomerLoadState("error");
            setError(caught.message);
          }
        });
    }, 250);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [session, customerFilter]);

  useEffect(() => {
    if (!session || !canAdmin) {
      setAdminAccounts([]);
      setAdminRoles([]);
      setSelectedAdminId("");
      setAdminForm({ org: "", workspace: "", roles: [] });
      return undefined;
    }
    let current = true;
    const timer = window.setTimeout(() => {
      const query = adminFilter.trim() ? `&q=${encodeURIComponent(adminFilter.trim())}` : "";
      api(`/api/admin/keyverse/accounts?limit=50${query}`)
        .then((value) => {
          if (!current) return;
          setAdminAccounts(value.accounts || []);
          setAdminRoles(value.available_roles || []);
          setSelectedAdminId((selected) => (
            value.accounts?.some((account) => account.account_id === selected)
              ? selected
              : value.accounts?.[0]?.account_id || ""
          ));
          setAdminStatus("");
        })
        .catch((caught) => {
          if (current) setAdminStatus("현재 운영 Keyverse 계정 원장이 연결되지 않아 계정별 권한 편집을 사용할 수 없습니다. 게시글 권한 통제와 Lineage 검토는 계속 사용할 수 있습니다.");
        });
    }, 250);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [session, canAdmin, adminFilter]);

  useEffect(() => {
    if (!session || !canAdmin || activeView !== "admin") {
      setAdminDocuments([]);
      setAdminDocumentTotal(0);
      setAdminDocumentLoadState("idle");
      return undefined;
    }
    let current = true;
    setAdminDocumentLoadState("loading");
    const timer = window.setTimeout(() => {
      const query = adminDocumentFilter.trim() ? `&q=${encodeURIComponent(adminDocumentFilter.trim())}` : "";
      api(`/api/documents?limit=20&offset=0${query}`)
        .then((value) => {
          if (!current) return;
          setAdminDocuments(value.items || []);
          setAdminDocumentTotal(value.total || 0);
          setAdminDocumentLoadState("ready");
        })
        .catch((caught) => {
          if (current) {
            setAdminDocuments([]);
            setAdminDocumentTotal(0);
            setAdminDocumentLoadState("error");
            setAdminStatus(`게시글 권한 목록을 불러오지 못했습니다: ${caught.message}`);
          }
        });
    }, 250);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [session, canAdmin, activeView, adminDocumentFilter]);

  useEffect(() => {
    if (!session || !canAdmin) {
      setLineageReviewEdges([]);
      setLineageReviewStatus("");
      return undefined;
    }
    let current = true;
    const timer = window.setTimeout(() => {
      const query = lineageFilter.trim() ? `&q=${encodeURIComponent(lineageFilter.trim())}` : "";
      api(`/api/admin/lineage/edges?limit=100${query}`)
        .then((value) => {
          if (!current) return;
          setLineageReviewEdges(value.items || []);
          setLineageReviewStatus("");
        })
        .catch((caught) => {
          if (current) setLineageReviewStatus(`Lineage 검토 목록을 불러오지 못했습니다: ${caught.message}`);
        });
    }, 250);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [session, canAdmin, lineageFilter]);

  useEffect(() => {
    if (!session || !canAdmin) {
      setEnrichmentStatus(null);
      setEnrichmentStatusMessage("");
      return undefined;
    }
    let current = true;
    const load = () => api("/api/admin/enrichment/status")
      .then((value) => {
        if (current) setEnrichmentStatus(value);
      })
      .catch((caught) => {
        if (current) setEnrichmentStatusMessage(`LLM 분석 상태를 불러오지 못했습니다: ${caught.message}`);
      });
    void load();
    const timer = window.setInterval(load, 5000);
    return () => {
      current = false;
      window.clearInterval(timer);
    };
  }, [session, canAdmin]);

  useEffect(() => {
    if (!session || !canAdmin) {
      setTeppStatus(null);
      setTeppStatusMessage("");
      return undefined;
    }
    let current = true;
    const load = () => api("/api/admin/tepp/status")
      .then((value) => {
        if (current) setTeppStatus(value);
      })
      .catch((caught) => {
        if (current) setTeppStatusMessage(`TEPP 상태를 불러오지 못했습니다: ${caught.message}`);
      });
    void load();
    const timer = window.setInterval(load, 5000);
    return () => {
      current = false;
      window.clearInterval(timer);
    };
  }, [session, canAdmin]);

  useEffect(() => {
    if (!session) return undefined;
    let current = true;
    setSemanticSearch(null);
    setDocumentLoadState("loading");
    const timer = window.setTimeout(() => {
      const query = filter.trim() ? `&q=${encodeURIComponent(filter.trim())}` : "";
      api(`/api/documents?limit=100&offset=0${query}`)
        .then((index) => {
          if (!current) return;
          setDocuments(index.items || []);
          setTotalDocuments(index.total || 0);
          setDocumentLoadState("ready");
        })
        .catch((caught) => {
          if (current) {
            setDocumentLoadState("error");
            setError(caught.message);
          }
        });
    }, 250);
    return () => {
      current = false;
      window.clearTimeout(timer);
    };
  }, [session, filter]);

  useEffect(() => {
    if (!session || !selectedNo) return;
    setBusy(true);
    setError("");
    api(`/api/documents/${encodeURIComponent(selectedNo)}`)
      .then((documentDetail) => {
        setDetail(documentDetail);
        setVisibility(documentDetail.document.visibility || "public");
        setKeymanForm({
          our: sideText(documentDetail.document.keyman_our_side),
          counterpart: sideText(documentDetail.document.keyman_counterpart_side),
        });
        setContent(null);
        setKnowledge(null);
        setSemanticRelated(null);
        setEvidence(null);
        setChat(null);
        setInferenceVerification(null);
        setOrganizationAlias("");
        setAliasResolution(null);
        setBusy(false);
        void api(`/api/documents/${encodeURIComponent(selectedNo)}/content`)
          .then(setContent)
          .catch(() => setContent({ document_no: selectedNo, assets: [], asset_count: 0, inspections: [] }));
      })
      .catch((caught) => setError(caught.message))
      .finally(() => setBusy(false));
  }, [session, selectedNo]);

  const documentRows = semanticSearch?.items || documents;
  const visibleDocumentTotal = semanticSearch ? documentRows.length : totalDocuments;

  const selectedDocument = detail?.document;
  const lineageBeads = selectedDocument?.document_no === selectedNo
    ? detail?.event_lineage?.beads || []
    : [];
  const hasObservedTransition = selectedDocument?.document_no === selectedNo
    && detail?.event_lineage?.has_observed_transition === true;
  const lineagePresentation = partitionLineageBeads(lineageBeads);
  const lineageRelatedness = selectedDocument?.document_no === selectedNo
    ? detail?.event_lineage?.relatedness || []
    : [];
  const events = detail?.rows?.length
    ? detail.rows
    : selectedDocument?.document_events || [];
  const graph = detail?.knowledge_graph || { nodes: [], edges: [] };
  const sourcePersons = graph.nodes.filter((node) => node.type === "person");
  const knowledgeEdges = knowledgeEdgeRows(knowledge);
  const ticketStatusOptions = detail?.ticket_status_options || [];

  useEffect(() => {
    if (selectedDocument && documentDialog.current && !documentDialog.current.open) {
      documentDialog.current.showModal();
    }
  }, [selectedDocument]);

  function closeDocument() {
    setSelectedNo("");
    setDetail(null);
    setEvidence(null);
  }

  function chooseAdminAccount(account) {
    setSelectedAdminId(account.account_id);
    setAdminForm({
      org: account.org || "",
      workspace: account.workspace || "",
      roles: account.roles || [],
    });
    setAdminStatus("");
  }

  async function saveAdminAccountClaims(event) {
    event.preventDefault();
    if (!selectedAdminId) return;
    setAdminBusy(true);
    setAdminStatus("");
    try {
      const updated = await api(`/api/admin/keyverse/accounts/${encodeURIComponent(selectedAdminId)}/claims`, {
        method: "POST",
        body: JSON.stringify(adminForm),
      });
      setAdminAccounts((current) => current.map((account) => (
        account.account_id === updated.account_id ? updated : account
      )));
      setAdminForm({ org: updated.org || "", workspace: updated.workspace || "", roles: updated.roles || [] });
      setAdminStatus("Keyverse 원장에 저장되었습니다.");
    } catch (caught) {
      setAdminStatus(`저장하지 못했습니다: ${caught.message}`);
    } finally {
      setAdminBusy(false);
    }
  }

  async function saveDocumentVisibilityFor(documentNo, nextVisibility) {
    setAdminBusy(true);
    setAdminStatus("");
    try {
      const result = await api(`/api/documents/${encodeURIComponent(documentNo)}/visibility`, {
        method: "POST",
        body: JSON.stringify({ visibility: nextVisibility }),
      });
      setDocuments((current) => current.map((item) => item.document_no === documentNo
        ? { ...item, visibility: result.document.visibility }
        : item));
      setAdminDocuments((current) => current.map((item) => item.document_no === documentNo
        ? { ...item, visibility: result.document.visibility }
        : item));
      setAdminStatus(`${documentNo} 게시글 공개 정책이 저장되었습니다.`);
    } catch (caught) {
      setAdminStatus(`게시글 공개 정책을 저장하지 못했습니다: ${caught.message}`);
    } finally {
      setAdminBusy(false);
    }
  }

  async function decideLineageEdge(item, overrideStatus) {
    setLineageReviewBusy(true);
    setLineageReviewStatus("");
    try {
      const updated = await api("/api/admin/lineage/edges/override", {
        method: "POST",
        body: JSON.stringify({
          source_node: item.source_node,
          target_node: item.target_node,
          relation: item.relation,
          override_status: overrideStatus,
          reason: overrideStatus === "suppressed" ? "관리자 검토에서 비관련 연결로 제외" : "관리자 재검토에서 연결 복원",
        }),
      });
      setLineageReviewEdges((current) => current.map((candidate) => (
        candidate.source_node === updated.source_node
          && candidate.target_node === updated.target_node
          && candidate.relation === updated.relation
          ? { ...candidate, ...updated }
          : candidate
      )));
      setLineageReviewStatus(overrideStatus === "suppressed" ? "비관련 연결을 Lineage에서 제외했습니다." : "Lineage 연결을 복원했습니다.");
    } catch (caught) {
      setLineageReviewStatus(`Lineage 결정을 저장하지 못했습니다: ${caught.message}`);
    } finally {
      setLineageReviewBusy(false);
    }
  }

  async function runEnrichment(event) {
    event.preventDefault();
    setEnrichmentBusy(true);
    setEnrichmentStatusMessage("");
    try {
      const result = await api("/api/admin/enrichment/run", {
        method: "POST",
        body: JSON.stringify({ task: enrichmentTask, limit: Number(enrichmentLimit) || 16 }),
      });
      setEnrichmentStatusMessage(result.status === "empty"
        ? "선택한 작업의 대기 문서가 없습니다."
        : `분석 작업을 시작했습니다: ${result.requested}건`);
    } catch (caught) {
      setEnrichmentStatusMessage(`분석 작업을 시작하지 못했습니다: ${caught.message}`);
    } finally {
      setEnrichmentBusy(false);
    }
  }

  async function refreshReports() {
    setReportRefreshBusy(true);
    setReportRefreshStatus("");
    try {
      const result = await api("/api/admin/reports/refresh", { method: "POST", body: "{}" });
      const reports = await api("/api/reports");
      setSummary((current) => ({
        ...(current || {}),
        period_reports: reports.reports || current?.period_reports || [],
        factor_definitions: reports.factor_definitions || current?.factor_definitions || [],
      }));
      setReportRefreshStatus(result.refreshed
        ? `보고서 ${result.refreshed}건을 재평가했습니다.`
        : "현재 재평가가 필요한 보고서가 없습니다.");
    } catch (caught) {
      setReportRefreshStatus(`보고서를 재평가하지 못했습니다: ${caught.message}`);
    } finally {
      setReportRefreshBusy(false);
    }
  }

  async function submitTeppAnalysis(event) {
    event.preventDefault();
    setTeppBusy(true);
    setTeppStatusMessage("");
    try {
      const result = await api("/api/admin/tepp/analysis-runs", {
        method: "POST",
        body: JSON.stringify({
          contract_version: "v1",
          idempotency_key: teppIdempotencyKey.trim(),
          snapshot_id: teppSnapshotId.trim(),
          knowledge_cutoff: teppKnowledgeCutoff.trim(),
          model_contract: { name: "trsl-tm", version: "v0.4" },
          configuration: { source: "lineageweave", mode: "temporal_relational_shared_latent_topic_measurement" },
          output_profile: { format: "json", include: ["events", "relations", "measurement"] },
        }),
      });
      setTeppStatusMessage(`TEPP 분석 요청을 ${result.status === "existing" ? "재사용했습니다" : "접수했습니다"}: ${result.run_id}`);
      setTeppStatus((current) => ({ ...(current || {}), runs: [result, ...((current && current.runs) || [])] }));
    } catch (caught) {
      setTeppStatusMessage(`TEPP 분석 요청을 접수하지 못했습니다: ${caught.message}`);
    } finally {
      setTeppBusy(false);
    }
  }

  async function refreshTeppRun(runId) {
    try {
      const updated = await api(`/api/admin/tepp/analysis-runs/${encodeURIComponent(runId)}`);
      setTeppStatus((current) => ({ ...(current || {}), runs: (current?.runs || []).map((run) => run.run_id === updated.run_id ? { ...run, ...updated } : run) }));
      setTeppStatusMessage(`TEPP 실행 상태를 갱신했습니다: ${updated.remote_state}`);
    } catch (caught) {
      setTeppStatusMessage(`TEPP 실행 상태를 갱신하지 못했습니다: ${caught.message}`);
    }
  }

  function renderLineageBead(bead, index, _beads, asObservation = false) {
    const evidenceId = String(bead.evidence_id || "");
    const opensEvidence = evidenceId && !evidenceId.includes(":");
    const connectsObservedEvents = !asObservation && bead.connects_to_next === true;
    return <div className={`lineage-step ${bead.kind || "document"} ${asObservation ? "observation" : ""}`} key={`${bead.kind}-${bead.label}-${index}`}>
      <button
        type="button"
        className={`lineage-node ${bead.evidence_status || "observed"} ${bead.kind === "event" ? "selected" : ""}`}
        onClick={() => { if (opensEvidence) void openEvidence(evidenceId); }}
      >
        <span>{bead.kind === "event" ? (asObservation ? "관찰된 사건" : String(index + 1).padStart(2, "0")) : `${bead.evidence_status || "observed"} · ${bead.kind || "document"}`}</span>
        <strong>{bead.label || selectedNo}</strong>
        <em>{bead.detail || bead.neighbor || selectedNo}</em>
      </button>
      {connectsObservedEvents ? <span className="lineage-edge" aria-label="관찰된 이벤트 전이 근거" /> : null}
    </div>;
  }

  function renderEventLineage(id = "") {
    const idProps = id ? { id } : {};
    if (!lineageBeads.length) {
      return <div {...idProps} className="lineage-presentation"><div className="lineage-chain"><span className="lineage-node selected"><span>observed</span><strong>{selectedNo}</strong></span></div></div>;
    }
    const segments = hasObservedTransition ? lineagePresentation.segments : [];
    const observations = segments.length ? lineagePresentation.observations : lineageBeads;
    return <div {...idProps} className="lineage-presentation">
      {segments.length ? <div className="lineage-segments">{segments.map((segment, index) => <div className="lineage-chain" key={`segment-${segment[0]?.evidence_id || index}`}>{segment.map(renderLineageBead)}</div>)}</div> : null}
      {observations.length ? <div className="lineage-unlinked">
        <p className="lineage-unlinked-message">{segments.length ? "전이 근거가 없는 사건은 독립적으로 표시합니다." : "사건 간 전이 근거가 확인되지 않아 Lineage로 연결하지 않습니다."}</p>
        <div className="lineage-observations">{observations.map((bead, index, beads) => renderLineageBead(bead, index, beads, true))}</div>
      </div> : null}
    </div>;
  }

  function validatedEmailAddress() {
    const email = emailAddress.trim();
    const message = emailValidationMessage(email, emailInput.current?.validity.valid);
    if (message) {
      setEmailError(message);
      return "";
    }
    setEmailError("");
    return email;
  }

  async function startKeyverseLogin(event) {
    event.preventDefault();
    const email = validatedEmailAddress();
    if (!email) {
      emailInput.current?.focus();
      return;
    }
    setBusy(true);
    try {
      const result = await api("/api/login", {
        method: "POST",
        body: JSON.stringify({ email_address: email }),
      });
      window.location.assign(result.authorization_url);
    } catch {
      setEmailError("로그인을 시작할 수 없습니다. 잠시 후 다시 시도하거나 관리자에게 문의해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  async function loadMore() {
    setLoadingMore(true);
    try {
      const query = filter.trim() ? `&q=${encodeURIComponent(filter.trim())}` : "";
      const index = await api(`/api/documents?limit=100&offset=${documents.length}${query}`);
      setDocuments((current) => [...current, ...(index.items || [])]);
      setTotalDocuments(index.total || totalDocuments);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setLoadingMore(false);
    }
  }

  async function loadMoreAdminDocuments() {
    if (adminDocumentLoadState === "loading_more" || adminDocuments.length >= adminDocumentTotal) return;
    setAdminDocumentLoadState("loading_more");
    try {
      const query = adminDocumentFilter.trim() ? `&q=${encodeURIComponent(adminDocumentFilter.trim())}` : "";
      const index = await api(`/api/documents?limit=20&offset=${adminDocuments.length}${query}`);
      setAdminDocuments((current) => [...current, ...(index.items || [])]);
      setAdminDocumentTotal(index.total || adminDocumentTotal);
      setAdminDocumentLoadState("ready");
    } catch (caught) {
      setAdminDocumentLoadState("error");
      setAdminStatus(`게시글 권한 목록을 더 불러오지 못했습니다: ${caught.message}`);
    }
  }

  async function searchSemanticDocuments() {
    const query = filter.trim();
    if (query.length < 2) return;
    setBusy(true);
    setError("");
    try {
      setSemanticSearch(await api(`/api/documents/semantic-search?q=${encodeURIComponent(query)}`));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function openEvidence(guid) {
    if (!selectedNo || !guid) return;
    setError("");
    try {
      setEvidence(await api(`/api/documents/${encodeURIComponent(selectedNo)}/evidence/${encodeURIComponent(guid)}`));
    } catch (caught) {
      setError(caught.message);
    }
  }

  async function openKnowledge(node) {
    if (!selectedNo || !node) return;
    setError("");
    try {
      const suffix = knowledgeDepth ? `&depth=${encodeURIComponent(knowledgeDepth)}` : "";
      const personName = node.type === "person" || node.person ? (node.person || node.label || "") : "";
      const query = personName
        ? `person=${encodeURIComponent(personName)}`
        : `node=${encodeURIComponent(node.id || "")}`;
      setKnowledge(await api(`/api/documents/${encodeURIComponent(selectedNo)}/knowledge?${query}${suffix}`));
    } catch (caught) {
      setError(caught.message);
    }
  }

  function openKnowledgeNode(node) {
    if (!node) return;
    const documentNo = String(node.document_no || "").trim();
    if (node.type === "document" && documentNo && documentNo !== selectedNo) {
      setSelectedNo(documentNo);
      return;
    }
    const evidenceId = String(node.source_evidence_id || node.evidence_id || "").trim();
    if ((node.type === "event" || node.type === "content_block") && evidenceId && !evidenceId.includes(":")) {
      void openEvidence(evidenceId);
      return;
    }
    void openKnowledge(node);
  }

  async function loadSemanticRelated() {
    if (!selectedNo) return;
    setBusy(true);
    setError("");
    try {
      setSemanticRelated(await api(`/api/documents/${encodeURIComponent(selectedNo)}/semantic-related`));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function indexSemanticContent() {
    if (!selectedNo) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/documents/${encodeURIComponent(selectedNo)}/semantic-index`, { method: "POST", body: "{}" });
      setSemanticRelated(await api(`/api/documents/${encodeURIComponent(selectedNo)}/semantic-related`));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function askLineage() {
    if (!selectedNo || !message.trim()) return;
    setBusy(true);
    setError("");
    try {
      setChat(await api(`/api/documents/${encodeURIComponent(selectedNo)}/chat`, {
        method: "POST",
        body: JSON.stringify({ message }),
      }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyLineage() {
    if (!selectedNo) return;
    setBusy(true);
    setError("");
    try {
      setInferenceVerification(await api(`/api/documents/${encodeURIComponent(selectedNo)}/lineage/verify`, {
        method: "POST",
        body: "{}",
      }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function resolveOrganizationAlias(event) {
    event.preventDefault();
    if (!selectedNo || organizationAlias.trim().length < 2) return;
    setBusy(true);
    setError("");
    try {
      setAliasResolution(await api(`/api/documents/${encodeURIComponent(selectedNo)}/organizations/resolve`, {
        method: "POST",
        body: JSON.stringify({ alias_name: organizationAlias.trim() }),
      }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function inspectAsset(asset) {
    if (!selectedNo || !asset) return;
    setBusy(true);
    setError("");
    try {
      const result = await api(`/api/documents/${encodeURIComponent(selectedNo)}/assets/${asset.asset_index}/inspect`, {
        method: "POST",
        body: "{}",
      });
      setContent((current) => ({
        ...current,
        assets: (current?.assets || []).map((item) => item.asset_index === result.asset.asset_index
          ? { ...item, inspection: result.inspection }
          : item),
      }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function searchImages(event) {
    event.preventDefault();
    if (imageQuery.trim().length < 2) return;
    setBusy(true);
    setError("");
    try {
      const result = await api(`/api/images/search?q=${encodeURIComponent(imageQuery.trim())}`);
      setImageResults(result.items || []);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveVisibility() {
    if (!selectedNo) return;
    setBusy(true);
    try {
      const result = await api(`/api/documents/${encodeURIComponent(selectedNo)}/visibility`, {
        method: "POST",
        body: JSON.stringify({ visibility }),
      });
      setDetail((current) => ({ ...current, document: result.document }));
      setDocuments((current) => current.map((item) => item.document_no === selectedNo ? { ...item, visibility } : item));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveKeymen() {
    if (!selectedNo) return;
    setBusy(true);
    try {
      const result = await api(`/api/documents/${encodeURIComponent(selectedNo)}/keymen`, {
        method: "POST",
        body: JSON.stringify({ our_side: parseSide(keymanForm.our), counterpart_side: parseSide(keymanForm.counterpart) }),
      });
      setDetail((current) => ({
        ...current,
        document: {
          ...current.document,
          keyman_our_side: result.our_side,
          keyman_counterpart_side: result.counterpart_side,
          keymen: [...result.our_side, ...result.counterpart_side].map((item) => item.actor_name || item.person_name || item.org_name).filter(Boolean),
          keyman_source: "user_override",
          keyman_status: "managed",
        },
      }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function deriveKeymen() {
    if (!selectedNo) return;
    setBusy(true);
    setError("");
    try {
      const result = await api(`/api/documents/${encodeURIComponent(selectedNo)}/keymen/derive`, { method: "POST", body: "{}" });
      setDetail((current) => ({ ...current, document: result.document }));
      setKeymanForm({ our: sideText(result.document.keyman_our_side), counterpart: sideText(result.document.keyman_counterpart_side) });
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function createTicket() {
    if (!selectedNo || !ticketTitle.trim()) return;
    setBusy(true);
    try {
      const ticket = await api(`/api/documents/${encodeURIComponent(selectedNo)}/tickets`, {
        method: "POST",
        body: JSON.stringify({ title: ticketTitle }),
      });
      setDetail((current) => ({
        ...current,
        document: {
          ...current.document,
          issue_tickets: [...(current.document.issue_tickets || []), ticket],
          todo_items: [...(current.document.todo_items || []), ticket.todo].filter(Boolean),
          calendar_items: [...(current.document.calendar_items || []), ticket.calendar].filter(Boolean),
        },
      }));
      setTicketTitle("");
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  async function updateTicketStatus(ticket, status) {
    if (!selectedNo || !ticket.ticket_id || !status) return;
    setBusy(true);
    try {
      const updated = await api(`/api/documents/${encodeURIComponent(selectedNo)}/tickets/${encodeURIComponent(ticket.ticket_id)}`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      setDetail((current) => ({
        ...current,
        document: {
          ...current.document,
          issue_tickets: (current.document.issue_tickets || []).map((item) => (
            item.ticket_id === updated.ticket_id ? { ...item, status: updated.status } : item
          )),
          todo_items: (current.document.todo_items || []).map((item) => (
            item.ticket_id === updated.ticket_id ? { ...item, status: updated.status } : item
          )),
        },
      }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  if (checkingSession) return <main className="login-gate"><p>로그인 상태를 확인하고 있어요.</p></main>;
  if (!session) {
    return (
      <main className="login-gate">
        <div className="login-card">
          <div className="brand-mark">LW</div>
          <p className="eyebrow product-lineage">글 자체의 Lineage</p>
          <h1>LineageWeave</h1>
          <p className="meta login-intro">업무 이메일을 입력하고 계속하세요.</p>
          <form id="loginForm" className="login-form" noValidate onSubmit={startKeyverseLogin}>
            <label htmlFor="loginEmail">업무 이메일</label>
            <input
              ref={emailInput}
              id="loginEmail"
              name="email_address"
              type="email"
              autoComplete="email"
              placeholder="name@company.com"
              required
              aria-invalid={emailError ? "true" : undefined}
              aria-describedby={emailError ? "emailError" : undefined}
              value={emailAddress}
              onChange={(event) => {
                setEmailAddress(event.target.value);
                if (emailError) setEmailError("");
              }}
            />
            {emailError ? <p className="error" id="emailError" role="alert">{emailError}</p> : null}
            <button id="loginBtn" className="primary-button" type="submit" disabled={busy}>계속하기</button>
          </form>
        </div>
      </main>
    );
  }

  const analytics = summary?.analytics || {};
  const queueHealth = summary?.queue_health;
  const periodReports = summary?.period_reports || [];
  const displayDocumentTotal = documentLoadState === "loading"
    ? "…"
    : formatNumber(visibleDocumentTotal);
  const displayCustomerTotal = customerLoadState === "loading"
    ? "…"
    : formatNumber(customerSurface?.accounts?.length || 0);
  const displayReportTotal = summary ? formatNumber(periodReports.length) : "…";
  const selectedReport = periodReports.find((report) => report.report_id === selectedReportId) || null;
  const reportFactors = selectedReport?.factor_definitions || summary?.factor_definitions || [];
  const reportFactorLabel = (factorId) => (
    reportFactors.find((factor) => factor.factor_id === factorId)?.factor_label || factorId
  );
  const reportMetricLabels = {
    ragas_faithfulness: "근거 충실도",
    ragas_answer_relevancy: "질문 관련성",
    ragas_context_precision: "맥락 정밀도",
    ragas_context_recall: "맥락 재현율",
  };
  return (
    <main id="workspace" className="app-shell">
      <div className="top-strip" />
      <header className="masthead">
        <div>
          <p className="eyebrow product-lineage">글 자체의 Lineage</p>
          <h1>LineageWeave</h1>
          <p className="meta">글을 선택하면 연결된 사건과 근거를 확인할 수 있습니다.</p>
        </div>
        <div id="sessionMeta" className="session-badge">
          <strong>내 업무공간</strong>
          <span>{session.corp_name || session.corp_code} / {session.pu_name || session.pu_code}</span>
          <span>{canAdmin ? "관리자" : canManage ? "업무 담당" : "열람"}</span>
          <a className="logout-link" href="/api/logout">로그아웃</a>
        </div>
      </header>

      <nav className="view-nav" aria-label="LineageWeave 화면">
        <button type="button" className={activeView === "home" ? "selected" : ""} aria-pressed={activeView === "home"} onClick={() => setActiveView("home")}>업무 홈</button>
        <button type="button" className={activeView === "workspace" ? "selected" : ""} aria-pressed={activeView === "workspace"} onClick={() => setActiveView("workspace")}>업무공간</button>
        <button type="button" className={activeView === "customers" ? "selected" : ""} aria-pressed={activeView === "customers"} onClick={() => setActiveView("customers")}>고객 화면</button>
        {canAdmin ? <button type="button" className={activeView === "admin" ? "selected" : ""} aria-pressed={activeView === "admin"} onClick={() => setActiveView("admin")}>관리자 모드</button> : null}
      </nav>

      {canAdmin && activeView === "workspace" ? <section className="kpi-grid" aria-label="운영 진단 지표">
        <div className="kpi"><span>ROWS</span><strong id="metricRows">{analytics.total_rows ?? 0}</strong></div>
        <div className="kpi"><span>DOCUMENTS</span><strong id="metricDocs">{analytics.total_documents ?? 0}</strong></div>
        <div className="kpi"><span>THREADS</span><strong id="metricThreads">{analytics.multi_document_threads ?? 0}</strong></div>
        <div className="kpi"><span>KG EDGES</span><strong>{formatNumber((summary?.metadata?.knowledge_edge_rows || 0) || Object.values(analytics.edge_count_by_relation || {}).reduce((a, b) => a + b, 0))}</strong></div>
        <div className="kpi"><span>EVENT QUEUE</span><strong id="metricQueue">{queueHealth?.ready ? "READY" : "CHECK"}</strong><small>{queueHealth ? `outbox ${formatNumber(queueHealth.pending_outbox)}` : "상태 미확인"}</small></div>
      </section> : null}

      {activeView === "home" ? (
        <section id="userHome" className="user-home">
          <header className="screen-header home-header">
            <div>
              <p className="eyebrow">업무 홈</p>
              <h2>오늘의 고객·업무 인사이트</h2>
              <p className="meta">글의 순서가 아니라 확인된 사건, 고객 관계, 약속과 후속 조치를 중심으로 업무를 시작하세요.</p>
            </div>
            <div className="home-actions">
              <button className="primary-button" type="button" onClick={() => setActiveView("workspace")}>글·이벤트 보기</button>
              <button className="secondary-button" type="button" onClick={() => setActiveView("customers")}>고객 마스터 보기</button>
            </div>
          </header>
          <section className="home-metrics" aria-label="업무 요약">
            <article className="home-metric home-metric-primary"><span>확인할 글</span><strong>{displayDocumentTotal}</strong><p>권한 범위에서 확인할 수 있는 업무 글</p></article>
            <article className="home-metric"><span>연결된 고객</span><strong>{displayCustomerTotal}</strong><p>근거 문서가 연결된 고객 마스터</p></article>
            <article className="home-metric"><span>발행 리포트</span><strong>{displayReportTotal}</strong><p>PU·팀·프로젝트별 업무 리포트</p></article>
            <article className="home-metric"><span>내 권한</span><strong>{canAdmin ? "관리자" : canManage ? "업무 담당" : "열람"}</strong><p>{session.corp_code} · {session.pu_code}</p></article>
          </section>
          <div className="home-columns">
            <section className="home-card" aria-labelledby="homeDocumentsTitle">
              <div className="home-card-header"><div><p className="eyebrow">최근 업무</p><h3 id="homeDocumentsTitle">최근 확인할 글</h3></div><button className="source-button" type="button" onClick={() => setActiveView("workspace")}>전체 보기</button></div>
              <div className="home-list">
                {documents.slice(0, 6).map((item) => <button className="home-list-item" type="button" key={item.document_no} onClick={() => { setSelectedNo(item.document_no); setActiveView("workspace"); }}><strong>{item.title || item.document_no}</strong><span>{item.document_no} · {item.entity_role || "업무 글"}</span><small>{item.visibility === "public" ? "공개" : "내부"}</small></button>)}
                {!documents.length ? <p className="empty" role={documentLoadState === "error" ? "alert" : undefined}>{documentLoadState === "loading" ? "업무 글을 불러오는 중입니다." : documentLoadState === "error" ? "업무 글을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." : "현재 권한 범위에서 확인할 업무 글이 없습니다."}</p> : null}
              </div>
            </section>
            <section className="home-card" aria-labelledby="homeCustomersTitle">
              <div className="home-card-header"><div><p className="eyebrow">고객 마스터</p><h3 id="homeCustomersTitle">고객 관계</h3></div><button className="source-button" type="button" onClick={() => setActiveView("customers")}>고객 화면</button></div>
              <div className="home-list">
                {(customerSurface?.accounts || []).slice(0, 6).map((account) => <button className="home-list-item" type="button" key={account.account_name} onClick={() => { setSelectedCustomer(account.account_name); setActiveView("customers"); }}><strong>{account.account_name}</strong><span>{account.parent_name ? `상위 · ${account.parent_name}` : account.entity_role || "고객"}</span><small>근거 {formatNumber(account.document_nos?.length || 0)}건</small></button>)}
                {!customerSurface?.accounts?.length ? <p className="empty" role={customerLoadState === "error" ? "alert" : undefined}>{customerLoadState === "loading" ? "연결된 고객 정보를 불러오는 중입니다." : customerLoadState === "error" ? "고객 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." : "현재 권한 범위에서 연결된 고객 마스터가 없습니다."}</p> : null}
              </div>
            </section>
            <section className="home-card" aria-labelledby="homeReportsTitle">
              <div className="home-card-header"><div><p className="eyebrow">업무 리포트</p><h3 id="homeReportsTitle">최근 리포트</h3></div><button className="source-button" type="button" onClick={() => setActiveView("workspace")}>리포트 열기</button></div>
              <div className="home-list">
                {periodReports.slice(0, 6).map((report) => <button className="home-list-item" type="button" key={report.report_id} onClick={() => { setSelectedReportId(report.report_id); setActiveView("workspace"); }}><strong>{reportBusinessTitle(report)}</strong><span>{report.period_start} ~ {report.period_end}</span><small>{reportVerdictLabel(report.judge?.verdict)} · {formatNumber(report.document_count)}건</small></button>)}
                {!periodReports.length ? <p className="empty">{summary ? "발행된 리포트가 없습니다." : "리포트를 불러오는 중입니다."}</p> : null}
              </div>
            </section>
          </div>
        </section>
      ) : activeView === "workspace" ? <>
      <section className="workspace-grid">
        <aside className="sidebar">
          <div className="section-heading"><span>글 목록</span><small>{formatNumber(visibleDocumentTotal)}</small></div>
          <div className="document-search"><input className="list-filter" aria-label="글 검색" placeholder="문서·제목·스레드·의미 검색" value={filter} onChange={(event) => setFilter(event.target.value)} /><button className="source-button" type="button" disabled={busy || filter.trim().length < 2} onClick={searchSemanticDocuments}>의미 검색</button></div>
          {semanticSearch ? <p className="meta search-result-summary"><strong>“{semanticSearch.query}” 검색 결과</strong> · {semanticSearch.status === "index_required" ? "권한 범위에서 색인된 의미 단위가 아직 없습니다." : semanticSearch.status === "keyword_fallback" ? "의미 일치가 없어 제목·문서 일치 결과를 보여줍니다." : semanticSearch.status === "candidate_limit_reached" ? "색인 후보 상한 안에서 관련도순으로 표시합니다." : "관련도순으로 표시합니다."}</p> : null}
          <form className="image-search" onSubmit={searchImages}>
            <input aria-label="이미지 OCR 검색" placeholder="이미지 OCR·태그 검색" value={imageQuery} onChange={(event) => setImageQuery(event.target.value)} />
            <button className="source-button" type="submit" disabled={busy || imageQuery.trim().length < 2}>이미지 검색</button>
          </form>
          {imageResults.length ? <div className="image-results" role="region" aria-label="이미지 검색 결과">{imageResults.slice(0, 8).map((item) => <button className="image-result" key={`${item.document_no}-${item.asset_index}`} onClick={() => setSelectedNo(item.document_no)}><strong>{item.document_no} · #{item.asset_index}</strong><span>{item.ocr_text || (item.object_labels || []).map((label) => label.label).join(" · ") || "OCR 결과 없음"}</span></button>)}</div> : null}
          {documentRows.map((item) => (
            <button className={`doc-node thread-row ${selectedNo === item.document_no ? "selected" : ""}`} key={item.document_no} onClick={() => setSelectedNo(item.document_no)} aria-label={semanticSearch ? `${item.title || item.document_no} 원문과 타임라인 보기` : undefined}>
              <strong>{item.document_no}</strong>
              <span>{item.title || "제목 없음"}</span>
            <small className={semanticSearch ? "search-result-detail" : ""}>{semanticSearch ? item.relation === "semantic_related" ? `관련도 ${Math.round(Number(item.similarity || 0) * 100)}% · 원문과 타임라인 보기` : "제목·문서 일치 · 원문과 타임라인 보기" : `${item.entity_role || "미분류"} · ${item.visibility === "public" ? "공개" : "내부"}`}</small>
            </button>
          ))}
          {!documentRows.length ? <p className="empty" role={documentLoadState === "error" ? "alert" : undefined}>{semanticSearch ? "검색 결과가 없습니다." : documentLoadState === "loading" ? "업무 글을 불러오는 중입니다." : documentLoadState === "error" ? "업무 글을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." : "현재 권한 범위에서 확인할 업무 글이 없습니다."}</p> : null}
          {!semanticSearch && documents.length < totalDocuments ? <button className="load-button" onClick={loadMore} disabled={loadingMore}>{loadingMore ? "불러오는 중…" : "더 보기"}</button> : null}
          <div id="affiliateTree" className="sidebar-block">
            <div className="section-heading"><span>고객 관계 요약</span><small>근거 기반</small></div>
            {(summary?.affiliate_tree?.edges || []).slice(0, 16).map((edge) => <p className="tree-label" key={`${edge.parent}-${edge.child}`}>{edge.parent} → {edge.child}</p>)}
            {!(summary?.affiliate_tree?.edges || []).length ? (summary?.affiliate_tree?.nodes || []).slice(0, 16).map((label) => <p className="tree-label" key={label}>{label}</p>) : null}
          </div>
          <div id="periodReports" className="sidebar-block">
            <div className="section-heading"><span>주간/월간 리포트</span></div>
            {periodReports.slice(0, 8).map((report) => {
              const families = new Set(
                (report.linked_scores || [])
                  .map((score) => score.factor_family)
                  .filter(Boolean)
              );
              const labels = [
                families.has("general_management") ? "일반 경영" : null,
                families.has("industry") ? "산업별" : null,
                families.has("sales_lead") ? "영업 Lead" : null,
              ].filter(Boolean);
              return (
                <button className={`tree-label report-slice report-button ${selectedReportId === report.report_id ? "selected" : ""}`} data-report-id={report.report_id} key={report.report_id} type="button" aria-pressed={selectedReportId === report.report_id} onClick={() => setSelectedReportId(report.report_id)}>
                  <strong>{reportBusinessTitle(report)}</strong>
                  <span>{reportVerdictLabel(report.judge?.verdict)} · {formatNumber(report.document_count)}건</span>
                  {labels.length ? <small className="report-factors"> · {labels.join(" / ")}</small> : null}
                </button>
              );
            })}
            {!periodReports.length ? <p className="tree-label">리포트 없음</p> : null}
            {selectedReport ? <section id="reportDetail" className="report-detail" aria-live="polite">
              <div className="report-detail-head"><strong>{reportBusinessTitle(selectedReport)}</strong><button className="close-button" type="button" onClick={() => setSelectedReportId("")} aria-label="리포트 닫기">×</button></div>
              <p className="meta">{reportPeriodLabel(selectedReport.period_kind)} {reportSliceLabel(selectedReport.slice_kind)} · {selectedReport.period_start} ~ {selectedReport.period_end} · {formatNumber(selectedReport.document_count)}건</p>
              {selectedReport.judge?.rationale ? <p className="report-rationale">{selectedReport.judge.rationale}</p> : null}
              <div className="report-score-list">
                {(selectedReport.linked_scores || []).map((score) => <p key={score.score_id || `${score.factor_id}-${score.linking_method}`}><strong>{reportFactorLabel(score.factor_id)}</strong><span>점수 {Number(score.theta || 0).toFixed(2)} · 오차 {Number(score.standard_error || 0).toFixed(2)} · {reportLinkingLabel(score.linking_method)}</span></p>)}
                {!(selectedReport.linked_scores || []).length ? <p className="meta">연결 점수 없음</p> : null}
              </div>
              <div className="report-metric-list" aria-label="리포트 품질 평가 지표">
                <div className="section-heading"><span>품질 평가 지표</span><small>{reportJudgeSourceLabel(selectedReport.judge?.source)}</small></div>
                {(selectedReport.judge?.ragas_metrics || []).map((metric) => {
                  const score = typeof metric.score === "number" ? `${Math.round(metric.score * 100)}점` : "평가 보류";
                  const evidenceIds = (metric.evidence_ids || []).filter(Boolean).slice(0, 8);
                  return <article className="report-metric" key={metric.metric_id}>
                    <div className="report-metric-head"><strong>{reportMetricLabels[metric.metric_id] || "품질 지표"}</strong><span className={`report-metric-verdict ${metric.verdict || "abstain"}`}>{reportVerdictLabel(metric.verdict)} · {score}</span></div>
                    {metric.rationale ? <p>{metric.rationale}</p> : null}
                    {evidenceIds.length ? <div className="report-metric-evidence"><span>근거</span>{evidenceIds.map((documentNo) => <button className="report-document-link" key={documentNo} type="button" onClick={() => setSelectedNo(documentNo)}>{documentNo}</button>)}</div> : <small className="meta">연결된 근거 없음</small>}
                  </article>;
                })}
                {!(selectedReport.judge?.ragas_metrics || []).length ? <p className="meta">저장된 RAGAS 지표 없음</p> : null}
              </div>
              <div className="report-document-list">
                {(selectedReport.document_nos || []).slice(0, 16).map((documentNo) => <button className="report-document-link" key={documentNo} type="button" onClick={() => setSelectedNo(documentNo)}>{documentNo}</button>)}
              </div>
            </section> : null}
          </div>
        </aside>

        <section className="content-panel">
          <div className="section-heading"><span>글 자체의 Lineage</span><small>선택 글의 근거 기반 사건 흐름</small></div>
          {error ? <p className="error inline-error">{error}</p> : null}
          {!selectedNo ? <p className="empty">왼쪽 글 목록에서 문서를 선택하세요.</p> : renderEventLineage()}
        </section>
      </section>

      {selectedDocument ? (
        <dialog id="postPopup" ref={documentDialog} className="document-modal" aria-labelledby="popupTitle" onClose={closeDocument} onMouseDown={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}>
            <header className="modal-header">
              <div>
                <p className="eyebrow">글 상세 · {selectedDocument.entity_role || "미분류"}</p>
                <h2 id="popupTitle">{selectedDocument.title_sample || selectedDocument.document_no}</h2>
                <p className="meta">{selectedDocument.document_no} · {selectedDocument.visibility} · {selectedDocument.corp_code}/{selectedDocument.owner_pu}</p>
              </div>
              <button className="close-button" onClick={() => documentDialog.current?.close()} aria-label="닫기">×</button>
            </header>
            {error ? <p className="error modal-error" role="alert">{error}</p> : null}
            <div className="modal-grid">
              <section className="detail-card wide modal-summary"><h3>한국어 요약</h3><p id="popupSummary">{selectedDocument.korean_summary || "요약 없음"}</p></section>
              <section className="detail-card modal-timeline">
                <h3>주요 이벤트 · AJAX 출처</h3>
                <ul id="popupEvents" className="event-list">
                  {events.map((item, index) => <li key={`${item.guid || index}-${item.timestamp || ""}`}><strong>{item.timestamp || "시간 미상"}</strong><span>{item.event || "observed_row"} · {item.stage || "stage 미상"}</span>{item.guid ? <button className="source-button" onClick={() => openEvidence(item.guid)}>원문 보기</button> : null}</li>)}
                </ul>
              </section>
              <section className="detail-card modal-roles"><h3>R&amp;R</h3><ul id="popupRoles">{(selectedDocument.roles_and_responsibilities || []).map((item, index) => <li key={`${item.role}-${item.actor_name || "agent"}-${index}`}><strong>{item.role}{item.actor_name ? ` · ${item.actor_name}` : ""}</strong><span>{item.responsibility}</span>{item.rank || item.title ? <small>{[item.rank, item.title].filter(Boolean).join(" · ")}</small> : null}{item.organization_name && item.organization_name !== item.actor_name ? <small>{item.actor_type === "person" ? "소속" : "기관"}: {item.organization_name} · {item.affiliation_status || "unknown"}</small> : item.actor_type ? <small>{item.actor_type}</small> : null}{item.node || item.entity || item.relationship || item.direction ? <small>Node {semanticValue(item.node)} · Entity {semanticValue(item.entity)} · Rel {semanticValue(item.relationship)} · Dir {semanticValue(item.direction)}</small> : null}</li>)}</ul></section>
              <section className="detail-card wide modal-lineage-card">
                <h3>글 자체의 Lineage</h3>
                <p className="meta">근거가 확인된 전이만 순서로 보여줍니다. 같은 스레드 단서와 추론 관련성은 아래에 따로 표시합니다.</p>
                {renderEventLineage("popupLineage")}
                <p className="evidence-note">
                  <span className="dot observed" /> 관측 근거
                  <span className="dot inferred" /> 추론 근거
                  <span className="dot predicted" /> 예측 근거
                </p>
                {lineageRelatedness.length ? <section className="lineage-relatedness" aria-label="직접 순서가 아닌 관련성">
                  <h4>직접 순서가 아닌 관련성</h4>
                  <p className="meta">추론·예측된 연결입니다. 이 글의 다음 사건으로 해석하지 않습니다.</p>
                  <div className="relatedness-list">
                    {lineageRelatedness.map((item, index) => {
                      const evidenceId = String(item.evidence_id || "");
                      const opensEvidence = evidenceId && !evidenceId.includes(":");
                      return <button type="button" className={`relatedness-node ${item.evidence_status || "inferred"}`} key={`${item.label}-${item.detail}-${index}`} onClick={() => { if (opensEvidence) void openEvidence(evidenceId); }}><strong>{lineageRelationLabel(item.label)}</strong><span>{item.detail || item.neighbor || "관련 노드"}</span></button>;
                    })}
                  </div>
                </section> : null}
                {canManage ? <button className="secondary-button" disabled={busy} onClick={verifyLineage}>LLM 근거 검증 실행</button> : null}
                {inferenceVerification ? <div className="inference-result"><p className="meta">검증 {inferenceVerification.candidate_count || 0}건 · 외부 검색 {inferenceVerification.external_search_mode}</p>{(inferenceVerification.items || []).map((item) => <article key={item.candidate_id}><strong>{item.relation_name} · {item.decision}</strong><span>confidence {Number(item.confidence || 0).toFixed(2)} · {item.rationale || "근거 불충분"}</span><div className="citation-row">{(item.evidence || []).map((evidence) => <a className="citation" key={evidence.evidence_id} href={evidence.source_uri || undefined} target={evidence.source_uri ? "_blank" : undefined} rel={evidence.source_uri ? "noreferrer" : undefined} onClick={(event) => { if (!evidence.source_uri) { event.preventDefault(); if (evidence.evidence_kind === "internal") openEvidence(evidence.evidence_id); } }}>{evidence.evidence_kind === "external" ? evidence.title || "외부 근거" : `내부 근거 ${evidence.evidence_id}`}</a>)}</div></article>)}</div> : null}
              </section>

              <section className="detail-card modal-keyman-our">
                <h3>Keyman · 사측</h3>
                <ul id="popupKeymanOur">{sideRows(selectedDocument.keyman_our_side).map((item, index) => { const label = item.actor_name || item.person_name || item.org_name; const node = sourcePersons.find((candidate) => candidate.label === label || candidate.label === item.organization_name || candidate.label === item.org_name); return <li key={`${label}-${item.org_name}-${index}`}><button className="keyman-link" onClick={() => openKnowledge(node || { person: label })}>{sideLabel(item)}</button></li>; })}</ul>
                <p className="meta">분석 상태: {keymanSourceLabel(selectedDocument.keyman_source || "pending")}</p>
              </section>
              <section className="detail-card modal-keyman-counterpart">
                <h3>Keyman · 상대측</h3>
                <ul id="popupKeymanCounterpart">{sideRows(selectedDocument.keyman_counterpart_side).map((item, index) => { const label = item.actor_name || item.person_name || item.org_name; const node = sourcePersons.find((candidate) => candidate.label === label || candidate.label === item.organization_name || candidate.label === item.org_name); return <li key={`${label}-${item.org_name}-${index}`}><button className="keyman-link" onClick={() => openKnowledge(node || { person: label })}>{sideLabel(item)}</button></li>; })}</ul>
                <p className="meta">관리 상태: {keymanStatusLabel(selectedDocument.keyman_status || "not_run")}</p>
              </section>
              <section className="detail-card wide modal-knowledge">
                <h3>Keyman Knowledge Graph</h3>
                <p className="meta">사람·조직·이벤트·글을 사전 계산한 KG에서 선택합니다. 노드 유형별 적응형 depth를 기본 적용하고, 필요하면 상한을 좁힐 수 있습니다.</p>
                <label className="depth-control">탐색 상한 <select value={knowledgeDepth} onChange={(event) => setKnowledgeDepth(event.target.value)}><option value="">적응형</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option></select></label>
                <div className="knowledge-summary">{graph.nodes.filter((node) => ["person", "organization", "organization_alias", "pu", "event", "document"].includes(node.type)).slice(0, 20).map((node) => <button className="knowledge-chip" key={node.id} onClick={() => openKnowledge(node)}><strong>{node.type}</strong><span>{node.label}</span></button>)}</div>
                {knowledge ? <div id="popupKnowledge" className="knowledge-result"><p className="meta">{knowledge.person_name || "선택한 KG 노드"} · {knowledge.nodes?.length || 0} nodes · {knowledge.edges?.length || 0} edges · depth {knowledgeDepth || "adaptive"}</p><ul className="event-list knowledge-node-list">{(knowledge.nodes || []).map((node) => <li key={node.id}><button type="button" className="knowledge-node-link" onClick={() => openKnowledgeNode(node)}><strong>{node.type}</strong><span>{node.label} · d{node.traversal_depth ?? "?"}</span></button></li>)}</ul><h4>연결 관계와 방향</h4>{knowledgeEdges.length ? <ul id="popupKnowledgeEdges" className="event-list" aria-label="Keyman Knowledge Graph 연결 관계와 방향">{knowledgeEdges.map((edge) => <li key={`${edge.sourceLabel}-${edge.relation}-${edge.targetLabel}`}><strong>{edge.sourceLabel} → {edge.targetLabel}</strong><span>{edge.sourceTypeLabel} → {edge.relationLabel} → {edge.targetTypeLabel}</span><small>관계 유형: {edge.relation} · {edge.evidenceLabel}</small></li>)}</ul> : <p className="meta">선택 범위에서 표시할 근거 기반 관계가 없습니다.</p>}</div> : null}
                <div className="inline-actions"><button className="secondary-button" disabled={busy} onClick={loadSemanticRelated}>의미 관련 글 보기</button>{canManage ? <button className="secondary-button" disabled={busy} onClick={indexSemanticContent}>이 글 임베딩 색인</button> : null}</div>
                {semanticRelated ? <div id="popupSemanticRelated" className="knowledge-result"><p className="meta">{semanticRelated.status === "index_required" ? "먼저 관리 권한으로 이 글의 DOM 의미 단위를 색인하세요." : "유사도 0.40 이상만 보이며, 결과는 문서 전이가 아닌 추론된 관련성입니다."}</p><ul className="event-list">{(semanticRelated.items || []).map((item) => <li key={item.document_no}><button className="keyman-link" onClick={() => setSelectedNo(item.document_no)}><strong>{item.title || item.document_no}</strong><span>{Number(item.similarity || 0).toFixed(3)} · {item.evidence_status}</span></button></li>)}</ul></div> : null}
                {canManage ? <form className="alias-resolution" onSubmit={resolveOrganizationAlias}><label htmlFor="organizationAlias">기관 약칭 검증</label><div className="inline-actions"><input id="organizationAlias" value={organizationAlias} onChange={(event) => setOrganizationAlias(event.target.value)} placeholder="본문의 기관 약칭" /><button className="secondary-button" type="submit" disabled={busy || organizationAlias.trim().length < 2}>LLM·SearXNG 검증</button></div></form> : null}
                {aliasResolution ? <div className="knowledge-result" id="organizationAliasResult"><p><strong>{aliasResolution.alias_name}</strong>에서 <strong>{aliasResolution.canonical_name || "미확정"}</strong>으로</p><p className="meta">{aliasResolution.decision} · confidence {Number(aliasResolution.confidence || 0).toFixed(2)} · {aliasResolution.direction}</p><div className="citation-row">{(aliasResolution.evidence || []).map((item) => <a className="citation" key={item.evidence_id} href={item.source_uri} target="_blank" rel="noreferrer">{item.title || "외부 근거"}</a>)}</div></div> : null}
                {canManage ? <button className="secondary-button" disabled={busy} onClick={deriveKeymen}>LLM Keyman 재도출</button> : null}
              </section>

              <section id="popupChat" className="detail-card wide modal-chat">
                <h3>이벤트 사이 무슨 일이 있었나</h3>
                <textarea id="chatMessage" aria-label="글 자체의 Lineage 질문" value={message} onChange={(event) => setMessage(event.target.value)} />
                <button id="chatAskBtn" className="secondary-button" disabled={busy} onClick={askLineage}>LLM에게 묻기</button>
                {chat ? (
                  <div className="chat-answer">
                    <p id="chatAnswer">{chat.answer}</p>
                    <div id="chatCitations" className="citation-row">
                      {(chat.citations || (chat.evidence_ids || []).map((evidenceId) => ({ evidence_id: evidenceId, guid: evidenceId, label: evidenceId }))).map((citation, index) => {
                        const handle = String(citation.term_uri || citation.evidence_id || citation.guid || "");
                        const ontology = handle.startsWith("http") || handle.startsWith("urn:") || citation.citation_kind === "ontology";
                        const vocId = String(citation.evidence_id || citation.guid || "");
                        return (
                          <button
                            className={`citation ${ontology ? "ontology" : "voc-source"}`}
                            id={ontology ? undefined : (index === 0 || citation.citation_kind === "voc" ? `vocCitation${index}` : undefined)}
                            data-evidence-id={ontology ? undefined : vocId}
                            key={`${handle}-${index}`}
                            title={handle}
                            onClick={() => {
                              if (ontology) return;
                              openEvidence(vocId);
                            }}
                          >
                            {ontology ? `온톨로지 ${citation.label || handle}` : `출처 ${citation.label || handle}`}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </section>

              {content ? <section className="detail-card wide modal-content"><h3>콘텐츠 구조 · {content.semantic_block_count || 0} blocks / {content.asset_count || 0} assets</h3><p className="meta">HTML 원문과 인라인 바이트는 KG에 넣지 않습니다. 의미 단위·서식·원래 위치를 PostgreSQL에 분리 저장하고, 원본은 인증된 endpoint에서만 필요할 때 읽습니다.</p>{(content.semantic_blocks || []).length ? <div className="content-block-list">{content.semantic_blocks.map((block) => <article className="content-block" key={`${block.source_evidence_id}-${block.block_index}`}><div className="content-block-head"><strong>{block.block_kind}</strong><span>row {block.source_row_number || "?"} · pos {block.source_position}</span><button className="source-button" type="button" onClick={() => openEvidence(block.source_evidence_id)}>근거 보기</button></div><p>{block.text_preview || "텍스트 없음"}</p>{(block.format_hints || []).length ? <div className="format-hints">{block.format_hints.map((hint, index) => <span key={`${hint.hint_kind}-${hint.hint_value}-${index}`}>{hint.hint_kind}: {hint.hint_value}</span>)}</div> : null}</article>)}</div> : <p className="meta">추출할 HTML 의미 단위가 없습니다.</p>}<div className="asset-grid">{(content.assets || []).slice(0, 24).map((asset) => <div className="asset-item" key={`${asset.asset_index}-${asset.source_position}`}><a href={`/api/documents/${encodeURIComponent(selectedNo)}/assets/${asset.asset_index}`} target="_blank" rel="noreferrer">{canPreviewAsset(asset) ? <img src={`/api/documents/${encodeURIComponent(selectedNo)}/assets/${asset.asset_index}`} alt={`인라인 이미지 ${asset.asset_index}`} /> : <span>{asset.mime_type} · {formatNumber(asset.encoded_bytes)} bytes · 원본 열기</span>}<small>{asset.content_kind} · pos {asset.source_position}</small></a>{asset.inspection ? <div className="asset-inspection"><strong>OCR</strong><p>{asset.inspection.ocr_text || "인식된 텍스트 없음"}</p><div className="asset-labels">{(asset.inspection.object_labels || []).map((label) => <span key={label.label} title={label.description || undefined}>{label.label}</span>)}</div></div> : canManage && isInspectableAsset(asset) ? <button className="source-button" type="button" disabled={busy} onClick={() => inspectAsset(asset)}>OCR·객체 분석</button> : canManage && String(asset.mime_type || "").startsWith("image/") ? <small>검사 한도를 넘었거나 지원되지 않는 형식</small> : null}</div>)}</div></section> : null}

              <section className="detail-card modal-visibility">
                <h3>공개 / 비공개</h3>
                <select aria-label="게시글 공개 범위" value={visibility} onChange={(event) => setVisibility(event.target.value)} disabled={!canManage}><option value="public">공개</option><option value="private">비공개</option></select>
                {canManage ? <button className="secondary-button" disabled={busy} onClick={saveVisibility}>저장</button> : <p className="meta">읽기 전용 세션</p>}
              </section>
              <section className="detail-card modal-tickets">
                <h3>이슈 티켓</h3>
                <ul id="popupTickets">{(selectedDocument.issue_tickets || []).map((ticket) => <li className="ticket" key={ticket.ticket_id}><strong>{ticket.title}</strong>{canManage ? <form className="ticket-form" onSubmit={(event) => { event.preventDefault(); void updateTicketStatus(ticket, String(new FormData(event.currentTarget).get("status") || "")); }}><select aria-label={`${ticket.title} 상태`} name="status" defaultValue={ticket.status || "open"} disabled={busy}>{ticketStatusOptions.map((option) => <option key={option.code} value={option.code}>{option.label}</option>)}</select><button className="secondary-button" disabled={busy}>상태 저장</button></form> : <span>{ticket.status}</span>}</li>)}</ul>
                {canManage ? <div className="ticket-form"><input value={ticketTitle} onChange={(event) => setTicketTitle(event.target.value)} placeholder="새 이슈 제목" /><button className="secondary-button" disabled={busy} onClick={createTicket}>등록</button></div> : null}
              </section>
              <section className="detail-card modal-todos">
                <h3>To Do</h3>
                <ul id="popupTodos">{(selectedDocument.todo_items || (selectedDocument.issue_tickets || []).map((ticket) => ticket.todo).filter(Boolean)).map((item) => <li className="ticket" key={item.todo_id}><strong>{item.title}</strong><span>{item.body}</span></li>)}</ul>
              </section>
              <section className="detail-card modal-calendar">
                <h3>캘린더</h3>
                <ul id="popupCalendar">{(selectedDocument.calendar_items || (selectedDocument.issue_tickets || []).map((ticket) => ticket.calendar).filter(Boolean)).map((item) => <li className="ticket" key={item.calendar_id}><strong>{item.occurred_on || "일정 미정"}</strong><span>{item.body}</span></li>)}</ul>
              </section>
              <section className="detail-card modal-appointments">
                <h3>고객 약속</h3>
                <ul id="popupAppointments">{(selectedDocument.appointments || []).map((item) => <li className="ticket" key={item.appointment_id}><strong>{item.occurred_on}</strong><span>{item.excerpt || item.label}</span></li>)}</ul>
              </section>
              {canManage ? <section className="detail-card wide modal-keyman-editor"><h3>Keyman 관리</h3><p className="meta">사람은 <code>이름 | 조직 | 직급 | 직책</code>, 기관·팀은 <code>organization | 이름 | 소속 | 직급 | 직책</code> 형식입니다. 기관을 사람 이름으로 입력하지 않으며, 뒤 항목은 생략할 수 있습니다.</p><div className="two-column"><label>사측<textarea value={keymanForm.our} onChange={(event) => setKeymanForm({ ...keymanForm, our: event.target.value })} /></label><label>상대측<textarea value={keymanForm.counterpart} onChange={(event) => setKeymanForm({ ...keymanForm, counterpart: event.target.value })} /></label></div><button className="secondary-button" disabled={busy} onClick={saveKeymen}>Keyman 저장</button></section> : null}
              {evidence ? <aside id="vocDrawer" className="source-drawer" aria-label="원문 출처"><button className="close-button" onClick={() => setEvidence(null)} aria-label="출처 닫기">×</button><p className="eyebrow">원문 근거</p><h2>{evidence.title || evidence.evidence_id}</h2><p className="meta">{evidence.event} · {evidence.stage} · {evidence.created_at}</p><dl><dt>법인 / PU</dt><dd>{evidence.corp_code} / {evidence.pu_code}</dd><dt>바이트</dt><dd>{formatNumber(evidence.content_bytes)}</dd><dt>본문 미리보기</dt><dd className="source-preview">{evidence.content_preview || "내용 없음"}</dd></dl></aside> : null}
            </div>
        </dialog>
      ) : null}
      </> : activeView === "customers" ? (
        <section id="customerScreen" className="customer-screen">
          <header className="screen-header">
            <div><p className="eyebrow">고객 관계 분석</p><h2>고객 마스터 · 계열 Tree</h2><p className="meta">확인된 고객·계열 관계를 근거 문서와 함께 살펴봅니다. 근거 없는 관계는 표시하지 않습니다.</p></div>
            <span className="status-chip">근거 연결</span>
          </header>
          <div className="customer-toolbar"><input aria-label="고객 검색" placeholder="고객사·계열·역할 검색" value={customerFilter} onChange={(event) => setCustomerFilter(event.target.value)} /><span className="meta">{displayCustomerTotal}개 고객</span></div>
          <div className="customer-layout">
            <aside className="customer-list" aria-label="고객 목록">
              {(customerSurface?.accounts || []).map((account) => <button type="button" className={`customer-item ${selectedCustomer === account.account_name ? "selected" : ""}`} key={account.account_name} onClick={() => setSelectedCustomer(account.account_name)}><strong>{account.account_name}</strong><span>{account.entity_role || "고객"} · {customerTierLabel(account.tier)}</span><small>근거 {formatNumber(account.document_nos?.length || 0)}건</small></button>)}
              {!(customerSurface?.accounts || []).length ? <p className="empty">{customerLoadState === "loading" ? "고객 정보를 불러오는 중입니다." : customerLoadState === "error" ? "고객 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요." : "인증된 문서에 연결된 고객이 없습니다."}</p> : null}
            </aside>
            <article className="customer-detail">
              {(() => {
                const account = (customerSurface?.accounts || []).find((item) => item.account_name === selectedCustomer);
                const childEdges = (customerSurface?.edges || []).filter((edge) => edge.parent === selectedCustomer);
                return account ? <>
                  <p className="eyebrow">고객 계정</p><h3>{account.account_name}</h3>
                  <div className="tag-row"><span>{account.entity_role || "고객"}</span><span>{customerTierLabel(account.tier)}</span>{account.parent_name ? <span>상위 · {account.parent_name}</span> : null}</div>
                  <h4>연결 계열</h4><div className="tree-list">{childEdges.length ? childEdges.map((edge) => <div className="customer-relation" key={`${edge.parent}-${edge.child}-${edge.relation}`}><p>{account.account_name} → {edge.child}</p><small>{customerRelationSourceLabel(edge.source)} · 의미 관계: {edge.relation || "계열 관계"} · 근거 {formatNumber(edge.document_nos?.length || 0)}건</small>{(edge.document_nos || []).length ? <div className="evidence-links">{edge.document_nos.map((documentNo) => <button type="button" className="report-document-link" key={documentNo} onClick={() => { setSelectedNo(documentNo); setActiveView("workspace"); }}>{documentNo}</button>)}</div> : null}</div>) : <p className="meta">직접 확인된 하위 계열이 없습니다.</p>}</div>
                  <h4>근거 문서</h4><div className="evidence-links">{(account.document_nos || []).map((documentNo) => <button type="button" className="report-document-link" key={documentNo} onClick={() => { setSelectedNo(documentNo); setActiveView("workspace"); }}>{documentNo}</button>)}</div>
                </> : <p className="empty">{customerLoadState === "loading" ? "고객 상세 정보를 불러오는 중입니다." : customerLoadState === "error" ? "고객 상세 정보를 불러오지 못했습니다." : "왼쪽 고객 목록에서 고객을 선택하세요."}</p>;
              })()}
            </article>
            <aside className="customer-tree" role="tree" aria-label="고객 계열 관계">
              <h3>통합 계열 Tree</h3>
              {customerTreeRows(customerSurface?.accounts, customerSurface?.edges).map(({ account, depth }) => <button type="button" role="treeitem" className={`tree-label customer-tree-node ${selectedCustomer === account.account_name ? "selected" : ""}`} style={{ paddingLeft: `${12 + depth * 16}px` }} aria-level={depth + 1} aria-selected={selectedCustomer === account.account_name} key={account.account_name} onClick={() => setSelectedCustomer(account.account_name)}><strong>{account.account_name}</strong><small>{account.parent_name ? `상위 · ${account.parent_name}` : account.entity_role || "고객"} · {customerTierLabel(account.tier)}</small></button>)}
              {!(customerSurface?.accounts || []).length ? <p className="meta">{customerLoadState === "loading" ? "계열 관계를 불러오는 중입니다." : "관찰된 계열 관계가 없습니다."}</p> : null}
            </aside>
          </div>
        </section>
      ) : (
        <section id="adminMode" className="admin-screen">
          <header className="screen-header"><div><p className="eyebrow">ADMINISTRATION</p><h2>Keyverse 계정 및 권한</h2><p className="meta">법인 코드는 로그인한 관리자 법인으로 고정됩니다. PU와 동일 클라이언트 역할만 변경하며, Keyverse 비밀번호·토큰·자격 증명은 브라우저로 보내지 않습니다.</p></div><span className="status-chip">corp · {session.corp_code}</span></header>
          <div className="customer-toolbar"><input aria-label="Keyverse 계정 검색" placeholder="계정·이메일 검색" value={adminFilter} onChange={(event) => setAdminFilter(event.target.value)} /><span className="meta">{adminStatus ? "계정 원장 연결 필요" : `${formatNumber(adminAccounts.length)}개 계정`}</span></div>
          {adminStatus ? <p className="admin-status" role="status">{adminStatus}</p> : null}
          <section id="accessPolicyScreen" className="admin-policy-panel" aria-labelledby="accessPolicyTitle">
            <div className="admin-section-heading"><div><p className="eyebrow">ABAC / RBAC</p><h3 id="accessPolicyTitle">게시글 권한 통제</h3></div><span className="status-chip">server enforced</span></div>
            <div className="policy-rule-grid">
              <article className="policy-rule"><strong>RBAC</strong><span>관리자는 법인 범위, author/editor는 같은 PU의 작성·관리, reader는 승인된 글 열람만 가능합니다.</span></article>
              <article className="policy-rule"><strong>ABAC</strong><span>법인 코드 일치가 기본 조건이며, 비공개 글은 같은 PU 또는 관리자만 볼 수 있습니다.</span></article>
              <article className="policy-rule"><strong>게시글 공개 정책</strong><span>공개·비공개 변경은 이 화면과 문서 팝업에서 가능하고, 모든 변경은 PostgreSQL outbox에 기록됩니다.</span></article>
            </div>
            <div className="admin-document-policy-list">
              <div className="admin-section-heading"><h4>현재 법인 게시글 정책</h4><span className="meta">{adminDocumentLoadState === "loading" ? "불러오는 중…" : `${formatNumber(adminDocuments.length)} / ${formatNumber(adminDocumentTotal)}건`}</span></div>
              <input aria-label="게시글 권한 검색" placeholder="문서·제목·PU 검색" value={adminDocumentFilter} onChange={(event) => setAdminDocumentFilter(event.target.value)} />
              {adminDocuments.map((item) => <div className="admin-document-policy" key={item.document_no}>
                <button type="button" className="admin-document-link" onClick={() => { setSelectedNo(item.document_no); setActiveView("workspace"); }}><strong>{item.document_no}</strong><span>{item.title || "제목 없음"}</span></button>
                <span className="policy-scope">법인 {item.corp_code || session.corp_code} · PU {item.owner_pu || "미지정"}</span>
                <select aria-label={`${item.document_no} 공개 정책`} value={item.visibility || "private"} disabled={adminBusy} onChange={(event) => void saveDocumentVisibilityFor(item.document_no, event.target.value)}><option value="public">공개</option><option value="private">비공개</option></select>
              </div>)}
              {adminDocumentLoadState === "error" ? <p className="empty" role="alert">게시글 권한 목록을 불러오지 못했습니다.</p> : null}
              {adminDocumentLoadState !== "loading" && !adminDocuments.length ? <p className="empty">검색 조건에 맞는 권한 범위의 게시글이 없습니다.</p> : null}
              {adminDocuments.length < adminDocumentTotal ? <button className="load-button" type="button" onClick={() => void loadMoreAdminDocuments()} disabled={adminDocumentLoadState === "loading_more"}>{adminDocumentLoadState === "loading_more" ? "더 불러오는 중…" : "게시글 더 보기"}</button> : null}
            </div>
          </section>
          <section id="lineageReviewScreen" className="admin-policy-panel" aria-labelledby="lineageReviewTitle">
            <div className="admin-section-heading"><div><p className="eyebrow">LINEAGE QUALITY</p><h3 id="lineageReviewTitle">비관련 연결 검토</h3></div><span className="status-chip">observed transitions locked</span></div>
            <p className="meta">추론·예측 관련성만 제외하거나 복원할 수 있습니다. 관찰된 시간 순서와 실제 revision 전이는 관리자 화면에서도 변경할 수 없습니다.</p>
            <div className="customer-toolbar"><input aria-label="Lineage 검토 검색" placeholder="문서·제목·관계·사유 검색" value={lineageFilter} onChange={(event) => setLineageFilter(event.target.value)} /><span className="meta">{formatNumber(lineageReviewEdges.length)}개 후보</span></div>
            {lineageReviewStatus ? <p className="admin-status" role="status">{lineageReviewStatus}</p> : null}
            <div className="lineage-review-list">
              {lineageReviewEdges.map((item) => <article className={`lineage-review-item ${item.override_status}`} key={`${item.source_node}-${item.target_node}-${item.relation}`}>
                <div><strong>{item.source_document} → {item.target_document}</strong><span>{item.source_title || "제목 없음"} · {item.target_title || "제목 없음"}</span><small>{item.relation} · {item.evidence_status} · {item.reason || "사유 없음"}</small></div>
                <button type="button" className="secondary-button" disabled={lineageReviewBusy} onClick={() => void decideLineageEdge(item, item.override_status === "suppressed" ? "restored" : "suppressed")}>{item.override_status === "suppressed" ? "연결 복원" : "비관련으로 제외"}</button>
              </article>)}
              {!lineageReviewEdges.length ? <p className="empty">검토할 추론·예측 연결이 없습니다.</p> : null}
            </div>
          </section>
          <section id="enrichmentScreen" className="admin-policy-panel" aria-labelledby="enrichmentTitle">
            <div className="admin-section-heading"><div><p className="eyebrow">LLM OPERATIONS</p><h3 id="enrichmentTitle">LLM 분석 작업</h3></div><span className="status-chip">bounded · outbox</span></div>
            <p className="meta">문서를 열 때까지 기다리지 않고, 관리자 권한으로 대기 중인 Keyman·R&amp;R·이슈·고객 약속 분석을 제한된 단위로 실행합니다. 빈 응답은 추정값으로 채우지 않고 LLM abstention으로 남깁니다.</p>
            <form className="enrichment-controls" onSubmit={runEnrichment}>
              <label>작업<select aria-label="LLM 분석 작업 종류" value={enrichmentTask} onChange={(event) => setEnrichmentTask(event.target.value)} disabled={enrichmentBusy}><option value="all">전체 대기 작업</option><option value="keyman">Keyman</option><option value="product">R&amp;R · 이슈 To Do/캘린더</option><option value="appointments">고객 약속</option></select></label>
              <label>최대 문서 수<input aria-label="LLM 분석 최대 문서 수" type="number" min="1" max="64" value={enrichmentLimit} onChange={(event) => setEnrichmentLimit(event.target.value)} disabled={enrichmentBusy} /></label>
              <button id="runEnrichmentBtn" className="primary-button" type="submit" disabled={enrichmentBusy}>{enrichmentBusy ? "시작 중…" : "분석 작업 시작"}</button>
            </form>
            {enrichmentStatusMessage ? <p className="admin-status" role="status">{enrichmentStatusMessage}</p> : null}
            <div className="enrichment-status-grid">
              {[["Keyman 대기", enrichmentStatus?.pending?.keyman], ["R&R·이슈 대기", enrichmentStatus?.pending?.product], ["고객 약속 대기", enrichmentStatus?.pending?.appointments]].map(([label, value]) => <article className="policy-rule" key={label}><strong>{label}</strong><span>{enrichmentStatus ? `${formatNumber(value)}개 문서` : "상태 확인 중"}</span></article>)}
            </div>
            {(enrichmentStatus?.active_runs || []).length ? <p className="meta">실행 중: {(enrichmentStatus.active_runs || []).map((run) => `${run.task} ${run.requested}건`).join(" · ")}</p> : null}
          </section>
          <section id="reportQualityScreen" className="admin-policy-panel" aria-labelledby="reportQualityTitle">
            <div className="admin-section-heading"><div><p className="eyebrow">REPORT QUALITY</p><h3 id="reportQualityTitle">보고서 평가 품질</h3></div><span className="status-chip">LLM · fast-mlsirm</span></div>
            <p className="meta">일시적인 모델·연계 장애로 평가되지 않은 주간·월간 보고서만 다시 평가합니다. 점수를 만들 수 없으면 abstention으로 보존하며 임의의 점수를 채우지 않습니다.</p>
            <button id="refreshReportsBtn" className="primary-button" type="button" onClick={() => void refreshReports()} disabled={reportRefreshBusy}>{reportRefreshBusy ? "재평가 중…" : "보고서 재평가"}</button>
            {reportRefreshStatus ? <p className="admin-status" role="status">{reportRefreshStatus}</p> : null}
          </section>
          <section id="teppScreen" className="admin-policy-panel" aria-labelledby="teppTitle">
            <div className="admin-section-heading"><div><p className="eyebrow">TEPP HTTP PORT</p><h3 id="teppTitle">TEPP 분석 요청</h3></div><span className="status-chip">contract · v1</span></div>
            <p className="meta">TEPP는 별도 서비스입니다. 설정된 TEPP HTTPS endpoint만 호출하며, endpoint가 없을 때 기록된 응답이나 임의의 분석 결과를 만들지 않습니다.</p>
            <form className="enrichment-controls" onSubmit={submitTeppAnalysis}>
              <label>Snapshot ID<input aria-label="TEPP snapshot ID" value={teppSnapshotId} onChange={(event) => setTeppSnapshotId(event.target.value)} required maxLength={256} /></label>
              <label>Knowledge cutoff<input aria-label="TEPP knowledge cutoff" value={teppKnowledgeCutoff} onChange={(event) => setTeppKnowledgeCutoff(event.target.value)} placeholder="2026-08-15T00:00:00Z" required maxLength={64} /></label>
              <label>Idempotency key<input aria-label="TEPP idempotency key" value={teppIdempotencyKey} onChange={(event) => setTeppIdempotencyKey(event.target.value)} required maxLength={256} /></label>
              <button className="primary-button" type="submit" disabled={teppBusy || !teppStatus?.configured}>{teppBusy ? "접수 중…" : "TEPP 분석 접수"}</button>
            </form>
            <p className="admin-status" role="status">{teppStatusMessage || (teppStatus?.configured ? "TEPP endpoint configured" : "TEPP endpoint unavailable")}</p>
            <div className="enrichment-status-grid">
              {(teppStatus?.runs || []).map((run) => <article className="policy-rule" key={run.run_id}><strong>{run.run_id}</strong><span>{run.remote_state} · snapshot {run.snapshot_id}</span><button className="secondary-button" type="button" onClick={() => void refreshTeppRun(run.run_id)}>상태 갱신</button></article>)}
              {!(teppStatus?.runs || []).length ? <p className="empty">아직 접수된 TEPP 분석이 없습니다.</p> : null}
            </div>
          </section>
          <div className="admin-layout">
            <aside className="admin-account-list" aria-label="Keyverse 계정 목록">
              {adminAccounts.map((account) => <button type="button" className={`admin-account ${selectedAdminId === account.account_id ? "selected" : ""}`} key={account.account_id} onClick={() => chooseAdminAccount(account)}><strong>{account.username || account.email || account.account_id}</strong><span>{account.email || "이메일 없음"}</span><small>{account.org || "법인 미할당"} / {account.workspace || "PU 미할당"}</small><small>{account.roles?.join(" · ") || "역할 미할당"}</small></button>)}
              {!adminAccounts.length ? <p className="empty">{adminStatus ? "운영 Keyverse 연결 후 계정별 법인·PU·역할을 관리할 수 있습니다." : "관리할 Keyverse 계정이 없습니다."}</p> : null}
            </aside>
            <form className="admin-account-editor" onSubmit={saveAdminAccountClaims}>
              {(() => {
                const account = adminAccounts.find((item) => item.account_id === selectedAdminId);
                return account ? <>
                  <p className="eyebrow">ACCOUNT CLAIMS</p><h3>{account.username || account.email || account.account_id}</h3><p className="meta">{account.email} · {account.account_id}</p>
                  <label>법인 코드<input value={adminForm.org || session.corp_code} readOnly aria-readonly="true" /></label>
                  <label>PU 코드<input value={adminForm.workspace} onChange={(event) => setAdminForm({ ...adminForm, workspace: event.target.value })} placeholder="예: D02" required maxLength={64} /></label>
                  <fieldset><legend>LineageWeave 역할</legend>{adminRoles.map((role) => <label className="role-option" key={role.name}><input type="checkbox" checked={(adminForm.roles || []).includes(role.name)} onChange={(event) => setAdminForm({ ...adminForm, roles: event.target.checked ? [...new Set([...(adminForm.roles || []), role.name])] : (adminForm.roles || []).filter((item) => item !== role.name) })} /> <span>{role.name}</span>{role.description ? <small>{role.description}</small> : null}</label>)}</fieldset>
                  <button className="primary-button" type="submit" disabled={adminBusy}>{adminBusy ? "저장 중…" : "Keyverse 원장에 저장"}</button>
                </> : <p className="empty">왼쪽 계정 목록에서 계정을 선택하세요.</p>;
              })()}
            </form>
          </div>
        </section>
      )}
    </main>
  );
}
