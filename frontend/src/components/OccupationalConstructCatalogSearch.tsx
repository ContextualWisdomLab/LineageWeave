import { useState } from "react";
import type { FormEvent } from "react";
import {
  BackendError,
  fetchOccupationalConstructSearch,
  type OccupationalConstructSearchHit,
  type OccupationalConstructSearchPage,
} from "../api";
import {
  occupationalConstructFormat,
  occupationalConstructText as text,
  type OccupationalConstructCopyKey,
} from "../occupationalConstructI18n";

export type OccupationalConstructCatalogSearchStatus =
  | "idle"
  | "loading"
  | "ready"
  | "empty"
  | "error";

const FAMILY_OPTIONS: { value: string; label: OccupationalConstructCopyKey }[] = [
  { value: "", label: "All families" },
  { value: "cognitive_ability", label: "Cognitive ability" },
  { value: "work_style", label: "Work style" },
  { value: "work_activity", label: "Work activity" },
];

const FAMILY_BADGE: Record<string, OccupationalConstructCopyKey> = {
  cognitive_ability: "Cognitive ability",
  work_style: "Work style",
  work_activity: "Work activity",
};

export type OccupationalConstructCatalogSearchProps = {
  accessToken?: string;
  knowledgeCutoff?: string;
  page?: OccupationalConstructSearchPage | null;
  status?: OccupationalConstructCatalogSearchStatus;
  onSelectPost?: (postId: string) => void;
};

/**
 * Find assertion-backed catalog labels, then open the supporting record.
 */
export function OccupationalConstructCatalogSearch({
  accessToken,
  knowledgeCutoff,
  page: provided,
  status: providedStatus,
  onSelectPost,
}: OccupationalConstructCatalogSearchProps) {
  const [query, setQuery] = useState(provided?.query ?? "");
  const [family, setFamily] = useState(provided?.family_code ?? "");
  const [page, setPage] = useState<OccupationalConstructSearchPage | null>(provided ?? null);
  const [status, setStatus] = useState<OccupationalConstructCatalogSearchStatus>(
    providedStatus ?? (provided ? (provided.hits.length ? "ready" : "empty") : "idle"),
  );

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setPage(null);
      setStatus("idle");
      return;
    }
    if (!accessToken) {
      setPage(null);
      setStatus("error");
      return;
    }
    setStatus("loading");
    try {
      const result = await fetchOccupationalConstructSearch(accessToken, {
        query: trimmed,
        family: family || undefined,
        knowledgeCutoff,
      });
      setPage(result);
      setStatus(result.hits.length ? "ready" : "empty");
    } catch (error: unknown) {
      setPage(null);
      if (error instanceof BackendError && error.status === 422) {
        setStatus("idle");
        return;
      }
      setStatus("error");
    }
  }

  async function onMore() {
    if (!accessToken || !page?.next_cursor) return;
    setStatus("loading");
    try {
      const result = await fetchOccupationalConstructSearch(accessToken, {
        query: page.query,
        family: page.family_code || undefined,
        knowledgeCutoff,
        cursor: page.next_cursor,
      });
      setPage({ ...result, hits: [...page.hits, ...result.hits] });
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }

  return (
    <section
      className="occupational-construct-catalog-search"
      aria-labelledby="occupational-construct-catalog-search-heading"
    >
      <h3 id="occupational-construct-catalog-search-heading">{text("Find work evidence")}</h3>
      <form className="occupational-construct-catalog-search-form" onSubmit={onSubmit}>
        <label className="ontology-search">
          {text("Catalog label")}
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label={text("Catalog label")}
            autoComplete="off"
          />
        </label>
        <label className="ontology-search">
          {text("Work-evidence family")}
          <select
            value={family}
            onChange={(event) => setFamily(event.target.value)}
            aria-label={text("Work-evidence family")}
          >
            {FAMILY_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {text(option.label)}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">{text("Find matching records")}</button>
      </form>
      {statusMessage(status)}
      {status === "ready" && page && page.hits.length > 0 ? (
        <>
          <ul className="ticket-list" aria-labelledby="occupational-construct-catalog-search-heading">
            {page.hits.map((hit) => (
              <CatalogHitItem key={hit.construct_id} hit={hit} onSelectPost={onSelectPost} />
            ))}
          </ul>
          {page.next_cursor ? (
            <button type="button" onClick={onMore}>{text("Show more matching records")}</button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function statusMessage(status: OccupationalConstructCatalogSearchStatus) {
  const messages: Record<OccupationalConstructCatalogSearchStatus, string> = {
    idle: text("Type two or more letters of a catalog label, then open the supporting record."),
    loading: text("Finding work evidence..."),
    ready: "",
    empty: text("No visible work evidence matches. Open a record with work evidence next."),
    error: text("Work-evidence search is unavailable. Open a visible record next."),
  };
  const message = messages[status];
  if (!message) return null;
  return (
    <p className={`ontology-status ontology-status-${status}`} role="status">
      {message}
    </p>
  );
}

function CatalogHitItem({
  hit,
  onSelectPost,
}: {
  hit: OccupationalConstructSearchHit;
  onSelectPost?: (postId: string) => void;
}) {
  const familyLabel = text(FAMILY_BADGE[hit.construct_family_code] ?? "Work evidence");
  return (
    <li className="ticket-list-item">
      <button
        type="button"
        className="post-list-item"
        aria-label={occupationalConstructFormat("Open supporting record: {label} · {title}", {
          label: hit.preferred_label,
          title: hit.supporting_post_title,
        })}
        onClick={() => onSelectPost?.(hit.supporting_post_id)}
      >
        <span className="ticket-title">
          {hit.preferred_label} · {hit.supporting_post_title}
        </span>
        <span className="post-badge">{familyLabel}</span>
        <span className="post-badge">{text("Open the supporting record")}</span>
        <q className="post-meta">{hit.evidence_text}</q>
      </button>
    </li>
  );
}
