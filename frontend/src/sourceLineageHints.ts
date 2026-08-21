import type { SourceLineageHints } from "./api";
import { t } from "./i18n";

const CONTEXT_LABELS: Record<string, string> = {
  no_sales_identifier_candidate: "No sales identifier candidate",
  customer_only_candidate: "Customer only candidate",
  customer_order_pool_candidate: "Customer + order-pool candidate",
  sales_order_item_context: "Sales-order item context",
  sales_order_item_without_customer: "Sales-order item without customer",
  order_pool_only_candidate: "Order-pool only candidate",
  sales_order_without_item_candidate: "Sales order without item candidate",
  customer_sales_order_without_item_candidate: "Customer + sales order without item",
  mixed_source_identifier_context: "Mixed source identifier context",
};

const FIELD_LABELS: Record<string, string> = {
  customer: "Customer code",
  order_pool: "Order pool",
  sales_order: "Sales order",
  sales_order_item: "Sales-order item",
};

export function sourceLineageContextLabel(hints: SourceLineageHints): string {
  return t(CONTEXT_LABELS[hints.commercial_context_code] ?? hints.commercial_context_code);
}

export function sourceLineageFieldLabel(field: string): string {
  return t(FIELD_LABELS[field] ?? field);
}
