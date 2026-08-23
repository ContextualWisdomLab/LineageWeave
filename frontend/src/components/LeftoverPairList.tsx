import type { LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import { formatLeftoverResidual } from "../leftoverResidual";

export type LeftoverPairListProps = {
  pairs: LeftoverPair[];
  criterionLabel: (criterionCode: string) => string;
  onSelectPost: (postId: string) => void;
};

/**
 * Closest and farthest leftover post–criterion pairs after IRT main effects.
 *
 * Distance is the leftover-map Euclidean gap. Residual is
 * ``R = Y − E[Y|θ, item]`` (Jeon et al., 2021, eq. 3 input).
 * Next action: read the residual, then open the named post.
 */
export function LeftoverPairList({
  pairs,
  criterionLabel,
  onSelectPost,
}: LeftoverPairListProps) {
  if (pairs.length === 0) {
    return null;
  }
  return (
    <ul className="ticket-list" aria-label={t("Leftover pairs")}>
      {pairs.map((pair) => {
        const kindLabel =
          pair.pair_kind === "farthest" ? t("Farthest leftover") : t("Closest leftover");
        const criterion = criterionLabel(pair.criterion_code);
        const residual = formatLeftoverResidual(pair.leftover_residual);
        const nextAction = tf(
          "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.",
          { residual, criterion },
        );
        return (
          <li
            key={`${pair.pair_kind}:${pair.post_id}:${pair.criterion_code}`}
            className="ticket-list-item"
          >
            <button
              type="button"
              className="post-list-item"
              aria-label={tf("Open leftover {kind} pair: {title} · {criterion}", {
                kind: pair.pair_kind,
                title: pair.post_title,
                criterion,
              })}
              onClick={() => onSelectPost(pair.post_id)}
            >
              <span className="ticket-title">
                {kindLabel}: {pair.post_title} · {criterion}
              </span>
              <span className="post-badge">{nextAction}</span>
              <span className="post-badge">R {residual}</span>
              <span className="post-badge">d {pair.leftover_distance.toFixed(2)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
