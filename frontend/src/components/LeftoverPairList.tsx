import type { LeftoverMapAxis, LeftoverMapCoverage, LeftoverPair } from "../api";
import { t, tf } from "../i18n";
import {
  formatLeftoverMapCrossShare,
  LEFTOVER_MAP_CROSS_SHARE_ACTION,
} from "../leftoverMapCrossShare";
import {
  formatLeftoverMapCoordinatePair,
  formatLeftoverMapCoordinates,
  LEFTOVER_MAP_COORDINATES_ACTION,
} from "../leftoverMapCoordinates";
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
import {
  formatLeftoverMapExplainedShare,
  LEFTOVER_MAP_EXPLAINED_SHARE_ACTION,
} from "../leftoverMapExplainedShare";
import {
  formatLeftoverMapUnexplainedShare,
  LEFTOVER_MAP_UNEXPLAINED_SHARE_ACTION,
} from "../leftoverMapUnexplainedShare";
import { LeftoverMapPlot } from "./LeftoverMapPlot";

export type LeftoverPairListProps = {
  pairs: LeftoverPair[];
  leftoverMapAxes?: LeftoverMapAxis[];
  leftoverMapCoverage?: LeftoverMapCoverage | null;
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
 * when finite. When leftover-map coordinates ``ξ_{1:2}`` and ``ζ_{1:2}``
 * are also present (ADR 0267), they name the next action instead of
 * leftover-map explained leftover share; a missing or non-finite value
 * falls back in order — leftover-map coordinates, explained leftover
 * share, unexplained leftover share, cross share, reconstruction,
 * unexplained leftover, then the existing residual/rank/observed-expected
 * next action. When four finite coordinates exist, ADR 0268 draws the
 * leftover-map graphic display above the pair buttons; click a post
 * marker opens that post. ADR 0269 captions those leftover-map axes with
 * persisted leftover-map axis share when finite. ADR 0270 ticks those
 * leftover-map axes at persisted ``ξ`` / ``ζ`` so the pair-row badge matches
 * the plot. ADR 0271 names persisted leftover-map distance ``d`` on those
 * pair segments. ADR 0272 names persisted leftover-map reconstruction
 * ``R̂`` on those pair segments. ADR 0273 names persisted leftover-map
 * explained leftover share ``e`` on those pair segments. ADR 0274 names
 * persisted leftover-map unexplained leftover share ``s`` on those pair
 * segments. ADR 0275 names persisted leftover-map cross share ``x`` on
 * those pair segments. ADR 0276 names persisted leftover-map unexplained
 * leftover ``U`` on those pair segments. ADR 0277 names persisted leftover
 * residual ``R`` on those pair segments. ADR 0278 names persisted leftover
 * observed ``Y`` on those pair segments. ADR 0279 names persisted leftover
 * expected ``E`` on those pair segments. ADR 0280 names persisted leftover-map
 * rank on those pair segments. ADR 0281 names persisted leftover-map
 * complete-case coverage on the graphic. ADR 0282 names persisted leftover-map
 * item complete-case coverage on the graphic. ADR 0283 names persisted leftover-map
 * incomplete post coverage on the graphic. ADR 0284 names persisted leftover-map
 * incomplete item coverage on the graphic. ADR 0285 names persisted leftover-map
 * item complete-case coverage on the pair-list note. ADR 0286 names persisted leftover-map
 * incomplete post coverage on the pair-list note. ADR 0287 names persisted leftover-map
 * incomplete item coverage on the pair-list note. ADR 0288 fail-closes pair-list
 * leftover-map post complete-case coverage through leftoverMapCoverageCounts so
 * used-greater-than-scored, negative, or non-integer counts omit that note. ADR 0289
 * names persisted leftover-map post complete-case coverage on the grouping
 * comparison strip, not this pair list. ADR 0290 names persisted leftover-map
 * item complete-case coverage on the grouping comparison strip, not this pair
 * list. ADR 0291 names persisted leftover-map incomplete post coverage on the
 * grouping comparison strip, not this pair list. ADR 0292 names persisted leftover-map
 * incomplete item coverage on the grouping comparison strip, not this pair list. ADR 0293
 * names persisted leftover-map reconstruction on grouping comparison leftover-pair
 * buttons, not this pair list. ADR 0294 names persisted leftover-map explained leftover
 * share on grouping comparison leftover-pair buttons, not this pair list. ADR 0295 names
 * persisted leftover-map unexplained leftover share on grouping comparison leftover-pair
 * buttons, not this pair list. ADR 0296 names persisted leftover-map cross share on
 * grouping comparison leftover-pair buttons, not this pair list. ADR 0297 names
 * persisted leftover-map unexplained leftover on grouping comparison leftover-pair
 * buttons, not this pair list. ADR 0298 names persisted leftover residual on
 * grouping comparison leftover-pair buttons, not this pair list. ADR 0299 names
 * persisted leftover observed on grouping comparison leftover-pair buttons, not
 * this pair list. ADR 0300 names persisted leftover expected on grouping
 * comparison leftover-pair buttons, not this pair list. ADR 0301 names
 * persisted leftover-map rank on grouping comparison leftover-pair
 * buttons, not this pair list. ADR 0302 names persisted leftover-map
 * coordinates on grouping comparison leftover-pair buttons, not this
 * pair list. ADR 0303 returns persisted leftover-map coordinates on
 * grouping comparison leftover pairs, not this pair list. ADR 0304 draws
 * the leftover-map graphic display on the grouping comparison strip, not
 * this pair list. Every badge still
 * renders together before opening the named post.
 */
export function LeftoverPairList({
  pairs,
  leftoverMapAxes,
  leftoverMapCoverage,
  criterionLabel,
  onSelectPost,
}: LeftoverPairListProps) {
  if (pairs.length === 0) {
    return null;
  }
  return (
    <div>
      <LeftoverMapPlot
        pairs={pairs}
        leftoverMapAxes={leftoverMapAxes}
        leftoverMapCoverage={leftoverMapCoverage}
        criterionLabel={criterionLabel}
        onSelectPost={onSelectPost}
      />
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
        const unexplainedShareBadge = formatLeftoverMapUnexplainedShare(
          pair.leftover_map_unexplained_share,
        );
        const explainedShareBadge = formatLeftoverMapExplainedShare(
          pair.leftover_map_explained_share,
        );
        const coordinatesBadge = formatLeftoverMapCoordinates(
          pair.leftover_map_person_axis_1,
          pair.leftover_map_person_axis_2,
          pair.leftover_map_item_axis_1,
          pair.leftover_map_item_axis_2,
        );
        const crossShareBadge = formatLeftoverMapCrossShare(pair.leftover_map_cross_share);
        const reconstruction = formatLeftoverMapReconstruction(
          pair.leftover_map_reconstruction,
        );
        const unexplainedShareValue =
          pair.leftover_map_unexplained_share != null &&
          Number.isFinite(pair.leftover_map_unexplained_share)
            ? pair.leftover_map_unexplained_share.toFixed(2)
            : "—";
        const explainedShareValue =
          pair.leftover_map_explained_share != null &&
          Number.isFinite(pair.leftover_map_explained_share)
            ? pair.leftover_map_explained_share.toFixed(2)
            : "—";
        const crossShareValue =
          pair.leftover_map_cross_share != null && Number.isFinite(pair.leftover_map_cross_share)
            ? pair.leftover_map_cross_share.toFixed(2)
            : "—";
        const personCoordinateValue = formatLeftoverMapCoordinatePair(
          pair.leftover_map_person_axis_1,
          pair.leftover_map_person_axis_2,
        );
        const itemCoordinateValue = formatLeftoverMapCoordinatePair(
          pair.leftover_map_item_axis_1,
          pair.leftover_map_item_axis_2,
        );
        let nextAction: string;
        if (coordinatesBadge !== null && personCoordinateValue !== null && itemCoordinateValue !== null) {
          nextAction = tf(LEFTOVER_MAP_COORDINATES_ACTION, {
            person: personCoordinateValue,
            item: itemCoordinateValue,
            criterion,
          });
        } else if (explainedShareBadge !== null) {
          nextAction = tf(LEFTOVER_MAP_EXPLAINED_SHARE_ACTION, {
            value: explainedShareValue,
            criterion,
          });
        } else if (unexplainedShareBadge !== null) {
          nextAction = tf(LEFTOVER_MAP_UNEXPLAINED_SHARE_ACTION, {
            value: unexplainedShareValue,
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
              {unexplainedShareBadge ? (
                <span className="post-badge">{unexplainedShareBadge}</span>
              ) : null}
              {explainedShareBadge ? (
                <span className="post-badge">{explainedShareBadge}</span>
              ) : null}
              {crossShareBadge ? <span className="post-badge">{crossShareBadge}</span> : null}
              {reconstruction ? <span className="post-badge">{reconstruction}</span> : null}
              {coordinatesBadge ? <span className="post-badge">{coordinatesBadge}</span> : null}
              <span className="post-badge">d {pair.leftover_distance.toFixed(2)}</span>
            </button>
          </li>
        );
      })}
      </ul>
    </div>
  );
}
