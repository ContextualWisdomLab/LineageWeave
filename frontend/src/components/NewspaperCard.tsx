import type { PostSummary } from "../api";

export type NewspaperCardProps = {
  post: PostSummary;
  onOpen: (postId: string) => void;
};

function grainLabel(code: "team" | "process_unit" | "corporate"): string {
  switch (code) {
    case "corporate":
      return "Corporate";
    case "process_unit":
      return "PU";
    case "team":
      return "Team";
    default: {
      const _exhaustive: never = code;
      return _exhaustive;
    }
  }
}

export function NewspaperCard({ post, onOpen }: NewspaperCardProps) {
  const edition = post.edition;
  return (
    <article className="newspaper-card">
      <button
        type="button"
        className="newspaper-card-open"
        aria-label={`Open newspaper: ${post.post_title}`}
        onClick={() => onOpen(post.post_id)}
      >
        <h3>{post.post_title}</h3>
      </button>
      {edition?.empty_next_action && edition.sections.every((section) => section.titles.length === 0) ? (
        <p className="popup-placeholder">{edition.empty_next_action}</p>
      ) : null}
      {edition?.sections.map((section, index) => (
        <section key={`${section.grain_code}:${section.unit_label}:${index}`} className="newspaper-section">
          <h4>
            {grainLabel(section.grain_code)}
            {section.unit_label ? ` · ${section.unit_label}` : ""}
          </h4>
          {section.titles.length > 0 ? (
            <ul>
              {section.titles.map((title) => (
                <li key={title}>{title}</li>
              ))}
            </ul>
          ) : (
            <p className="popup-placeholder">{section.empty_next_action}</p>
          )}
        </section>
      ))}
    </article>
  );
}
