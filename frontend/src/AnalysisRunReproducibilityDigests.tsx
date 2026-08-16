import { useId, useState } from "react";
import {
  analysisRunDigestButtonLabel,
  analysisRunDigestNextAction,
  type AnalysisRunDigestKind,
} from "./analysisRunDigests";

/**
 * One digest disclosure. The button name stays the audible prefix; the
 * full value is shown only after Enter, Space, or click (APG Disclosure).
 */
function AnalysisRunDigestDisclosure({
  kind,
  digest,
  panelId,
}: {
  kind: AnalysisRunDigestKind;
  digest: string;
  panelId: string;
}) {
  const [open, setOpen] = useState(false);
  const label = analysisRunDigestButtonLabel(kind, digest);
  return (
    <span className="analysis-run-digest">
      <button
        type="button"
        className="analysis-run-digest-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
      >
        {label}
      </button>
      {open ? (
        <code id={panelId} className="analysis-run-digest-full">
          {digest}
        </code>
      ) : null}
    </span>
  );
}

/**
 * Labeled group of analysis-run reproducibility digests.
 *
 * Prefixes remain the accessible contents of the group. Full digests
 * stay off the home list and off the default detail text until the
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
  if (!codeRevisionSha && !configurationSha256) {
    return null;
  }
  return (
    <div role="group" aria-label="Analysis run reproducibility digests">
      <p className="post-meta">{analysisRunDigestNextAction()}</p>
      <p className="post-meta analysis-run-digest-row">
        {codeRevisionSha ? (
          <AnalysisRunDigestDisclosure
            kind="code"
            digest={codeRevisionSha}
            panelId={`${id}-code`}
          />
        ) : null}
        {codeRevisionSha && configurationSha256 ? " · " : null}
        {configurationSha256 ? (
          <AnalysisRunDigestDisclosure
            kind="config"
            digest={configurationSha256}
            panelId={`${id}-config`}
          />
        ) : null}
      </p>
    </div>
  );
}
