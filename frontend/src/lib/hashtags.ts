// Mirrors HASHTAG_RE in backend/accounts/services.py: '#' + word, inner hyphens allowed.
export const HASHTAG_RE = /#([\p{L}\p{N}_](?:[\p{L}\p{N}_-]*[\p{L}\p{N}_])?)/gu;

export function normalizeTag(raw: string): string {
  return raw.replace(/[^\p{L}\p{N}_-]/gu, "").replace(/^-+|-+$/g, "").toLowerCase().slice(0, 30);
}

interface Node {
  type: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: Node[];
}

/** Plain bio text -> Tiptap doc, with `#tags` as mention nodes. */
export function bioToDoc(text: string): Node {
  const paragraphs = text.split(/\r?\n/).map((line) => {
    const content: Node[] = [];
    let last = 0;
    for (const m of line.matchAll(HASHTAG_RE)) {
      const index = m.index ?? 0;
      if (index > last) content.push({ type: "text", text: line.slice(last, index) });
      const tag = m[1].toLowerCase();
      content.push({ type: "mention", attrs: { id: tag, label: tag, mentionSuggestionChar: "#" } });
      last = index + m[0].length;
    }
    if (last < line.length) content.push({ type: "text", text: line.slice(last) });
    return content.length ? { type: "paragraph", content } : { type: "paragraph" };
  });
  return { type: "doc", content: paragraphs };
}

/** Tiptap doc -> plain bio text; mentions become `#tag`. */
export function docToBio(doc: Node | null | undefined): string {
  if (!doc?.content) return "";
  return doc.content
    .map((p) =>
      (p.content ?? [])
        .map((n) => {
          if (n.type === "mention") return `#${(n.attrs?.label ?? n.attrs?.id ?? "") as string}`;
          if (n.type === "hardBreak") return "\n";
          return n.text ?? "";
        })
        .join(""),
    )
    .join("\n")
    .trim();
}

/** Split text into plain and hashtag parts for highlighted rendering. */
export function splitHashtags(text: string): { text: string; tag: boolean }[] {
  const parts: { text: string; tag: boolean }[] = [];
  let last = 0;
  for (const m of text.matchAll(HASHTAG_RE)) {
    const index = m.index ?? 0;
    if (index > last) parts.push({ text: text.slice(last, index), tag: false });
    parts.push({ text: m[0], tag: true });
    last = index + m[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), tag: false });
  return parts;
}
