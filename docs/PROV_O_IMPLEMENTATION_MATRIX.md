# PROV-O implementation matrix

> Normative decision: [ADR 0065](adr/0065-prov-o-provenance-boundary.md).
> This file remains the machine-reviewable coverage matrix.

LineageWeave implements the W3C PROV-O Recommendation as a separate standards-complete provenance layer. The product-specific `knowledge_graph_edge` remains a compact navigation projection; it is not used to flatten literal-valued or qualified PROV-O assertions.

## Coverage contract

- 30 normative classes.
- 50 normative properties: 44 object properties and 6 datatype properties.
- 14 qualified influence mappings from Tables 2 and 3.
- Qualified forms imply their unqualified forms.
- Transitive subproperty closure, defined inverses, `alternateOf` symmetry, and qualified event-time shortcuts are materialized deterministically.
- All 44 Appendix B inverse names are cataloged; non-canonical reserved names are accepted by reversing into the preferred PROV-O direction.

## Property matrix

| PROV-O property | Kind | Domain | Range / datatype | Superproperty | Qualification | Appendix B inverse |
|---|---|---|---|---|---|---|
| `prov:wasGeneratedBy` | object | Entity | Activity | wasInfluencedBy | qualifiedGeneration → Generation.activity | `prov:generated` |
| `prov:wasDerivedFrom` | object | Entity | Entity | wasInfluencedBy | qualifiedDerivation → Derivation.entity | `prov:hadDerivation` |
| `prov:wasAttributedTo` | object | Entity | Agent | wasInfluencedBy | qualifiedAttribution → Attribution.agent | `prov:contributed` |
| `prov:startedAtTime` | datatype | Activity | http://www.w3.org/2001/XMLSchema#dateTime | — | — | — |
| `prov:used` | object | Activity | Entity | wasInfluencedBy | qualifiedUsage → Usage.entity | `prov:wasUsedBy` |
| `prov:wasInformedBy` | object | Activity | Activity | wasInfluencedBy | qualifiedCommunication → Communication.activity | `prov:informed` |
| `prov:endedAtTime` | datatype | Activity | http://www.w3.org/2001/XMLSchema#dateTime | — | — | — |
| `prov:wasAssociatedWith` | object | Activity | Agent | wasInfluencedBy | qualifiedAssociation → Association.agent | `prov:wasAssociateFor` |
| `prov:actedOnBehalfOf` | object | Agent | Agent | wasInfluencedBy | qualifiedDelegation → Delegation.agent | `prov:hadDelegate` |
| `prov:alternateOf` | object | Entity | Entity | — | — | `prov:alternateOf` |
| `prov:specializationOf` | object | Entity | Entity | alternateOf | — | `prov:generalizationOf` |
| `prov:generatedAtTime` | datatype | Entity | http://www.w3.org/2001/XMLSchema#dateTime | — | — | — |
| `prov:hadPrimarySource` | object | Entity | Entity | wasDerivedFrom | qualifiedPrimarySource → PrimarySource.entity | `prov:wasPrimarySourceOf` |
| `prov:value` | datatype | Entity | RDF literal | — | — | — |
| `prov:wasQuotedFrom` | object | Entity | Entity | wasDerivedFrom | qualifiedQuotation → Quotation.entity | `prov:quotedAs` |
| `prov:wasRevisionOf` | object | Entity | Entity | wasDerivedFrom | qualifiedRevision → Revision.entity | `prov:hadRevision` |
| `prov:invalidatedAtTime` | datatype | Entity | http://www.w3.org/2001/XMLSchema#dateTime | — | — | — |
| `prov:wasInvalidatedBy` | object | Entity | Activity | wasInfluencedBy | qualifiedInvalidation → Invalidation.activity | `prov:invalidated` |
| `prov:hadMember` | object | Collection | Entity | wasInfluencedBy | — | `prov:wasMemberOf` |
| `prov:wasStartedBy` | object | Activity | Entity | wasInfluencedBy | qualifiedStart → Start.entity | `prov:started` |
| `prov:wasEndedBy` | object | Activity | Entity | wasInfluencedBy | qualifiedEnd → End.entity | `prov:ended` |
| `prov:invalidated` | object | Activity | Entity | influenced | — | `prov:wasInvalidatedBy` |
| `prov:influenced` | object | Entity / Activity / Agent | Entity / Activity / Agent | — | — | `prov:wasInfluencedBy` |
| `prov:atLocation` | object | Activity / Agent / Entity / InstantaneousEvent | Location | — | — | `prov:locationOf` |
| `prov:generated` | object | Activity | Entity | influenced | — | `prov:wasGeneratedBy` |
| `prov:wasInfluencedBy` | object | Entity / Activity / Agent | Entity / Activity / Agent | — | qualifiedInfluence → Influence.influencer | `prov:influenced` |
| `prov:qualifiedInfluence` | object | Entity / Activity / Agent | Influence | — | — | `prov:qualifiedInfluenceOf` |
| `prov:qualifiedGeneration` | object | Entity | Generation | qualifiedInfluence | — | `prov:qualifiedGenerationOf` |
| `prov:qualifiedDerivation` | object | Entity | Derivation | qualifiedInfluence | — | `prov:qualifiedDerivationOf` |
| `prov:qualifiedPrimarySource` | object | Entity | PrimarySource | qualifiedInfluence | — | `prov:qualifiedSourceOf` |
| `prov:qualifiedQuotation` | object | Entity | Quotation | qualifiedInfluence | — | `prov:qualifiedQuotationOf` |
| `prov:qualifiedRevision` | object | Entity | Revision | qualifiedInfluence | — | `prov:revisedEntity` |
| `prov:qualifiedAttribution` | object | Entity | Attribution | qualifiedInfluence | — | `prov:qualifiedAttributionOf` |
| `prov:qualifiedInvalidation` | object | Entity | Invalidation | qualifiedInfluence | — | `prov:qualifiedInvalidationOf` |
| `prov:qualifiedStart` | object | Activity | Start | qualifiedInfluence | — | `prov:qualifiedStartOf` |
| `prov:qualifiedUsage` | object | Activity | Usage | qualifiedInfluence | — | `prov:qualifiedUsingActivity` |
| `prov:qualifiedCommunication` | object | Activity | Communication | qualifiedInfluence | — | `prov:qualifiedCommunicationOf` |
| `prov:qualifiedAssociation` | object | Activity | Association | qualifiedInfluence | — | `prov:qualifiedAssociationOf` |
| `prov:qualifiedEnd` | object | Activity | End | qualifiedInfluence | — | `prov:qualifiedEndOf` |
| `prov:qualifiedDelegation` | object | Agent | Delegation | qualifiedInfluence | — | `prov:qualifiedDelegationOf` |
| `prov:influencer` | object | Influence | Entity / Activity / Agent | — | — | `prov:hadInfluence` |
| `prov:entity` | object | EntityInfluence | Entity | influencer | — | `prov:entityOfInfluence` |
| `prov:hadUsage` | object | Derivation | Usage | — | — | `prov:wasUsedInDerivation` |
| `prov:hadGeneration` | object | Derivation | Generation | — | — | `prov:generatedAsDerivation` |
| `prov:activity` | object | ActivityInfluence | Activity | influencer | — | `prov:activityOfInfluence` |
| `prov:agent` | object | AgentInfluence | Agent | influencer | — | `prov:agentOfInfluence` |
| `prov:hadPlan` | object | Association | Plan | — | — | `prov:wasPlanOf` |
| `prov:hadActivity` | object | Delegation / Derivation / End / Start | Activity | — | — | `prov:wasActivityOfInfluence` |
| `prov:atTime` | datatype | InstantaneousEvent | http://www.w3.org/2001/XMLSchema#dateTime | — | — | — |
| `prov:hadRole` | object | Association / InstantaneousEvent | Role | — | — | `prov:wasRoleIn` |
