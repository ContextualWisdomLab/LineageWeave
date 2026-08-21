"""Standards-complete W3C PROV-O relation registry and graph runtime.

The module implements every class and every object/datatype property in the
PROV-O Recommendation's normative cross-reference.  It deliberately keeps
LineageWeave's product-specific knowledge graph separate: PROV-O needs
literal-valued properties and qualified influence resources, neither of
which can be represented faithfully by the existing binary UUID edge table.

Consumers may assert the compact, unqualified form, the qualified form, or
both.  :class:`ProvGraph` materializes the Recommendation's property
hierarchy, declared inverses, symmetry, and the rule that a qualified form
implies its corresponding unqualified relation.  Appendix B inverse names
are accepted as import aliases by reversing the assertion into the preferred
PROV-O direction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Iterable, Literal as TypingLiteral, Mapping, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

PROV: Final = Namespace("http://www.w3.org/ns/prov#")
_PROPERTY_KIND = TypingLiteral["object", "datatype"]


class ProvValidationError(ValueError):
    """Raised when an assertion violates a PROV-O domain, range, or shape."""


def _snake_case(local_name: str) -> str:
    """Convert a PROV-O camel-case local name to stable lower snake case."""
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", local_name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


def class_code(local_name: str) -> str:
    """Relational code for one PROV-O class, e.g. ``prov_entity``."""
    return f"prov_{_snake_case(local_name)}"


def relation_code(local_name: str) -> str:
    """Relational code for one PROV-O property, e.g. ``prov_used``."""
    return f"prov_{_snake_case(local_name)}"


@dataclass(frozen=True)
class ProvClassSpec:
    """One normative PROV-O class and its direct superclass names."""

    local_name: str
    superclasses: tuple[str, ...] = ()

    @property
    def iri(self) -> str:
        """Absolute W3C IRI for the class."""
        return str(PROV[self.local_name])

    @property
    def code(self) -> str:
        """Stable multiword snake-case relational code."""
        return class_code(self.local_name)


@dataclass(frozen=True)
class ProvRelationSpec:
    """One normative PROV-O object or datatype property."""

    local_name: str
    property_kind: _PROPERTY_KIND
    domains: tuple[str, ...]
    ranges: tuple[str, ...] = ()
    datatype_iri: str | None = None
    superproperties: tuple[str, ...] = ()
    defined_inverse: str | None = None
    symmetric: bool = False

    @property
    def iri(self) -> str:
        """Absolute W3C IRI for the property."""
        return str(PROV[self.local_name])

    @property
    def code(self) -> str:
        """Stable multiword snake-case relational code."""
        return relation_code(self.local_name)


@dataclass(frozen=True)
class ProvQualificationSpec:
    """Normative mapping from a binary relation to its qualified pattern."""

    unqualified_relation: str
    qualification_relation: str
    influence_class: str
    influencer_relation: str


@dataclass(frozen=True)
class ProvInverseSpec:
    """Appendix B recommended inverse name for one object property.

    ``defined_relation`` names a normative PROV-O property when the inverse
    is itself part of the 50-term relation registry.  Otherwise the name is
    reserved for interoperable import/export but is not asserted as a new
    ontology property by this implementation.
    """

    relation: str
    inverse_local_name: str
    defined_relation: str | None = None

    @property
    def inverse_iri(self) -> str:
        """Absolute reserved inverse IRI in the PROV namespace."""
        return str(PROV[self.inverse_local_name])


# ---------------------------------------------------------------------------
# Normative class registry (30 terms)
# ---------------------------------------------------------------------------


def _class(local_name: str, *superclasses: str) -> ProvClassSpec:
    """Implement the _class operation for this channel."""
    return ProvClassSpec(local_name, tuple(superclasses))


PROV_CLASSES: Final[Mapping[str, ProvClassSpec]] = {
    spec.local_name: spec
    for spec in (
        _class("Entity"),
        _class("Activity"),
        _class("Agent"),
        _class("Collection", "Entity"),
        _class("EmptyCollection", "Collection"),
        _class("Bundle", "Entity"),
        _class("Person", "Agent"),
        _class("SoftwareAgent", "Agent"),
        _class("Organization", "Agent"),
        _class("Location"),
        _class("Influence"),
        _class("EntityInfluence", "Influence"),
        _class("Usage", "InstantaneousEvent", "EntityInfluence"),
        _class("Start", "InstantaneousEvent", "EntityInfluence"),
        _class("End", "InstantaneousEvent", "EntityInfluence"),
        _class("Derivation", "EntityInfluence"),
        _class("PrimarySource", "Derivation"),
        _class("Quotation", "Derivation"),
        _class("Revision", "Derivation"),
        _class("ActivityInfluence", "Influence"),
        _class("Generation", "InstantaneousEvent", "ActivityInfluence"),
        _class("Communication", "ActivityInfluence"),
        _class("Invalidation", "InstantaneousEvent", "ActivityInfluence"),
        _class("AgentInfluence", "Influence"),
        _class("Attribution", "AgentInfluence"),
        _class("Association", "AgentInfluence"),
        _class("Plan", "Entity"),
        _class("Delegation", "AgentInfluence"),
        _class("InstantaneousEvent"),
        _class("Role"),
    )
}


# ---------------------------------------------------------------------------
# Normative property registry (50 terms)
# ---------------------------------------------------------------------------


def _object(
    local_name: str,
    domains: tuple[str, ...],
    ranges: tuple[str, ...],
    *,
    superproperties: tuple[str, ...] = (),
    defined_inverse: str | None = None,
    symmetric: bool = False,
) -> ProvRelationSpec:
    """Implement the _object operation for this channel."""
    return ProvRelationSpec(
        local_name=local_name,
        property_kind="object",
        domains=domains,
        ranges=ranges,
        superproperties=superproperties,
        defined_inverse=defined_inverse,
        symmetric=symmetric,
    )


def _datatype(
    local_name: str,
    domains: tuple[str, ...],
    *,
    datatype_iri: str | None,
) -> ProvRelationSpec:
    """Implement the _datatype operation for this channel."""
    return ProvRelationSpec(
        local_name=local_name,
        property_kind="datatype",
        domains=domains,
        datatype_iri=datatype_iri,
    )


_RESOURCE_UNION = ("Entity", "Activity", "Agent")

PROV_RELATIONS: Final[Mapping[str, ProvRelationSpec]] = {
    spec.local_name: spec
    for spec in (
        # Starting-point properties.
        _object(
            "wasGeneratedBy",
            ("Entity",),
            ("Activity",),
            superproperties=("wasInfluencedBy",),
            defined_inverse="generated",
        ),
        _object(
            "wasDerivedFrom",
            ("Entity",),
            ("Entity",),
            superproperties=("wasInfluencedBy",),
        ),
        _object(
            "wasAttributedTo",
            ("Entity",),
            ("Agent",),
            superproperties=("wasInfluencedBy",),
        ),
        _datatype("startedAtTime", ("Activity",), datatype_iri=str(XSD.dateTime)),
        _object("used", ("Activity",), ("Entity",), superproperties=("wasInfluencedBy",)),
        _object(
            "wasInformedBy",
            ("Activity",),
            ("Activity",),
            superproperties=("wasInfluencedBy",),
        ),
        _datatype("endedAtTime", ("Activity",), datatype_iri=str(XSD.dateTime)),
        _object(
            "wasAssociatedWith",
            ("Activity",),
            ("Agent",),
            superproperties=("wasInfluencedBy",),
        ),
        _object(
            "actedOnBehalfOf",
            ("Agent",),
            ("Agent",),
            superproperties=("wasInfluencedBy",),
        ),
        # Expanded properties.
        _object(
            "alternateOf",
            ("Entity",),
            ("Entity",),
            defined_inverse="alternateOf",
            symmetric=True,
        ),
        _object(
            "specializationOf",
            ("Entity",),
            ("Entity",),
            superproperties=("alternateOf",),
        ),
        _datatype("generatedAtTime", ("Entity",), datatype_iri=str(XSD.dateTime)),
        _object(
            "hadPrimarySource",
            ("Entity",),
            ("Entity",),
            superproperties=("wasDerivedFrom",),
        ),
        _datatype("value", ("Entity",), datatype_iri=None),
        _object(
            "wasQuotedFrom",
            ("Entity",),
            ("Entity",),
            superproperties=("wasDerivedFrom",),
        ),
        _object(
            "wasRevisionOf",
            ("Entity",),
            ("Entity",),
            superproperties=("wasDerivedFrom",),
        ),
        _datatype("invalidatedAtTime", ("Entity",), datatype_iri=str(XSD.dateTime)),
        _object(
            "wasInvalidatedBy",
            ("Entity",),
            ("Activity",),
            superproperties=("wasInfluencedBy",),
            defined_inverse="invalidated",
        ),
        _object(
            "hadMember",
            ("Collection",),
            ("Entity",),
            superproperties=("wasInfluencedBy",),
        ),
        _object(
            "wasStartedBy",
            ("Activity",),
            ("Entity",),
            superproperties=("wasInfluencedBy",),
        ),
        _object(
            "wasEndedBy",
            ("Activity",),
            ("Entity",),
            superproperties=("wasInfluencedBy",),
        ),
        _object(
            "invalidated",
            ("Activity",),
            ("Entity",),
            superproperties=("influenced",),
            defined_inverse="wasInvalidatedBy",
        ),
        _object(
            "influenced",
            _RESOURCE_UNION,
            _RESOURCE_UNION,
            defined_inverse="wasInfluencedBy",
        ),
        _object(
            "atLocation",
            ("Activity", "Agent", "Entity", "InstantaneousEvent"),
            ("Location",),
        ),
        _object(
            "generated",
            ("Activity",),
            ("Entity",),
            superproperties=("influenced",),
            defined_inverse="wasGeneratedBy",
        ),
        # Qualified properties.
        _object(
            "wasInfluencedBy",
            _RESOURCE_UNION,
            _RESOURCE_UNION,
            defined_inverse="influenced",
        ),
        _object("qualifiedInfluence", _RESOURCE_UNION, ("Influence",)),
        _object(
            "qualifiedGeneration",
            ("Entity",),
            ("Generation",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedDerivation",
            ("Entity",),
            ("Derivation",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedPrimarySource",
            ("Entity",),
            ("PrimarySource",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedQuotation",
            ("Entity",),
            ("Quotation",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedRevision",
            ("Entity",),
            ("Revision",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedAttribution",
            ("Entity",),
            ("Attribution",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedInvalidation",
            ("Entity",),
            ("Invalidation",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedStart",
            ("Activity",),
            ("Start",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedUsage",
            ("Activity",),
            ("Usage",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedCommunication",
            ("Activity",),
            ("Communication",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedAssociation",
            ("Activity",),
            ("Association",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedEnd",
            ("Activity",),
            ("End",),
            superproperties=("qualifiedInfluence",),
        ),
        _object(
            "qualifiedDelegation",
            ("Agent",),
            ("Delegation",),
            superproperties=("qualifiedInfluence",),
        ),
        _object("influencer", ("Influence",), _RESOURCE_UNION),
        _object(
            "entity",
            ("EntityInfluence",),
            ("Entity",),
            superproperties=("influencer",),
        ),
        _object("hadUsage", ("Derivation",), ("Usage",)),
        _object("hadGeneration", ("Derivation",), ("Generation",)),
        _object(
            "activity",
            ("ActivityInfluence",),
            ("Activity",),
            superproperties=("influencer",),
        ),
        _object(
            "agent",
            ("AgentInfluence",),
            ("Agent",),
            superproperties=("influencer",),
        ),
        _object("hadPlan", ("Association",), ("Plan",)),
        _object("hadActivity", ("Delegation", "Derivation", "End", "Start"), ("Activity",)),
        _datatype("atTime", ("InstantaneousEvent",), datatype_iri=str(XSD.dateTime)),
        _object("hadRole", ("Association", "InstantaneousEvent"), ("Role",)),
    )
}


# ---------------------------------------------------------------------------
# Normative qualification tables (Tables 2 and 3)
# ---------------------------------------------------------------------------

PROV_QUALIFICATIONS: Final[tuple[ProvQualificationSpec, ...]] = (
    ProvQualificationSpec("wasGeneratedBy", "qualifiedGeneration", "Generation", "activity"),
    ProvQualificationSpec("wasDerivedFrom", "qualifiedDerivation", "Derivation", "entity"),
    ProvQualificationSpec("wasAttributedTo", "qualifiedAttribution", "Attribution", "agent"),
    ProvQualificationSpec("used", "qualifiedUsage", "Usage", "entity"),
    ProvQualificationSpec("wasInformedBy", "qualifiedCommunication", "Communication", "activity"),
    ProvQualificationSpec("wasAssociatedWith", "qualifiedAssociation", "Association", "agent"),
    ProvQualificationSpec("actedOnBehalfOf", "qualifiedDelegation", "Delegation", "agent"),
    ProvQualificationSpec("wasInfluencedBy", "qualifiedInfluence", "Influence", "influencer"),
    ProvQualificationSpec("hadPrimarySource", "qualifiedPrimarySource", "PrimarySource", "entity"),
    ProvQualificationSpec("wasQuotedFrom", "qualifiedQuotation", "Quotation", "entity"),
    ProvQualificationSpec("wasRevisionOf", "qualifiedRevision", "Revision", "entity"),
    ProvQualificationSpec("wasInvalidatedBy", "qualifiedInvalidation", "Invalidation", "activity"),
    ProvQualificationSpec("wasStartedBy", "qualifiedStart", "Start", "entity"),
    ProvQualificationSpec("wasEndedBy", "qualifiedEnd", "End", "entity"),
)


# ---------------------------------------------------------------------------
# Appendix B inverse-name registry (all 44 object properties)
# ---------------------------------------------------------------------------

_INVERSE_NAME_ROWS = {
    "actedOnBehalfOf": "hadDelegate",
    "activity": "activityOfInfluence",
    "agent": "agentOfInfluence",
    "alternateOf": "alternateOf",
    "atLocation": "locationOf",
    "entity": "entityOfInfluence",
    "generated": "wasGeneratedBy",
    "hadActivity": "wasActivityOfInfluence",
    "hadGeneration": "generatedAsDerivation",
    "hadMember": "wasMemberOf",
    "hadPlan": "wasPlanOf",
    "hadPrimarySource": "wasPrimarySourceOf",
    "hadRole": "wasRoleIn",
    "hadUsage": "wasUsedInDerivation",
    "influenced": "wasInfluencedBy",
    "influencer": "hadInfluence",
    "invalidated": "wasInvalidatedBy",
    "qualifiedAssociation": "qualifiedAssociationOf",
    "qualifiedAttribution": "qualifiedAttributionOf",
    "qualifiedCommunication": "qualifiedCommunicationOf",
    "qualifiedDelegation": "qualifiedDelegationOf",
    "qualifiedDerivation": "qualifiedDerivationOf",
    "qualifiedEnd": "qualifiedEndOf",
    "qualifiedGeneration": "qualifiedGenerationOf",
    "qualifiedInfluence": "qualifiedInfluenceOf",
    "qualifiedInvalidation": "qualifiedInvalidationOf",
    "qualifiedPrimarySource": "qualifiedSourceOf",
    "qualifiedQuotation": "qualifiedQuotationOf",
    "qualifiedRevision": "revisedEntity",
    "qualifiedStart": "qualifiedStartOf",
    "qualifiedUsage": "qualifiedUsingActivity",
    "specializationOf": "generalizationOf",
    "used": "wasUsedBy",
    "wasAssociatedWith": "wasAssociateFor",
    "wasAttributedTo": "contributed",
    "wasDerivedFrom": "hadDerivation",
    "wasEndedBy": "ended",
    "wasGeneratedBy": "generated",
    "wasInfluencedBy": "influenced",
    "wasInformedBy": "informed",
    "wasInvalidatedBy": "invalidated",
    "wasQuotedFrom": "quotedAs",
    "wasRevisionOf": "hadRevision",
    "wasStartedBy": "started",
}

PROV_RECOMMENDED_INVERSES: Final[Mapping[str, ProvInverseSpec]] = {
    relation: ProvInverseSpec(
        relation=relation,
        inverse_local_name=inverse_name,
        defined_relation=inverse_name if inverse_name in PROV_RELATIONS else None,
    )
    for relation, inverse_name in _INVERSE_NAME_ROWS.items()
}

# Non-standard-but-reserved aliases are safe to normalize because canonical
# PROV-O names always win when the same local name is itself a real property.
_INVERSE_ALIAS_TO_CANONICAL: Final[Mapping[str, str]] = {
    spec.inverse_local_name: relation
    for relation, spec in PROV_RECOMMENDED_INVERSES.items()
    if spec.inverse_local_name not in PROV_RELATIONS
}


@dataclass(frozen=True)
class ProvLiteral:
    """RDF literal used as the object of a PROV-O datatype property."""

    lexical_value: str
    datatype_iri: str | None = None
    language_tag: str | None = None

    def __post_init__(self) -> None:
        if self.datatype_iri and self.language_tag:
            raise ProvValidationError("a literal cannot have both datatype_iri and language_tag")
        if self.language_tag and not re.fullmatch(r"[A-Za-z]+(?:-[A-Za-z0-9]+)*", self.language_tag):
            raise ProvValidationError("language_tag must be a valid BCP 47-style tag")

    @classmethod
    def datetime(cls, value: datetime) -> "ProvLiteral":
        """Create a timezone-aware ``xsd:dateTime`` literal."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ProvValidationError("PROV-O dateTime values must be timezone-aware")
        return cls(value.isoformat(), datatype_iri=str(XSD.dateTime))

    def to_rdflib(self) -> Literal:
        """Convert to an rdflib literal without changing lexical form."""
        return Literal(
            self.lexical_value,
            datatype=URIRef(self.datatype_iri) if self.datatype_iri else None,
            lang=self.language_tag,
        )


@dataclass(frozen=True)
class ProvAssertion:
    """One canonical PROV-O assertion with exactly one object kind."""

    subject_iri: str
    relation: str
    object_resource_iri: str | None = None
    object_literal: ProvLiteral | None = None

    def __post_init__(self) -> None:
        if (self.object_resource_iri is None) == (self.object_literal is None):
            raise ProvValidationError(
                "a provenance assertion must have exactly one resource or literal object"
            )

    @classmethod
    def resource(cls, subject_iri: str, relation: str, object_iri: str) -> "ProvAssertion":
        """Construct a resource-to-resource assertion."""
        return cls(subject_iri, relation, object_resource_iri=object_iri)

    @classmethod
    def literal(
        cls, subject_iri: str, relation: str, object_literal: ProvLiteral
    ) -> "ProvAssertion":
        """Construct a resource-to-literal assertion."""
        return cls(subject_iri, relation, object_literal=object_literal)


class ProvGraph:
    """Validated in-memory PROV-O graph with deterministic entailment.

    Resource IRIs are explicitly typed.  Assertions may use a local PROV
    name, ``prov:`` compact name, full PROV IRI, or an Appendix B reserved
    inverse name.  Reserved inverse names are rewritten into the preferred
    PROV-O direction at insertion time.
    """

    def __init__(self) -> None:
        self._resource_types: dict[str, set[str]] = {}
        self._explicit_assertions: set[ProvAssertion] = set()

    @property
    def resource_types(self) -> Mapping[str, frozenset[str]]:
        """Read-only snapshot of explicitly assigned resource types."""
        return {iri: frozenset(types) for iri, types in self._resource_types.items()}

    @property
    def explicit_assertions(self) -> frozenset[ProvAssertion]:
        """Assertions supplied by callers after inverse-alias normalization."""
        return frozenset(self._explicit_assertions)

    def add_resource(self, resource_iri: str, *class_names: str) -> None:
        """Declare one resource and one or more normative PROV-O types."""
        if not resource_iri:
            raise ProvValidationError("resource_iri is required")
        if not class_names:
            raise ProvValidationError("at least one PROV-O class is required")
        normalized = {self._normalize_class_name(name) for name in class_names}
        self._resource_types.setdefault(resource_iri, set()).update(normalized)

    def add_assertion(
        self,
        subject_iri: str,
        relation: str,
        object_value: str | ProvLiteral,
    ) -> ProvAssertion:
        """Validate, canonicalize, and store one PROV-O assertion."""
        relation_name, reverse = self._normalize_relation_name(relation)
        if reverse:
            if isinstance(object_value, ProvLiteral):
                raise ProvValidationError("an inverse object-property alias cannot reverse a literal")
            subject_iri, object_value = object_value, subject_iri

        spec = PROV_RELATIONS[relation_name]
        self._validate_subject(subject_iri, spec)
        if spec.property_kind == "object":
            if isinstance(object_value, ProvLiteral):
                raise ProvValidationError(f"{relation_name} requires a resource object")
            self._validate_resource_object(object_value, spec)
            assertion = ProvAssertion.resource(subject_iri, relation_name, object_value)
        else:
            if isinstance(object_value, str):
                raise ProvValidationError(f"{relation_name} requires a literal object")
            self._validate_literal_object(object_value, spec)
            assertion = ProvAssertion.literal(subject_iri, relation_name, object_value)
        self._explicit_assertions.add(assertion)
        return assertion

    def materialized_assertions(self) -> frozenset[ProvAssertion]:
        """Return explicit assertions plus deterministic PROV-O entailments.

        Materialization includes transitive superproperty closure, declared
        standard inverses, ``alternateOf`` symmetry, all fourteen
        qualified-to-unqualified mappings, and the four direct time
        shortcuts defined by qualified Generation/Invalidation/Start/End.
        """
        assertions = set(self._explicit_assertions)
        changed = True
        while changed:
            changed = False
            additions: set[ProvAssertion] = set()

            for assertion in assertions:
                relation_spec = PROV_RELATIONS[assertion.relation]
                for superproperty in relation_spec.superproperties:
                    additions.add(self._same_object(assertion, superproperty))
                if assertion.object_resource_iri is not None:
                    if relation_spec.defined_inverse is not None:
                        additions.add(
                            ProvAssertion.resource(
                                assertion.object_resource_iri,
                                relation_spec.defined_inverse,
                                assertion.subject_iri,
                            )
                        )
                    if relation_spec.symmetric:
                        additions.add(
                            ProvAssertion.resource(
                                assertion.object_resource_iri,
                                assertion.relation,
                                assertion.subject_iri,
                            )
                        )

            by_relation: dict[str, list[ProvAssertion]] = {}
            for assertion in assertions | additions:
                by_relation.setdefault(assertion.relation, []).append(assertion)

            for qualification in PROV_QUALIFICATIONS:
                qualified_edges = by_relation.get(qualification.qualification_relation, [])
                influencer_edges = by_relation.get(qualification.influencer_relation, [])
                influencers_by_node: dict[str, list[str]] = {}
                for edge in influencer_edges:
                    influencer_iri = cast(str, edge.object_resource_iri)
                    influencers_by_node.setdefault(edge.subject_iri, []).append(influencer_iri)
                for edge in qualified_edges:
                    qualified_node = cast(str, edge.object_resource_iri)
                    for influencer_iri in influencers_by_node.get(qualified_node, []):
                        additions.add(
                            ProvAssertion.resource(
                                edge.subject_iri,
                                qualification.unqualified_relation,
                                influencer_iri,
                            )
                        )

            # Direct time properties are shorthand for atTime on the
            # corresponding qualified instantaneous event.
            for qualified_relation, direct_time_relation in (
                ("qualifiedGeneration", "generatedAtTime"),
                ("qualifiedInvalidation", "invalidatedAtTime"),
                ("qualifiedStart", "startedAtTime"),
                ("qualifiedEnd", "endedAtTime"),
            ):
                event_times: dict[str, list[ProvLiteral]] = {}
                for at_time in by_relation.get("atTime", []):
                    literal = cast(ProvLiteral, at_time.object_literal)
                    event_times.setdefault(at_time.subject_iri, []).append(literal)
                for edge in by_relation.get(qualified_relation, []):
                    event_iri = cast(str, edge.object_resource_iri)
                    for literal in event_times.get(event_iri, []):
                        additions.add(
                            ProvAssertion.literal(edge.subject_iri, direct_time_relation, literal)
                        )

            new_assertions = additions - assertions
            if new_assertions:
                assertions.update(new_assertions)
                changed = True

        return frozenset(assertions)

    def to_rdflib(self, *, materialize: bool = False) -> Graph:
        """Serialize explicit or materialized content to an rdflib graph."""
        graph = Graph()
        graph.bind("prov", PROV)
        for resource_iri, types in self._resource_types.items():
            for class_name in sorted(types):
                graph.add((URIRef(resource_iri), RDF.type, PROV[class_name]))
        assertions: Iterable[ProvAssertion]
        assertions = self.materialized_assertions() if materialize else self.explicit_assertions
        for assertion in assertions:
            subject = URIRef(assertion.subject_iri)
            predicate = PROV[assertion.relation]
            if assertion.object_resource_iri is not None:
                object_node = URIRef(assertion.object_resource_iri)
            else:
                assert assertion.object_literal is not None
                object_node = assertion.object_literal.to_rdflib()
            graph.add((subject, predicate, object_node))
        return graph

    @staticmethod
    def _same_object(assertion: ProvAssertion, relation: str) -> ProvAssertion:
        """Copy an object-property assertion under one of its superproperties."""
        return ProvAssertion.resource(
            assertion.subject_iri, relation, cast(str, assertion.object_resource_iri)
        )

    @staticmethod
    def _normalize_class_name(class_name: str) -> str:
        """Implement the _normalize_class_name operation for this channel."""
        local_name = _local_name(class_name)
        if local_name not in PROV_CLASSES:
            raise ProvValidationError(f"unknown PROV-O class {class_name!r}")
        return local_name

    @staticmethod
    def _normalize_relation_name(relation: str) -> tuple[str, bool]:
        """Implement the _normalize_relation_name operation for this channel."""
        local_name = _local_name(relation)
        if local_name in PROV_RELATIONS:
            return local_name, False
        canonical = _INVERSE_ALIAS_TO_CANONICAL.get(local_name)
        if canonical is None:
            raise ProvValidationError(f"unknown PROV-O relation {relation!r}")
        return canonical, True

    def _validate_subject(self, subject_iri: str, spec: ProvRelationSpec) -> None:
        """Implement the _validate_subject operation for this channel."""
        actual_types = self._resource_types.get(subject_iri)
        if actual_types is None:
            raise ProvValidationError(f"subject resource {subject_iri!r} has not been declared")
        if not _matches_any_class(actual_types, spec.domains):
            expected = " or ".join(spec.domains)
            raise ProvValidationError(
                f"subject {subject_iri!r} of {spec.local_name} must be {expected}"
            )

    def _validate_resource_object(self, object_iri: str, spec: ProvRelationSpec) -> None:
        """Implement the _validate_resource_object operation for this channel."""
        actual_types = self._resource_types.get(object_iri)
        if actual_types is None:
            raise ProvValidationError(f"object resource {object_iri!r} has not been declared")
        if not _matches_any_class(actual_types, spec.ranges):
            expected = " or ".join(spec.ranges)
            raise ProvValidationError(
                f"object {object_iri!r} of {spec.local_name} must be {expected}"
            )

    @staticmethod
    def _validate_literal_object(literal: ProvLiteral, spec: ProvRelationSpec) -> None:
        """Implement the _validate_literal_object operation for this channel."""
        if spec.datatype_iri is not None and literal.datatype_iri != spec.datatype_iri:
            raise ProvValidationError(
                f"{spec.local_name} requires datatype {spec.datatype_iri}, "
                f"got {literal.datatype_iri!r}"
            )


def _local_name(value: str) -> str:
    """Return the local name from a local, compact, or absolute PROV IRI."""
    if value.startswith(str(PROV)):
        return value[len(str(PROV)) :]
    if value.startswith("prov:"):
        return value[5:]
    return value


def _class_ancestors(class_name: str) -> frozenset[str]:
    """Return a class and every transitive superclass without duplicates."""
    ancestors = {class_name}
    pending = [class_name]
    while pending:
        current = pending.pop()
        unseen = set(PROV_CLASSES[current].superclasses) - ancestors
        ancestors.update(unseen)
        pending.extend(unseen)
    return frozenset(ancestors)


def _matches_any_class(actual_types: Iterable[str], expected_types: Iterable[str]) -> bool:
    """Implement the _matches_any_class operation for this channel."""
    expected = set(expected_types)
    return any(bool(_class_ancestors(actual) & expected) for actual in actual_types)


__all__ = [
    "PROV",
    "PROV_CLASSES",
    "PROV_QUALIFICATIONS",
    "PROV_RELATIONS",
    "PROV_RECOMMENDED_INVERSES",
    "ProvAssertion",
    "ProvClassSpec",
    "ProvGraph",
    "ProvInverseSpec",
    "ProvLiteral",
    "ProvQualificationSpec",
    "ProvRelationSpec",
    "ProvValidationError",
    "class_code",
    "relation_code",
]
