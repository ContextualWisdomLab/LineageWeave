export const EMPTY_EMAIL_MESSAGE = "업무 이메일을 입력해 주세요.";
export const INVALID_EMAIL_MESSAGE = "올바른 업무 이메일 주소를 입력해 주세요.";

export function emailValidationMessage(value, inputIsValid) {
  if (!value) return EMPTY_EMAIL_MESSAGE;
  return inputIsValid ? "" : INVALID_EMAIL_MESSAGE;
}

export function sideText(items) {
  return (items || [])
    .map((item) => {
      if (typeof item === "string") return item;
      const actorType = String(item.actor_type || "").trim();
      const actorName = item.actor_name || item.name || item.person_name || item.organization_name || item.org_name || "";
      const organizationName = item.organization_name || item.org_name || item.org || "";
      const fields = actorType && actorType !== "person"
        ? [actorType, actorName, organizationName, item.rank || item.grade || "", item.title || item.position || ""]
        : [item.person_name || actorName, organizationName, item.rank || item.grade || "", item.title || item.position || ""];
      return fields.join(" | ").replace(/(?: \| )+$/, "");
    })
    .filter(Boolean)
    .join("\n");
}

export function sideRows(items) {
  return (items || [])
    .map((item) => {
      if (typeof item === "string") return { actor_type: "person", actor_name: item, person_name: item, org_name: "", rank: "", title: "" };
      const actorType = String(item.actor_type || (item.person_name ? "person" : item.org_name ? "organization" : "")).trim();
      const actorName = String(item.actor_name || item.name || item.person_name || item.organization_name || item.org_name || item.org || "").trim();
      return {
        actor_type: actorType,
        actor_name: actorName,
        person_name: actorType === "organization" || actorType === "team" ? "" : String(item.person_name || actorName || "").trim(),
        org_name: String(item.org_name || item.org || "").trim(),
        organization_name: String(item.organization_name || item.org_name || item.org || "").trim(),
        rank: String(item.rank || item.grade || "").trim(),
        title: String(item.title || item.position || item.job_title || "").trim(),
      };
    })
    .filter((item) => item.actor_name || item.person_name || item.org_name);
}

export function sideLabel(item) {
  const label = item.actor_type === "organization" || item.actor_type === "team" ? item.actor_name : item.person_name || item.actor_name;
  const organization = item.organization_name || item.org_name;
  return [label, organization && organization !== label ? organization : "", item.rank, item.title].filter(Boolean).join(" · ");
}

export function parseSide(value) {
  return value
    .split("\n")
    .map((line) => {
      const parts = line.split("|").map((part) => part.trim());
      const [first = "", second = "", third = "", fourth = "", ...rest] = parts;
      const actorTypes = { person: "person", organization: "organization", institution: "organization", team: "team", 기관: "organization", 조직: "organization", 팀: "team" };
      const actorType = actorTypes[first.toLowerCase()];
      if (actorType) {
        return {
          actor_type: actorType,
          actor_name: second,
          organization_name: third,
          org_name: third,
          rank: fourth,
          title: rest.join("|").trim(),
        };
      }
      return {
        person_name: first,
        org_name: second,
        rank: third,
        title: [fourth, ...rest].filter(Boolean).join("|").trim(),
      };
    })
    .filter((item) => item.actor_name || item.person_name || item.org_name);
}

export function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

export function visibilityLabel(value) {
  return { public: "공개", private: "내부" }[String(value || "").trim().toLowerCase()] || "공개 범위 확인";
}

export function lineageRelationLabel(value) {
  const relation = String(value || "").trim();
  return relation === "shared_thread_identifier" ? "같은 스레드 단서" : relation || "관련성";
}

export function isInspectableAsset(asset) {
  return Boolean(asset?.inspection_eligible);
}

export function canPreviewAsset(asset) {
  return String(asset?.mime_type || "").startsWith("image/")
    && Number(asset?.encoded_bytes || 0) * 3 / 4 <= 6 * 1024 * 1024;
}

export function semanticValue(value) {
  if (value === undefined || value === null || value === "") return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}

const KNOWLEDGE_NODE_TYPE_LABELS = {
  document: "글",
  event: "이벤트",
  organization: "조직",
  organization_alias: "조직 별칭",
  person: "사람",
  pu: "PU",
  team: "팀",
};

const KNOWLEDGE_RELATION_LABELS = {
  cross_corp_same_pu_thread: "서로 다른 회사·같은 PU 간 대화",
  cross_corp_same_pu_transaction: "서로 다른 회사·같은 PU 간 거래",
  cross_corp_thread: "서로 다른 회사 간 대화",
  cross_corp_transaction: "서로 다른 회사 간 거래",
  cross_pu_thread: "같은 회사·다른 PU 간 대화",
  cross_pu_transaction: "같은 회사·다른 PU 간 거래",
  identity_name_match: "이름 일치",
};

const KNOWLEDGE_EVIDENCE_LABELS = {
  inferred: "추론 근거",
  observed: "관측 근거",
  predicted: "예측 근거",
  verified: "검증 근거",
};

export function knowledgeEdgeRows(knowledge = {}) {
  const nodes = Array.isArray(knowledge?.nodes) ? knowledge.nodes : [];
  const edges = Array.isArray(knowledge?.edges) ? knowledge.edges : [];
  const nodesById = new Map(nodes.flatMap((node) => {
    const id = String(node?.id || "").trim();
    const label = String(node?.label || "").trim();
    return id && label ? [[id, { ...node, label }]] : [];
  }));

  return edges.flatMap((edge) => {
    const source = nodesById.get(String(edge?.source || "").trim());
    const target = nodesById.get(String(edge?.target || "").trim());
    const relation = String(edge?.relation || "").trim();
    if (!source || !target || !relation) return [];
    const sourceType = String(source.type || "node").trim() || "node";
    const targetType = String(target.type || "node").trim() || "node";
    const evidenceStatus = String(edge.evidence_status || "").trim();
    return [{
      evidenceLabel: KNOWLEDGE_EVIDENCE_LABELS[evidenceStatus] || "근거 상태 미상",
      relation,
      relationLabel: KNOWLEDGE_RELATION_LABELS[relation] || "근거 기반 연결",
      sourceLabel: source.label,
      sourceType,
      sourceTypeLabel: KNOWLEDGE_NODE_TYPE_LABELS[sourceType] || sourceType,
      targetLabel: target.label,
      targetType,
      targetTypeLabel: KNOWLEDGE_NODE_TYPE_LABELS[targetType] || targetType,
    }];
  });
}

export function counterpartVocExcerpts(appointments = [], counterparts = []) {
  const rows = (Array.isArray(appointments) ? appointments : []).filter((item) => String(item?.excerpt || "").trim());
  const names = (Array.isArray(counterparts) ? counterparts : [])
    .flatMap((item) => [item?.actor_name, item?.person_name, item?.org_name, item?.organization_name])
    .map((value) => String(value || "").trim().toLowerCase())
    .filter(Boolean);
  if (!names.length) return rows.slice(0, 8);
  const matched = rows.filter((item) => {
    const blob = `${item.excerpt || ""} ${item.label || ""}`.toLowerCase();
    return names.some((name) => blob.includes(name));
  });
  return (matched.length ? matched : rows).slice(0, 8);
}

export function partitionLineageBeads(beads = []) {
  const segments = [];
  const observations = [];
  let segment = [];
  for (const bead of Array.isArray(beads) ? beads : []) {
    segment.push(bead);
    if (bead?.connects_to_next === true) continue;
    if (segment.length > 1) segments.push(segment);
    else observations.push(segment[0]);
    segment = [];
  }
  if (segment.length > 1) segments.push(segment);
  else if (segment.length) observations.push(segment[0]);
  return { segments, observations };
}

export function customerTreeRows(accounts = [], edges = []) {
  const accountByName = new Map(accounts.map((account) => [String(account.account_name || ""), account]));
  const childrenByParent = new Map();
  edges.forEach((edge) => {
    const parent = String(edge.parent || "");
    const child = String(edge.child || "");
    if (!accountByName.has(parent) || !accountByName.has(child)) return;
    const children = childrenByParent.get(parent) || [];
    children.push(child);
    childrenByParent.set(parent, children);
  });
  const rows = [];
  const visited = new Set();
  const visit = (name, depth) => {
    if (!name || visited.has(name)) return;
    visited.add(name);
    rows.push({ account: accountByName.get(name), depth });
    (childrenByParent.get(name) || []).forEach((child) => visit(child, depth + 1));
  };
  const names = [...accountByName.keys()];
  names
    .filter((name) => !accountByName.get(name)?.parent_name || !accountByName.has(accountByName.get(name).parent_name))
    .forEach((name) => visit(name, 0));
  names.forEach((name) => visit(name, 0));
  return rows;
}
