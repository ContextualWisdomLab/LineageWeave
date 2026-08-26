#!/usr/bin/env python3
"""Build the deterministic static LineageWeave ontology documentation site.

The governed Turtle source tree remains authoritative. This builder publishes a
human-readable, fragment-addressable HTML view plus equivalent JSON-LD and
N-Triples files without introducing a second ontology source of truth.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Any

try:
    from scripts.ontology_site_contract import public_fragment
except ModuleNotFoundError:  # direct execution with ``scripts`` as sys.path[0]
    from ontology_site_contract import public_fragment

from rdflib import Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.namespace import OWL, RDF, RDFS, SKOS

PUBLIC_BASE_URL = "https://contextualwisdomlab.github.io/LineageWeave"
DOCUMENTATION_URL = f"{PUBLIC_BASE_URL}/ontology"
#: ADR 0207: the canonical namespace is the repository-case spelling --
#: the exact project path GitHub Pages serves. The lowercase form is a
#: deprecated compatibility vocabulary published beside the ontology.
CANONICAL_LOOKUP_PREDICATE = (
    "https://contextualwisdomlab.github.io/LineageWeave/ontology#lookupCode"
)
CANONICAL_FJA_DOMAIN_PREDICATE = URIRef(
    "https://contextualwisdomlab.github.io/LineageWeave/ontology#fjaDomain"
)
CANONICAL_FJA_RANK_PREDICATE = URIRef(
    "https://contextualwisdomlab.github.io/LineageWeave/ontology#fjaRank"
)
SHAPES_RELATIVE_PATH = Path("docs/ontology/lineageweave-kg-shapes.ttl")
CANONICAL_LINK_SUPPRESSION = (
    "<!-- nosemgrep: html.security.audit.missing-integrity.missing-integrity "
    "-- canonical metadata fetches no subresource -->"
)
SOURCE_RELATIVE_PATH = Path("docs/ontology/lineageweave-kg.ttl")
SOURCE_FRAGMENT_RELATIVE_PATHS = (Path("docs/ontology/soc-2018-structure.ttl"),)
PROV_PROFILE_RELATIVE_PATH = Path("docs/ontology/prov-o-support-profile.ttl")
COMPATIBILITY_RELATIVE_PATH = Path("docs/ontology/namespace-compatibility.ttl")
TERM_TYPES: tuple[tuple[str, URIRef], ...] = (
    ("Classes", OWL.Class),
    ("Object properties", OWL.ObjectProperty),
    ("Datatype properties", OWL.DatatypeProperty),
    ("Annotation properties", OWL.AnnotationProperty),
    ("Concept schemes", SKOS.ConceptScheme),
    ("Concepts", SKOS.Concept),
)
RELATION_FIELDS: tuple[tuple[str, URIRef], ...] = (
    ("Subclass of", RDFS.subClassOf),
    ("Domain", RDFS.domain),
    ("Range", RDFS.range),
    ("Inverse of", OWL.inverseOf),
    ("Broader", SKOS.broader),
    ("Narrower", SKOS.narrower),
    ("In scheme", SKOS.inScheme),
)


def _sha256(path: Path) -> str:
    """Return a lowercase SHA-256 digest for one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fragment(value: URIRef) -> str:
    """Return the stable local fragment used as the HTML anchor."""
    iri = str(value)
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rstrip("/").rsplit("/", 1)[-1]


def _preferred_literal(graph: Graph, subject: URIRef, predicate: URIRef) -> str | None:
    """Choose an English, untagged, or first literal in a deterministic order."""
    literals = sorted(
        (value for value in graph.objects(subject, predicate) if isinstance(value, Literal)),
        key=lambda value: (
            0 if value.language == "en" else 1 if value.language is None else 2,
            value.language or "",
            str(value),
        ),
    )
    return str(literals[0]) if literals else None


def _canonicalize_json(value: Any, parent_key: str | None = None) -> Any:
    """Canonicalize JSON-LD while preserving explicit ``@list`` ordering."""
    if isinstance(value, dict):
        return {key: _canonicalize_json(value[key], key) for key in sorted(value)}
    if isinstance(value, list):
        canonical = [_canonicalize_json(item, parent_key) for item in value]
        if parent_key == "@list":
            return canonical
        return sorted(
            canonical,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    return value


def _write_serializations(graph: Graph, ontology_dir: Path) -> str:
    """Write deterministic serializations and return canonical RDF lines."""
    canonical_graph = to_canonical_graph(graph)
    raw_jsonld = canonical_graph.serialize(format="json-ld", auto_compact=False)
    parsed_jsonld = json.loads(raw_jsonld)
    canonical_jsonld = _canonicalize_json(parsed_jsonld)
    (ontology_dir / "ontology.jsonld").write_text(
        json.dumps(canonical_jsonld, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    raw_nt = canonical_graph.serialize(format="nt")
    nt_lines = sorted(line.strip() for line in raw_nt.splitlines() if line.strip())
    (ontology_dir / "ontology.nt").write_text(
        "\n".join(nt_lines) + "\n",
        encoding="utf-8",
    )
    return "\n".join(nt_lines) + "\n"


def _render_link(value: URIRef, ontology_subjects: set[URIRef]) -> str:
    """Render a local term link or a non-navigating external RDF identifier."""
    if value not in ontology_subjects:
        return f"<code>{html.escape(str(value))}</code>"
    href = html.escape(f"#{public_fragment(_fragment(value))}", quote=True)
    return f'<a href="{href}">{html.escape(_fragment(value))}</a>'


def _render_relation_rows(
    graph: Graph,
    subject: URIRef,
    ontology_subjects: set[URIRef],
) -> str:
    """Render standard semantic relations for one term."""
    rows: list[str] = []
    for heading, predicate in RELATION_FIELDS:
        values = sorted(
            (value for value in graph.objects(subject, predicate) if isinstance(value, URIRef)),
            key=str,
        )
        if not values:
            continue
        rendered = ", ".join(_render_link(value, ontology_subjects) for value in values)
        rows.append(f"<dt>{html.escape(heading)}</dt><dd>{rendered}</dd>")
    return "".join(rows)


def _render_term(graph: Graph, subject: URIRef, ontology_subjects: set[URIRef]) -> str:
    """Render one fragment-addressable ontology term section."""
    raw_fragment = _fragment(subject)
    fragment_href = public_fragment(raw_fragment)
    label = (
        _preferred_literal(graph, subject, RDFS.label)
        or _preferred_literal(graph, subject, SKOS.prefLabel)
        or raw_fragment
    )
    comment = _preferred_literal(graph, subject, SKOS.definition) or _preferred_literal(
        graph, subject, RDFS.comment
    )
    lookup_predicate = URIRef(CANONICAL_LOOKUP_PREDICATE)
    lookup_codes = sorted(str(value) for value in graph.objects(subject, lookup_predicate))
    type_values = sorted(
        (value for value in graph.objects(subject, RDF.type) if isinstance(value, URIRef)),
        key=str,
    )
    relation_rows = _render_relation_rows(graph, subject, ontology_subjects)
    type_links = ", ".join(_render_link(value, ontology_subjects) for value in type_values)
    lookup_row = (
        "<dt>Lookup code</dt><dd>"
        + "".join(f"<code>{html.escape(code)}</code>" for code in lookup_codes)
        + "</dd>"
        if lookup_codes
        else ""
    )
    fja_rows = "".join(
        f"<dt>{heading}</dt><dd><code>{html.escape(value)}</code></dd>"
        for heading, predicate in (
            ("FJA domain", CANONICAL_FJA_DOMAIN_PREDICATE),
            ("FJA rank", CANONICAL_FJA_RANK_PREDICATE),
        )
        if (value := _preferred_literal(graph, subject, predicate)) is not None
    )
    comment_html = (
        f'<p class="term-comment">{html.escape(comment)}</p>' if comment else ""
    )
    return (
        f'<article class="term-card" id="{html.escape(raw_fragment, quote=True)}">'
        f'<h3><a class="fragment-link" href="#{html.escape(fragment_href, quote=True)}" '
        f'aria-label="Link to {html.escape(label, quote=True)}">#</a> '
        f"{html.escape(label)}</h3>"
        f'<p class="iri"><code>{html.escape(str(subject))}</code></p>'
        f"{comment_html}"
        '<dl class="term-facts">'
        f"<dt>RDF type</dt><dd>{type_links or '<span>Unspecified</span>'}</dd>"
        f"{lookup_row}"
        f"{fja_rows}"
        f"{relation_rows}"
        "</dl>"
        "</article>"
    )


def _ontology_subjects(graph: Graph) -> set[URIRef]:
    """Return every URI subject that belongs in the generated term inventory."""
    subjects: set[URIRef] = set()
    for _, rdf_type in TERM_TYPES:
        subjects.update(
            subject
            for subject in graph.subjects(RDF.type, rdf_type)
            if isinstance(subject, URIRef)
        )
    return subjects


def _render_term_sections(graph: Graph) -> tuple[str, str, int]:
    """Render the navigation and categorized term sections."""
    subjects = _ontology_subjects(graph)
    nav_items: list[str] = []
    sections: list[str] = []
    counted: set[URIRef] = set()

    for heading, rdf_type in TERM_TYPES:
        terms = sorted(
            (
                subject
                for subject in graph.subjects(RDF.type, rdf_type)
                if isinstance(subject, URIRef)
            ),
            key=lambda subject: (
                (
                    _preferred_literal(graph, subject, RDFS.label)
                    or _preferred_literal(graph, subject, SKOS.prefLabel)
                    or _fragment(subject)
                ).casefold(),
                str(subject),
            ),
        )
        terms = [term for term in terms if term not in counted]
        if not terms:
            continue
        section_id = heading.lower().replace(" ", "-")
        nav_items.append(
            f'<li><a href="#{section_id}">{html.escape(heading)} '
            f"<span>{len(terms)}</span></a></li>"
        )
        cards: list[str] = []
        for term in terms:
            counted.add(term)
            cards.append(_render_term(graph, term, subjects))
        sections.append(
            f'<section class="term-section" id="{section_id}">'
            f"<h2>{html.escape(heading)}</h2>"
            '<div class="term-grid">' + "".join(cards) + "</div>"
            "</section>"
        )
    return "".join(nav_items), "".join(sections), len(counted)


def _ontology_metadata(graph: Graph) -> tuple[str, str, str]:
    """Return ontology IRI, label, and comment from the source graph."""
    ontology_nodes = sorted(
        (
            subject
            for subject in graph.subjects(RDF.type, OWL.Ontology)
            if isinstance(subject, URIRef)
        ),
        key=str,
    )
    if not ontology_nodes:
        raise ValueError("source graph does not declare an owl:Ontology resource")
    subject = ontology_nodes[0]
    label = _preferred_literal(graph, subject, RDFS.label) or "LineageWeave ontology"
    comment = _preferred_literal(graph, subject, RDFS.comment) or (
        "Formal OWL 2, RDF Schema, and SKOS vocabulary for LineageWeave."
    )
    return str(subject), label, comment


def _style_sheet() -> str:
    """Return the self-contained accessible stylesheet."""
    return """
:root { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; line-height: 1.55; }
* { box-sizing: border-box; }
body { margin: 0; color: #172033; background: #f5f7fb; }
a { color: #174ea6; }
a:focus-visible, button:focus-visible { outline: 3px solid #f2b705; outline-offset: 3px; }
header { color: white; background: #102a43; padding: 3rem max(1.25rem, calc((100vw - 78rem)/2)); }
header p { max-width: 70ch; color: #d9e8f5; }
header a { color: #fff; }
header code { overflow-wrap: anywhere; }
main { max-width: 78rem; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
.downloads, .summary-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); }
.downloads a, .summary-card { display: block; padding: 1rem; border: 1px solid #c8d2df; border-radius: .75rem; background: #fff; }
.downloads a { text-decoration: none; font-weight: 700; }
.on-this-page { margin: 2rem 0; padding: 1rem 1.25rem; border-left: .35rem solid #2b6cb0; background: #eaf2fb; }
.on-this-page ul { display: flex; flex-wrap: wrap; gap: .65rem 1.25rem; list-style: none; padding: 0; }
.on-this-page span { font-variant-numeric: tabular-nums; }
.term-section { scroll-margin-top: 1rem; margin-top: 3rem; }
.term-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 25rem), 1fr)); gap: 1rem; }
.term-card { scroll-margin-top: 1rem; padding: 1.15rem; border: 1px solid #c8d2df; border-radius: .75rem; background: #fff; box-shadow: 0 1px 2px rgb(16 42 67 / 8%); }
.term-card h3 { margin-top: 0; }
.fragment-link { text-decoration: none; opacity: .55; }
.iri { overflow-wrap: anywhere; }
.term-comment { white-space: pre-wrap; }
.term-facts { display: grid; grid-template-columns: minmax(7rem, max-content) 1fr; gap: .35rem .75rem; }
.term-facts dt { font-weight: 700; }
.term-facts dd { margin: 0; overflow-wrap: anywhere; }
.term-facts code + code { margin-left: .35rem; }
.notice { padding: 1rem; border-radius: .75rem; background: #fff7d6; border: 1px solid #e6c75b; }
footer { border-top: 1px solid #c8d2df; padding: 2rem 1.25rem; text-align: center; }
@media (prefers-color-scheme: dark) {
  body { color: #e8eef5; background: #0b1522; }
  header { background: #06111d; }
  a { color: #8fc2ff; }
  .downloads a, .summary-card, .term-card { background: #122236; border-color: #38516a; }
  .on-this-page { background: #102a43; }
  .notice { background: #3d3212; border-color: #8a712b; }
  footer { border-color: #38516a; }
}
@media print {
  body { background: white; color: black; }
  header { background: white; color: black; padding: 1rem 0; }
  header p { color: black; }
  main { max-width: none; padding: 0; }
  .term-card { break-inside: avoid; box-shadow: none; }
}
""".strip()


def _render_ontology_page(graph: Graph, source_sha256: str) -> tuple[str, int]:
    """Render the complete ontology documentation page and unique term count."""
    ontology_iri, label, comment = _ontology_metadata(graph)
    nav, term_sections, term_count = _render_term_sections(graph)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(label)}</title>\n"
        f'<meta name="description" content="{html.escape(comment, quote=True)}">\n'
        f'<link rel="canonical" href="{DOCUMENTATION_URL}"> '
        f"{CANONICAL_LINK_SUPPRESSION}\n"
        '<link rel="alternate" type="text/turtle" href="ontology.ttl" title="Turtle">\n'
        '<link rel="alternate" type="application/ld+json" href="ontology.jsonld" title="JSON-LD">\n'
        '<link rel="alternate" type="application/n-triples" href="ontology.nt" title="N-Triples">\n'
        f"<style>{_style_sheet()}</style>\n"
        "</head>\n<body>\n"
        "<header>"
        '<p><a href="../">LineageWeave</a> / Ontology</p>'
        f"<h1>{html.escape(label)}</h1>"
        f"<p>{html.escape(comment)}</p>"
        f'<p>Ontology IRI: <code>{html.escape(ontology_iri)}</code></p>'
        "</header>"
        "<main>"
        '<section aria-labelledby="downloads-heading">'
        '<h2 id="downloads-heading">Machine-readable artifacts</h2>'
        '<div class="downloads">'
        '<a href="ontology.ttl" type="text/turtle">Turtle <small>generated equivalent</small></a>'
        '<a href="ontology.jsonld" type="application/ld+json">JSON-LD <small>generated equivalent</small></a>'
        '<a href="ontology.nt" type="application/n-triples">N-Triples <small>generated equivalent</small></a>'
        '<a href="prov-o-support-profile.ttl" type="text/turtle">PROV-O support profile</a>'
        '<a href="namespace-compatibility.ttl" type="text/turtle">Deprecated namespace compatibility</a>'
        '<a href="lineageweave-kg-shapes.ttl" type="text/turtle">SHACL shapes</a>'
        '<a href="manifest.json" type="application/json">Build manifest</a>'
        "</div></section>"
        '<section class="summary-grid" aria-label="Ontology publication summary">'
        f'<div class="summary-card"><strong>{term_count}</strong><br>Unique documented terms</div>'
        f'<div class="summary-card"><strong>{len(graph)}</strong><br>RDF triples</div>'
        f'<div class="summary-card"><strong><code>{html.escape(source_sha256[:12])}</code></strong><br>Source SHA-256 prefix</div>'
        "</section>"
        '<p class="notice"><strong>Identity boundary:</strong> this project page is the stable documentation endpoint requested for the repository. Per ADR 0207 the repository-case ontology IRI shown above is the canonical semantic identifier; the lowercase namespace remains a deprecated compatibility vocabulary with validated mappings.</p>'
        '<nav class="on-this-page" aria-label="Ontology term categories"><strong>Term categories</strong><ul>'
        f"{nav}</ul></nav>"
        f"{term_sections}"
        "</main>"
        '<footer><p>Generated deterministically from the governed <code>docs/ontology/</code> source tree. No analytics or external scripts.</p></footer>'
        "</body>\n</html>\n",
        term_count,
    )


def _render_root_page() -> str:
    """Render the project Pages landing page with a direct ontology action."""
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>LineageWeave public specifications</title>"
        f'<link rel="canonical" href="{PUBLIC_BASE_URL}/">'
        f"{CANONICAL_LINK_SUPPRESSION}"
        f"<style>{_style_sheet()}</style></head><body>"
        "<header><h1>LineageWeave public specifications</h1>"
        "<p>Stable, machine-readable public artifacts published from the protected repository source.</p></header>"
        '<main><section><h2>Ontology</h2><p>Inspect the OWL 2, RDF Schema, SKOS, and provenance vocabulary.</p>'
        '<p><a href="ontology/">Open the ontology documentation</a></p></section></main>'
        "<footer><p>ContextualWisdomLab / LineageWeave</p></footer>"
        "</body></html>\n"
    )


def _write_manifest(
    ontology_dir: Path,
    sources: tuple[Path, ...],
    graph: Graph,
    term_count: int,
) -> None:
    """Write deterministic provenance metadata for the published ontology."""
    payload = {
        "documentation_url": DOCUMENTATION_URL,
        "generated_artifacts": [
            "index.html",
            "lineageweave-kg-shapes.ttl",
            "manifest.json",
            "namespace-compatibility.ttl",
            "ontology.jsonld",
            "ontology.nt",
            "ontology.ttl",
            "prov-o-support-profile.ttl",
        ],
        "shapes_path": SHAPES_RELATIVE_PATH.as_posix(),
        "ontology_triple_count": len(graph),
        "ontology_ttl_sha256": _sha256(ontology_dir / "ontology.ttl"),
        "ontology_unique_term_count": term_count,
        "source_tree_sha256": hashlib.sha256(
            b"".join(source.read_bytes() for source in sources)
        ).hexdigest(),
        "source_files": [
            {"path": path.as_posix(), "sha256": _sha256(source)}
            for path, source in zip(
                (SOURCE_RELATIVE_PATH, *SOURCE_FRAGMENT_RELATIVE_PATHS),
                sources,
                strict=True,
            )
        ],
    }
    (ontology_dir / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_site(repository_root: Path, output_dir: Path) -> None:
    """Build the complete static ontology site under ``output_dir``."""
    root = repository_root.resolve()
    output = output_dir.resolve()
    source = root / SOURCE_RELATIVE_PATH
    fragments = tuple(root / path for path in SOURCE_FRAGMENT_RELATIVE_PATHS)
    prov_profile = root / PROV_PROFILE_RELATIVE_PATH
    compatibility = root / COMPATIBILITY_RELATIVE_PATH
    shapes = root / SHAPES_RELATIVE_PATH
    if not source.is_file():
        raise FileNotFoundError(f"ontology source is missing: {source}")
    if not prov_profile.is_file():
        raise FileNotFoundError(f"PROV-O support profile is missing: {prov_profile}")
    if not compatibility.is_file():
        raise FileNotFoundError(f"namespace compatibility vocabulary is missing: {compatibility}")
    if not shapes.is_file():
        raise FileNotFoundError(f"SHACL shapes graph is missing: {shapes}")
    for fragment in fragments:
        if not fragment.is_file():
            raise FileNotFoundError(f"ontology source fragment is missing: {fragment}")

    if output.exists():
        raise FileExistsError(
            "refusing to replace an existing output directory; "
            "use publish_ontology_site for marked replacement"
        )
    ontology_dir = output / "ontology"
    ontology_dir.mkdir(parents=True)

    graph = Graph().parse(source, format="turtle")
    for fragment in fragments:
        graph.parse(fragment, format="turtle")
    sources = (source, *fragments)
    source_sha256 = hashlib.sha256(
        b"".join(path.read_bytes() for path in sources)
    ).hexdigest()
    ontology_html, term_count = _render_ontology_page(graph, source_sha256)

    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "index.html").write_text(_render_root_page(), encoding="utf-8")
    (ontology_dir / "index.html").write_text(ontology_html, encoding="utf-8")
    shutil.copyfile(prov_profile, ontology_dir / "prov-o-support-profile.ttl")
    shutil.copyfile(compatibility, ontology_dir / "namespace-compatibility.ttl")
    shutil.copyfile(shapes, ontology_dir / "lineageweave-kg-shapes.ttl")
    canonical_rdf = _write_serializations(graph, ontology_dir)
    # N-Triples is a strict subset of Turtle. Publishing the canonical graph
    # avoids joining independent Turtle documents whose prefix/base scopes
    # are document-local, while retaining a deterministic .ttl representation.
    (ontology_dir / "ontology.ttl").write_text(canonical_rdf, encoding="utf-8")
    _write_manifest(ontology_dir, sources, graph, term_count)
    (output / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: " f"{PUBLIC_BASE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )
    (output / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{PUBLIC_BASE_URL}/</loc></url>\n"
        f"  <url><loc>{DOCUMENTATION_URL}</loc></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for repository and output locations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="LineageWeave repository root (default: inferred from this script)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_site"),
        help="Static site output directory (default: _site)",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    """Build the site from CLI arguments and return a process exit code."""
    args = _parse_args(argv)
    build_site(args.repository_root, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
