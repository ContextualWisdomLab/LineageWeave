import type { PostRoleResponsibility } from "../api";

export const ROLES_EMPTY = "역할·책임이 아직 없습니다";
export const ROLES_NEXT_DECISION = "다음 사람 조치를 이 행위자에서 결정하세요.";

type ActorTypeCode = "prov_person" | "prov_organization" | "prov_team";

function isActorTypeCode(code: string): code is ActorTypeCode {
  return code === "prov_person" || code === "prov_organization" || code === "prov_team";
}

function actorTypeLabel(code: string): string {
  if (!isActorTypeCode(code)) {
    return code;
  }
  switch (code) {
    case "prov_person":
      return "Person";
    case "prov_organization":
      return "Organization";
    case "prov_team":
      return "Team";
    default: {
      const _exhaustive: never = code;
      return _exhaustive;
    }
  }
}

export type RolesResponsibilitiesProps = {
  roles: PostRoleResponsibility[] | null;
  unavailable?: boolean;
};

export function RolesResponsibilities({ roles, unavailable }: RolesResponsibilitiesProps) {
  return (
    <section className="popup-section" role="region" aria-label="역할·책임">
      <h3>역할·책임</h3>
      {unavailable ? (
        <p className="popup-placeholder">{ROLES_EMPTY}</p>
      ) : null}
      {!unavailable && roles === null ? <p>Loading...</p> : null}
      {!unavailable && roles && roles.length === 0 ? (
        <p className="popup-placeholder">{ROLES_EMPTY}</p>
      ) : null}
      {!unavailable && roles && roles.length > 0 ? (
        <>
          <p className="post-meta" role="status" aria-label="R&R next decision">
            {ROLES_NEXT_DECISION}
          </p>
          <ul>
            {roles.map((rr, index) => (
              <li key={`${rr.actor_type_code}:${rr.actor_name}:${index}`}>
                <span className={`actor-type-badge actor-type-${rr.actor_type_code}`}>
                  {actorTypeLabel(rr.actor_type_code)}
                </span>{" "}
                <strong>{rr.actor_name}</strong>
                {rr.affiliated_organization_name ? (
                  <span className="rr-affiliation"> ({rr.affiliated_organization_name})</span>
                ) : null}
                : {rr.responsibility}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
