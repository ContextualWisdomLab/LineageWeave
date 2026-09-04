export * from "./apiTransport";

import type { CustomerMasterResponse } from "./apiTransport";
import { fetchCustomerMaster as fetchCustomerMasterTransport } from "./apiTransport";
import { projectCustomerMasterResponse } from "./customerMasterProjection";
import { CustomerMasterRequestGate } from "./customerMasterRequestGate";

const customerMasterRequestGate = new CustomerMasterRequestGate<CustomerMasterResponse>();

/**
 * Loads Customer Master through the raw transport, then creates the safe display projection.
 * A newer request owns the visible result so an older account/token response cannot overwrite
 * the current authorized view. Other API functions remain direct re-exports so this boundary
 * does not absorb unrelated domain behavior.
 */
export function fetchCustomerMaster(accessToken: string): Promise<CustomerMasterResponse> {
  return customerMasterRequestGate.run(() =>
    fetchCustomerMasterTransport(accessToken).then(projectCustomerMasterResponse),
  );
}
