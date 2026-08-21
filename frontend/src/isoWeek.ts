const MS_PER_DAY = 86_400_000;

/** ISO-8601 week (YYYY-Www) from a UTC timestamp. Thursday decides the ISO year. */
export function isoWeekFromCreatedAt(createdAt: string | null | undefined): string | null {
  if (!createdAt) {
    return null;
  }
  const datePrefix = /^(\d{4})-(\d{2})-(\d{2})T/.exec(createdAt);
  if (!datePrefix) {
    return null;
  }
  const year = Number(datePrefix[1]);
  const month = Number(datePrefix[2]);
  const day = Number(datePrefix[3]);
  const calendarDate = new Date(0);
  calendarDate.setUTCHours(0, 0, 0, 0);
  calendarDate.setUTCFullYear(year, month - 1, day);
  if (
    calendarDate.getUTCFullYear() !== year ||
    calendarDate.getUTCMonth() !== month - 1 ||
    calendarDate.getUTCDate() !== day
  ) {
    return null;
  }
  const parsed = new Date(createdAt);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  const utcDate = new Date(
    Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate()),
  );
  const weekday = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - weekday);
  const isoYear = utcDate.getUTCFullYear();
  const yearStart = new Date(Date.UTC(isoYear, 0, 1));
  const week = Math.ceil(((utcDate.getTime() - yearStart.getTime()) / MS_PER_DAY + 1) / 7);
  return `${isoYear}-W${String(week).padStart(2, "0")}`;
}

/** Lexicographic latest ISO week among already-formatted YYYY-Www values. */
export function latestIsoWeek(weeks: Array<string | null | undefined>): string | null {
  const present = weeks.filter((week): week is string => Boolean(week));
  if (present.length === 0) {
    return null;
  }
  return present.reduce((latest, week) => (week > latest ? week : latest));
}
