import type { CustomerMasterScopeFacet } from "../api";
import { t } from "../i18n";

export function customerScopeFacetLabel(facet: CustomerMasterScopeFacet): string {
  switch (facet) {
    case "authorized_own":
      return t("Own company");
    case "authorized_granted":
      return t("Granted company");
    case "scope_unclassified":
      return t("Scope not classified");
    case "observed_organization":
      return t("Observed organization");
    case "observed_hierarchy":
      return t("Observed hierarchy");
  }
}
