const GENERIC_TEAM_ACTOR_NAMES = new Set([
  "사업부",
  "부서",
  "팀",
  "business unit",
  "department",
  "division",
]);

export function isGenericTeamActor(actorTypeCode: string, actorName: string): boolean {
  const normalizedName = actorName.trim().replace(/\s+/g, " ").toLowerCase();
  return actorTypeCode === "prov_team" && GENERIC_TEAM_ACTOR_NAMES.has(normalizedName);
}
