import type { LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import {
  formatLeftoverMapCrossShare,
  LEFTOVER_MAP_CROSS_SHARE_ACTION,
} from "../leftoverMapCrossShare";
import {
  formatLeftoverMapExplainedShare,
  LEFTOVER_MAP_EXPLAINED_SHARE_ACTION,
} from "../leftoverMapExplainedShare";
import {
  formatLeftoverMapReconstruction,
  LEFTOVER_MAP_RECONSTRUCTION_ACTION,
} from "../leftoverMapReconstruction";
import {
  formatLeftoverMapRank,
  LEFTOVER_RANK_STRUCTURE_ACTION,
  LEFTOVER_RANK_ZERO_ACTION,
} from "../leftoverMapRank";
import { formatLeftoverObservedExpected } from "../leftoverObservedExpected";
import { formatLeftoverResidual } from "../leftoverResidual";
import {
  formatLeftoverMapUnexplained,
  formatSignedLeftoverValue,
  LEFTOVER_MAP_UNEXPLAINED_ACTION,
} from "../leftoverMapUnexplained";

export type LeftoverPairListProps = {
  pairs: LeftoverPair[];
  criterionLabel: (criterionCode: string) => string;
  onSelectPost: (pair: LeftoverPair) => void;
};

/**
 * Closest and farthest leftover post–criterion pairs after IRT main effects.
 *
 * Distance is the two-axis leftover-map Euclidean gap. Residual is
 * ``R = Y − E[Y|θ, item]`` (Jeon et al., 2021, eq. 3 input). Unexplained
 * leftover ``U = R − R̂`` after two-axis Gabriel reconstruction (ADR 0182)
 * takes priority over the residual/observed-expected/rank next action
 * when finite. When leftover-map cross share ``x = 2 R̂ U / R²`` of
 * raw residual is also present (ADR 0185), it names the next action
 * instead of unexplained leftover. Leftover-map explained share
 * ``e = R̂² / R²`` of raw residual (ADR 0232) takes priority over
 * cross share when finite. A missing or non-finite value falls back
 * in order — explained share, cross share, reconstruction, unexplained
 * leftover, then the existing residual/rank/observed-expected next
 * action. Every badge still renders together before opening the named
 * post.
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
        const observedExpected = formatLeftoverObservedExpected(
          pair.observed_response,
          pair.expected_response,
        );
        const rankBadge = formatLeftoverMapRank(pair.leftover_map_rank);
        const unexplained = formatLeftoverMapUnexplained(pair.leftover_map_unexplained);
        const crossShareBadge = formatLeftoverMapCrossShare(pair.leftover_map_cross_share);
        const reconstruction = formatLeftoverMapReconstruction(
          pair.leftover_map_reconstruction,
        );
        const explainedShareBadge = formatLeftoverMapExplainedShare(
          pair.leftover_map_explained_share,
        );
        const explainedShareValue =
          pair.leftover_map_explained_share != null &&
          Number.isFinite(pair.leftover_map_explained_share)
            ? pair.leftover_map_explained_share.toFixed(2)
            : "—";
        const crossShareValue =
          pair.leftover_map_cross_share != null && Number.isFinite(pair.leftover_map_cross_share)
            ? pair.leftover_map_cross_share.toFixed(2)
            : "—";
        let nextAction: string;
        if (explainedShareBadge !== null) {
          nextAction = tf(LEFTOVER_MAP_EXPLAINED_SHARE_ACTION, {
            value: explainedShareValue,
            criterion,
          });
        } else if (crossShareBadge !== null) {
          nextAction = tf(LEFTOVER_MAP_CROSS_SHARE_ACTION, {
            value: crossShareValue,
            criterion,
          });
        } else if (reconstruction !== null) {
          const signedReconstruction =
            formatSignedLeftoverValue(pair.leftover_map_reconstruction ?? Number.NaN) ?? "—";
          nextAction = tf(LEFTOVER_MAP_RECONSTRUCTION_ACTION, {
            value: signedReconstruction,
            criterion,
          });
        } else if (unexplained !== null) {
          const signedUnexplained =
            formatSignedLeftoverValue(pair.leftover_map_unexplained ?? Number.NaN) ?? "—";
          nextAction = tf(LEFTOVER_MAP_UNEXPLAINED_ACTION, {
            value: signedUnexplained,
            criterion,
          });
        } else if (rankBadge !== null && observedExpected !== null) {
          nextAction =
            pair.leftover_map_rank === 0
              ? tf(
                  "Leftover map rank 0 means no leftover structure after IRT main effects. Read observed Y {observed} and expected E {expected}, then open this post.",
                  {
                    observed: Number(pair.observed_response).toFixed(2),
                    expected: Number(pair.expected_response).toFixed(2),
                  },
                )
              : tf(
                  "Read leftover map rank {rank}, observed Y {observed}, and expected E {expected} after IRT main effects, then open this post.",
                  {
                    rank: String(pair.leftover_map_rank),
                    observed: Number(pair.observed_response).toFixed(2),
                    expected: Number(pair.expected_response).toFixed(2),
                  },
                );
        } else if (rankBadge !== null) {
          nextAction =
            pair.leftover_map_rank === 0
              ? t(LEFTOVER_RANK_ZERO_ACTION)
              : tf(LEFTOVER_RANK_STRUCTURE_ACTION, {
                  rank: String(pair.leftover_map_rank),
                });
        } else if (observedExpected !== null) {
          nextAction = tf(
            "Read observed Y {observed} and expected E {expected} after IRT main effects, then open this post.",
            {
              observed: Number(pair.observed_response).toFixed(2),
              expected: Number(pair.expected_response).toFixed(2),
            },
          );
        } else {
          nextAction = tf(
            "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.",
            { residual, criterion },
          );
        }
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
              title={t("Open this post so the leftover criterion is current in Post quality.")}
              onClick={() => onSelectPost(pair)}
            >
              <span className="ticket-title">
                {kindLabel}: {pair.post_title} · {criterion}
              </span>
              <span className="post-badge">{nextAction}</span>
              <span className="post-badge">R {residual}</span>
              {observedExpected ? <span className="post-badge">{observedExpected}</span> : null}
              {rankBadge ? <span className="post-badge">{rankBadge}</span> : null}
              {unexplained ? <span className="post-badge">{unexplained}</span> : null}
              {crossShareBadge ? <span className="post-badge">{crossShareBadge}</span> : null}
              {reconstruction ? <span className="post-badge">{reconstruction}</span> : null}
              {explainedShareBadge ? <span className="post-badge">{explainedShareBadge}</span> : null}
              <span className="post-badge">d {pair.leftover_distance.toFixed(2)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
