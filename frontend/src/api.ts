export * from "./apiTransport";

import type { CustomerMasterResponse } from "./apiTransport";
import { fetchCustomerMaster as fetchCustomerMasterTransport } from "./apiTransport";
import { projectCustomerMasterResponse } from "./customerMasterProjection";

/**
 * Loads Customer Master through the raw transport, then creates the safe display projection.
 * Other API functions remain direct re-exports so this boundary does not absorb unrelated
 * domain behavior.
 */
export function fetchCustomerMaster(accessToken: string): Promise<CustomerMasterResponse> {
  return fetchCustomerMasterTransport(accessToken).then(projectCustomerMasterResponse);
}
