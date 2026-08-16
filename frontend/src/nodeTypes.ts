/** Graph node type codes used by related-node chips and walks. */

export const NODE_PERSON = "node_person";
export const NODE_POST = "node_post";
export const NODE_CORPORATE_ENTITY = "node_corporate_entity";

export type RelatedNodeKind =
  | typeof NODE_PERSON
  | typeof NODE_POST
  | typeof NODE_CORPORATE_ENTITY;

export function isRelatedNodeKind(code: string): code is RelatedNodeKind {
  return code === NODE_PERSON || code === NODE_POST || code === NODE_CORPORATE_ENTITY;
}
