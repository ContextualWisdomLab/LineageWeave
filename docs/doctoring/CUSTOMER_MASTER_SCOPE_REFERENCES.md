# Customer Master scope references

This register grounds the proposed Customer Master scope-facet decision in
authoritative access-control and semantic-hierarchy sources. Keep the
authorization boundary, observed evidence, and catalog identity separate when
implementing ADR 0125.

## Evidence mapping

| Source | Product decision |
| --- | --- |
| NIST SP 800-162 | Treat account, resource, action, and environment attributes as inputs to an ABAC decision; do not turn a display classification into a permission grant. |
| NIST SP 800-207 | Re-evaluate access at the resource boundary and minimize implicit trust; visible relationship evidence cannot widen private-post access. |
| W3C SKOS | Represent the corporate hierarchy as a broader/narrower concept relation while retaining the evidence and authorization facets separately. |

## APA 7th references

Hu, V. C., Ferraiolo, D., Kuhn, R., Schnitzer, A., Sandlin, K., Miller, R., &
Scarfone, K. (2019). *Guide to attribute based access control (ABAC)
definition and considerations* (NIST Special Publication 800-162, updated
2019). National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.SP.800-162

Rose, S., Borchert, O., Mitchell, S., & Connelly, S. (2020). *Zero trust
architecture* (NIST Special Publication 800-207). National Institute of
Standards and Technology. https://doi.org/10.6028/NIST.SP.800-207

World Wide Web Consortium. (2009). *SKOS simple knowledge organization system
reference*. https://www.w3.org/TR/skos-reference/
