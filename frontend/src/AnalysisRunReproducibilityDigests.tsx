import { useId, useState } from "react";
import {
  ANALYSIS_RUN_DIGEST_TARGET_MIN_PX,
  analysisRunDigestButtonLabel,
  analysisRunDigestNextAction,
  analysisRunDigestRevealedNextAction,
  type AnalysisRunDigestKind,
} from "./analysisRunDigests";

/**
 * One digest disclosure. The button name stays the audible prefix; the
 * full value stays in the document with `hidden` until Enter, Space, or
 * click so `aria-controls` always has a target (APG Disclosure).
 */
function AnalysisRunDigestDisclosure({
  kind,
  digest,
  panelId,
  open,
  onOpenChange,
}: {
  kind: AnalysisRunDigestKind;
  digest: string;
  panelId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const label = analysisRunDigestButtonLabel(kind, digest);
  return (
    <span className="analysis-run-digest">
      <button
        type="button"
        className="analysis-run-digest-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        style={{
          minHeight: ANALYSIS_RUN_DIGEST_TARGET_MIN_PX,
          minWidth: ANALYSIS_RUN_DIGEST_TARGET_MIN_PX,
        }}
        onClick={() => onOpenChange(!open)}
      >
        {label}
      </button>
      <code id={panelId} className="analysis-run-digest-full" hidden={!open}>
        {digest}
      </code>
    </span>
  );
}

/**
 * Labeled group of analysis-run reproducibility digests.
 *
 * Prefixes remain the accessible contents of the group. Full digests
 * stay off the home list and stay `hidden` on the detail until the
 * operator activates a prefix.
 */
export function AnalysisRunReproducibilityDigests({
  codeRevisionSha,
  configurationSha256,
}: {
  codeRevisionSha?: string;
  configurationSha256?: string;
}) {
  const id = useId();
  const [openCode, setOpenCode] = useState(false);
  const [openConfig, setOpenConfig] = useState(false);
  if (!codeRevisionSha && !configurationSha256) {
    return null;
  }
  const anyOpen =
    (Boolean(codeRevisionSha) && openCode) ||
    (Boolean(configurationSha256) && openConfig);
  return (
    <div role="group" aria-label="Analysis run reproducibility digests">
      <p className="post-meta">
        {anyOpen
          ? analysisRunDigestRevealedNextAction()
          : analysisRunDigestNextAction()}
      </p>
      <p className="post-meta analysis-run-digest-row">
        {codeRevisionSha ? (
          <AnalysisRunDigestDisclosure
            kind="code"
            digest={codeRevisionSha}
            panelId={`${id}-code`}
            open={openCode}
            onOpenChange={setOpenCode}
          />
        ) : null}
        {codeRevisionSha && configurationSha256 ? " · " : null}
        {configurationSha256 ? (
          <AnalysisRunDigestDisclosure
            kind="config"
            digest={configurationSha256}
            panelId={`${id}-config`}
            open={openConfig}
            onOpenChange={setOpenConfig}
          />
        ) : null}
      </p>
    </div>
  );
}
