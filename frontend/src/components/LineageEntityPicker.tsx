export type LineageEntityOption = {
  corporate_entity_id: string;
  entity_name: string;
};

export type LineageEntityPickerProps = {
  entities: LineageEntityOption[];
  selectedEntityId: string;
  onSelectEntityId: (entityId: string) => void;
};

/**
 * Chooses which affiliated corp a lineage request will cover.
 *
 * Next action: pick the entity, then click Request a lineage reconstruction.
 */
export function LineageEntityPicker({
  entities,
  selectedEntityId,
  onSelectEntityId,
}: LineageEntityPickerProps) {
  if (entities.length <= 1) {
    return null;
  }
  return (
    <label className="lineage-entity-picker">
      Corporate entity to reconstruct
      <select
        aria-label="Corporate entity to reconstruct"
        value={selectedEntityId}
        onChange={(event) => onSelectEntityId(event.target.value)}
      >
        <option value="">Choose a corporate entity</option>
        {entities.map((entity) => (
          <option key={entity.corporate_entity_id} value={entity.corporate_entity_id}>
            {entity.entity_name}
          </option>
        ))}
      </select>
    </label>
  );
}
