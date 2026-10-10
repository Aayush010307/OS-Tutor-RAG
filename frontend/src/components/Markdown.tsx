import { memo, useMemo, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import bash from "highlight.js/lib/languages/bash";
import c from "highlight.js/lib/languages/c";
import cpp from "highlight.js/lib/languages/cpp";
import python from "highlight.js/lib/languages/python";
import plaintext from "highlight.js/lib/languages/plaintext";
import { CopyButton } from "./CopyButton";
import { formatLocation, linkCitations } from "../lib/tutor";
import type { Source } from "../types";

// Only the languages an OS course writes; unlabelled blocks (pseudocode) stay plain.
const highlightOptions = {
  languages: { bash, c, cpp, python, plaintext },
  aliases: { bash: ["sh", "shell", "console"], plaintext: ["pseudo", "pseudocode", "text"] },
};

/** Model output is untrusted: raw HTML is never rendered (react-markdown escapes it) and only these schemes link. */
function safeUrl(url: string): string {
  return /^(https?:|cite:S\d+$)/i.test(url) ? url : "";
}

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) return textOf((node.props as { children?: ReactNode }).children);
  return "";
}

interface Props {
  text: string;
  sources: Source[];
  onCite: (ref: string) => void;
}

const staticComponents: Components = {
  img: ({ alt }) => <span>{alt}</span>,
  pre({ children }) {
    const code = textOf(children).replace(/\n$/, "");
    const child = Array.isArray(children) ? children[0] : children;
    const cls = (child && typeof child === "object" && "props" in child ? (child.props as { className?: string }).className : "") ?? "";
    const lang = /language-(\w+)/.exec(cls)?.[1];
    return (
      <div className="not-prose overflow-hidden rounded-panel border border-line bg-code">
        <div className="flex items-center justify-between border-b border-line py-0.5 pl-3.5 pr-1">
          <span className="font-mono text-meta text-ink-3">{lang ?? "code"}</span>
          <CopyButton text={code} label="Copy code" />
        </div>
        <pre className="code-body overflow-x-auto px-3.5 py-3">{children}</pre>
      </div>
    );
  },
};

const Markdown = memo(function Markdown({ text, sources, onCite }: Props) {
  // Only the citation renderer depends on props; the rest are module constants so code blocks never remount.
  const components: Components = useMemo(() => ({
    ...staticComponents,
    a({ href, children }) {
      if (href?.startsWith("cite:")) {
        const ref = href.slice(5);
        const src = sources.find((s) => s.ref === ref);
        const where = src ? formatLocation(src.location) : null;
        const label = src ? `Source ${ref.slice(1)}: ${src.filename}${where ? `, ${where}` : ""}` : `Source ${ref}`;
        return (
          <button
            type="button"
            className="cite mx-0.5 inline-flex h-[1.35rem] translate-y-[-1px] items-center rounded-[5px] border border-accent-line bg-accent-soft px-1.5 align-middle font-mono text-[0.72rem] font-semibold leading-none text-accent transition-colors hover:bg-accent-strong hover:text-on-accent"
            onClick={() => onCite(ref)}
            aria-label={label}
            title={label}
          >
            {ref}
          </button>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
  }), [sources, onCite]);

  return (
    <div className="prose-tutor">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeHighlight, highlightOptions]]} urlTransform={safeUrl} components={components}>
        {linkCitations(text, sources)}
      </ReactMarkdown>
    </div>
  );
});

export default Markdown;
