"""Apply and verify PR 343 contract-integrity and stack-consolidation fixes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one repository command and surface captured output."""

    completed = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace one known fragment or fail closed when the contributor head moved."""

    if new in text:
        return text
    if text.count(old) != 1:
        raise SystemExit(f"refusing unknown {label} shape")
    return text.replace(old, new, 1)


def _add_regressions() -> None:
    """Add authorization, malformed-provider, and LLM invocation tests first."""

    reconstruct_path = ROOT / "tests/test_reconstruct.py"
    reconstruct = reconstruct_path.read_text(encoding="utf-8")
    reconstruct = _replace_once(
        reconstruct,
        "from lineageweave import Record, reconstruct\n",
        "from lineageweave import Record, reconstruct\nfrom lineageweave.adjudication_client import AdjudicationClientError\n",
        label="reconstruct adjudication import",
    )
    anchor = '''def test_candidate_window_bounds_which_priors_are_considered() -> None:
'''
    regression = '''class _MalformedAdjudicationClient:
    """Provider boundary that returns no usable confidence for any pair."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Raise the typed provider-shape error used by the production client."""

        raise AdjudicationClientError("verbose provider reply")


def test_core_reconstruction_degrades_one_malformed_llm_pair_to_zero() -> None:
    """The legacy core must not abort a whole group on one malformed reply."""

    trees = reconstruct(sample_records(), llm=_MalformedAdjudicationClient())

    assert trees
    assert all(
        edge.channel_scores.get("llm") == 0.0
        for tree in trees
        for edge in tree.edges
    )


'''
    if regression not in reconstruct:
        if anchor not in reconstruct:
            raise SystemExit("refusing unknown reconstruct test insertion point")
        reconstruct = reconstruct.replace(anchor, regression + anchor, 1)
    reconstruct_path.write_text(reconstruct, encoding="utf-8")

    analysis_path = ROOT / "tests/test_external_lineage_analysis.py"
    analysis = analysis_path.read_text(encoding="utf-8")
    anchor = '''def test_project_projection_is_proposed_and_uses_only_included_evidence() -> None:
'''
    regression = '''def test_llm_status_is_not_invoked_without_an_inferred_candidate_pair() -> None:
    client = CountingLlm()
    request = _request(
        [
            _record(
                "email:single",
                "One bounded record",
                "2026-08-20T09:00:00Z",
            )
        ],
        allow_llm=True,
    )

    result = analyze_external_lineage(request, llm=client)

    assert client.call_count == 0
    assert result.llm_status_code == "not_invoked"
    assert result.edges == ()


'''
    if regression not in analysis:
        if anchor not in analysis:
            raise SystemExit("refusing unknown external analysis insertion point")
        analysis = analysis.replace(anchor, regression + anchor, 1)
    analysis_path.write_text(analysis, encoding="utf-8")

    contract_path = ROOT / "tests/test_external_lineage_contract.py"
    contract = contract_path.read_text(encoding="utf-8")
    contract = _replace_once(
        contract,
        '        "analysis_id": "analysis:demo-001",\n        "analysis_scope_code": "email_lineage",\n',
        '        "analysis_id": "analysis:demo-001",\n        "authorization_scope_ref": "authorization-scope:opaque",\n        "analysis_scope_code": "email_lineage",\n',
        label="contract payload authorization scope",
    )
    contract = _replace_once(
        contract,
        '    assert request.analysis_id == "analysis:demo-001"\n    assert request.analysis_scope_code == "email_lineage"\n',
        '    assert request.analysis_id == "analysis:demo-001"\n    assert request.authorization_scope_ref == "authorization-scope:opaque"\n    assert request.analysis_scope_code == "email_lineage"\n',
        label="authorization parse assertion",
    )
    contract = _replace_once(
        contract,
        '        "analysis_scope_code": payload["analysis_scope_code"],\n        "analysis_id": payload["analysis_id"],\n',
        '        "analysis_scope_code": payload["analysis_scope_code"],\n        "authorization_scope_ref": payload["authorization_scope_ref"],\n        "analysis_id": payload["analysis_id"],\n',
        label="reordered authorization scope",
    )
    schema_anchor = '''    assert schema["additionalProperties"] is False
'''
    schema_assertion = '''    assert "authorization_scope_ref" in schema["required"]
    assert schema["properties"]["authorization_scope_ref"] == {
        "$ref": "#/$defs/OpaqueReference"
    }
    assert "not_invoked" in schema["$defs"]["LineageAnalysisResult"][
        "properties"
    ]["llm_status_code"]["enum"]
'''
    if schema_assertion not in contract:
        if schema_anchor not in contract:
            raise SystemExit("refusing unknown schema assertion point")
        contract = contract.replace(schema_anchor, schema_anchor + schema_assertion, 1)
    missing_anchor = '''    payload = _payload()
    del payload["analysis_id"]
    with pytest.raises(LineageContractError) as missing:
        parse_lineage_analysis_request(payload)
    assert missing.value.code == "missing_field"
'''
    missing_replacement = missing_anchor + '''
    payload = _payload()
    del payload["authorization_scope_ref"]
    with pytest.raises(LineageContractError) as missing_scope:
        parse_lineage_analysis_request(payload)
    assert missing_scope.value.code == "missing_field"
'''
    contract = _replace_once(
        contract,
        missing_anchor,
        missing_replacement,
        label="authorization required-field regression",
    )
    unsafe_anchor = '''def test_parser_rejects_invalid_policy_values(
'''
    unsafe_test = '''def test_parser_rejects_unsafe_authorization_scope_reference() -> None:
    payload = _payload()
    payload["authorization_scope_ref"] = "https://caller.example/scope"

    with pytest.raises(LineageContractError) as captured:
        parse_lineage_analysis_request(payload)

    assert captured.value.code == "unsafe_opaque_reference"


'''
    if unsafe_test not in contract:
        if unsafe_anchor not in contract:
            raise SystemExit("refusing unknown authorization safety insertion point")
        contract = contract.replace(unsafe_anchor, unsafe_test + unsafe_anchor, 1)
    contract_path.write_text(contract, encoding="utf-8")


def _apply_core_repair() -> None:
    """Preserve legacy graceful degradation for typed malformed LLM replies."""

    path = ROOT / "lineageweave/reconstruct.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "from .adjudication_client import AdjudicationClient, NullAdjudicationClient\n",
        "from .adjudication_client import (\n    AdjudicationClient,\n    AdjudicationClientError,\n    NullAdjudicationClient,\n)\n",
        label="core adjudication import",
    )
    text = _replace_once(
        text,
        '''        if "llm" in weights:
            scores["llm"] = llm.judge(candidate.label, record.label)
''',
        '''        if "llm" in weights:
            try:
                scores["llm"] = llm.judge(candidate.label, record.label)
            except AdjudicationClientError:
                # The long-lived core historically degraded one malformed model
                # reply to a zero contribution instead of aborting the group.
                # External contract wrappers raise LineageContractError and
                # therefore retain their stricter fail-closed boundary.
                scores["llm"] = 0.0
''',
        label="core malformed-provider handling",
    )
    path.write_text(text, encoding="utf-8")


def _apply_contract_repair() -> None:
    """Bind caller authorization and distinguish a configured but unused model."""

    path = ROOT / "lineageweave/external_lineage_contract.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        'LlmStatusCode = Literal["not_requested", "unavailable", "completed"]\n',
        'LlmStatusCode = Literal["not_requested", "unavailable", "not_invoked", "completed"]\n',
        label="LLM status vocabulary",
    )
    text = _replace_once(
        text,
        '_LLM_STATUSES = frozenset({"not_requested", "unavailable", "completed"})\n',
        '_LLM_STATUSES = frozenset({"not_requested", "unavailable", "not_invoked", "completed"})\n',
        label="LLM status set",
    )
    text = _replace_once(
        text,
        '''    contract_version: str
    analysis_id: str
    analysis_scope_code: AnalysisScopeCode
''',
        '''    contract_version: str
    analysis_id: str
    authorization_scope_ref: str
    analysis_scope_code: AnalysisScopeCode
''',
        label="request authorization field",
    )
    text = _replace_once(
        text,
        '''                "contract_version",
                "analysis_id",
                "analysis_scope_code",
''',
        '''                "contract_version",
                "analysis_id",
                "authorization_scope_ref",
                "analysis_scope_code",
''',
        label="allowed authorization field",
    )
    text = _replace_once(
        text,
        '''                "contract_version",
                "analysis_id",
                "analysis_scope_code",
                "policy",
''',
        '''                "contract_version",
                "analysis_id",
                "authorization_scope_ref",
                "analysis_scope_code",
                "policy",
''',
        label="required authorization field",
    )
    text = _replace_once(
        text,
        '''        analysis_id=cast(
            str,
            _opaque_reference(data["analysis_id"], field="analysis_id"),
        ),
        analysis_scope_code=cast(
''',
        '''        analysis_id=cast(
            str,
            _opaque_reference(data["analysis_id"], field="analysis_id"),
        ),
        authorization_scope_ref=cast(
            str,
            _opaque_reference(
                data["authorization_scope_ref"],
                field="authorization_scope_ref",
            ),
        ),
        analysis_scope_code=cast(
''',
        label="authorization parser",
    )
    text = _replace_once(
        text,
        '''        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "analysis_scope_code": request.analysis_scope_code,
''',
        '''        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "authorization_scope_ref": request.authorization_scope_ref,
        "analysis_scope_code": request.analysis_scope_code,
''',
        label="authorization serializer",
    )
    path.write_text(text, encoding="utf-8")


def _apply_analysis_repair() -> None:
    """Track actual LLM invocation and decouple wire math/order from RankWeave."""

    path = ROOT / "lineageweave/external_lineage_analysis.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '''        self._client = client

    def judge(self, candidate_label: str, record_label: str) -> float:
''',
        '''        self._client = client
        self.invocation_count = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
''',
        label="bounded client invocation counter",
    )
    text = _replace_once(
        text,
        '''        try:
            score = self._client.judge(candidate_label, record_label)
''',
        '''        self.invocation_count += 1
        try:
            score = self._client.judge(candidate_label, record_label)
''',
        label="bounded client invocation accounting",
    )
    text = _replace_once(
        text,
        '    return _BoundedAdjudicationClient(llm), "completed"\n',
        '    return _BoundedAdjudicationClient(llm), "not_invoked"\n',
        label="initial LLM status",
    )
    old_edge = '''            edges.append(
                LineageEdgeResult(
                    parent_evidence_ref=parent.record_id,
                    child_evidence_ref=source_record.evidence_ref,
                    relation_type_code="reconstructed_continuation",
                    truth_status_code="inferred",
                    fused_score=float(fused_score),
                    channel_evidence=_channel_evidence(
                        channel_scores,
                        weights,
                    ),
                )
            )
'''
    new_edge = '''            channel_evidence = _channel_evidence(channel_scores, weights)
            contract_fused_score = sum(
                item.contribution for item in channel_evidence
            )
            edges.append(
                LineageEdgeResult(
                    parent_evidence_ref=parent.record_id,
                    child_evidence_ref=source_record.evidence_ref,
                    relation_type_code="reconstructed_continuation",
                    truth_status_code="inferred",
                    fused_score=contract_fused_score,
                    channel_evidence=channel_evidence,
                )
            )
'''
    text = _replace_once(text, old_edge, new_edge, label="contract fused score")
    text = _replace_once(
        text,
        '''    inferred = _inferred_edges(
        included,
        selected_llm,
        validated,
    )
''',
        '''    inferred = _inferred_edges(
        included,
        selected_llm,
        validated,
    )
    if (
        llm_status == "not_invoked"
        and isinstance(selected_llm, _BoundedAdjudicationClient)
        and selected_llm.invocation_count > 0
    ):
        llm_status = "completed"
''',
        label="completed LLM status",
    )
    old_order = '''    edge_order = {
        record.evidence_ref: (record.group_ref, record.occurred_at, record.evidence_ref)
        for record in included
    }
    result = LineageAnalysisResult(
'''
    text = _replace_once(text, old_order, '    result = LineageAnalysisResult(\n', label="edge order projection")
    text = _replace_once(
        text,
        '''                key=lambda item: (
                    edge_order[item.child_evidence_ref],
                    item.parent_evidence_ref,
                    item.relation_type_code,
                ),
''',
        '''                key=lambda item: (
                    item.child_evidence_ref,
                    item.parent_evidence_ref,
                    item.relation_type_code,
                ),
''',
        label="canonical in-memory edge order",
    )
    path.write_text(text, encoding="utf-8")


def _apply_schema_and_docs() -> None:
    """Synchronize the public schema, example, authorization note, and changelog."""

    schema_path = ROOT / "docs/contracts/external-lineage-analysis-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required = schema["required"]
    if "authorization_scope_ref" not in required:
        required.insert(required.index("analysis_scope_code"), "authorization_scope_ref")
    schema["properties"]["authorization_scope_ref"] = {
        "$ref": "#/$defs/OpaqueReference"
    }
    statuses = schema["$defs"]["LineageAnalysisResult"]["properties"][
        "llm_status_code"
    ]["enum"]
    if "not_invoked" not in statuses:
        statuses.insert(statuses.index("completed"), "not_invoked")
    schema_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    example_path = ROOT / "docs/contracts/external-lineage-analysis-v1.example.json"
    example = json.loads(example_path.read_text(encoding="utf-8"))
    ordered = {
        "contract_version": example["contract_version"],
        "analysis_id": example["analysis_id"],
        "authorization_scope_ref": "authorization-scope:synthetic",
        **{
            key: value
            for key, value in example.items()
            if key not in {"contract_version", "analysis_id"}
        },
    }
    example_path.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    authorization_path = ROOT / "docs/contracts/external-lineage-analysis-v1.authorization.md"
    authorization = authorization_path.read_text(encoding="utf-8")
    paragraph = (
        "\n\nEvery request must carry an opaque `authorization_scope_ref` issued and "
        "validated by the caller. LineageWeave includes it in canonical request identity "
        "but does not dereference it or infer authorization from it.\n"
    )
    if paragraph.strip() not in authorization:
        authorization = authorization.rstrip() + paragraph
    authorization_path.write_text(authorization, encoding="utf-8")

    changelog_path = ROOT / "CHANGELOG.d/external-lineage-contract.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    bullet = (
        "- Bind each request to a caller-owned opaque authorization scope, distinguish a "
        "configured but uninvoked LLM from completed adjudication, and preserve graceful "
        "legacy reconstruction when a provider returns malformed confidence text.\n"
    )
    if bullet not in changelog:
        changelog = changelog.rstrip() + "\n" + bullet
    changelog_path.write_text(changelog, encoding="utf-8")


def main() -> None:
    """Prove RED, apply the bounded repair, then prove focused and full GREEN."""

    _add_regressions()
    focused = (
        "tests/test_reconstruct.py::test_core_reconstruction_degrades_one_malformed_llm_pair_to_zero",
        "tests/test_external_lineage_analysis.py::test_llm_status_is_not_invoked_without_an_inferred_candidate_pair",
        "tests/test_external_lineage_contract.py::test_parse_request_is_strict_immutable_and_canonicalizes_timestamps",
        "tests/test_external_lineage_contract.py::test_parser_rejects_unsafe_authorization_scope_reference",
        "tests/test_external_lineage_contract.py::test_public_schema_exists_and_mirrors_contract_vocabularies",
    )
    red = _run(
        "uv",
        "run",
        "--frozen",
        "python",
        "-m",
        "pytest",
        "-q",
        *focused,
        check=False,
    )
    if red.returncode == 0:
        raise SystemExit("PR 343 regressions unexpectedly passed before the repair")
    _apply_core_repair()
    _apply_contract_repair()
    _apply_analysis_repair()
    _apply_schema_and_docs()
    _run(
        "uv",
        "run",
        "--frozen",
        "python",
        "-m",
        "pytest",
        "-q",
        *focused,
    )
    _run("uv", "run", "--frozen", "python", "-m", "pytest", "-q")


if __name__ == "__main__":
    main()
