import { GithubLogo } from "@phosphor-icons/react/dist/ssr";
import { site } from "@/lib/site";

export function SiteNav({ preview }: { preview: boolean }) {
  return (
    <header className="absolute inset-x-0 top-0 z-20">
      <nav
        aria-label="Primary"
        className="mx-auto flex h-16 max-w-[1240px] items-center justify-between gap-4 px-4 sm:px-8"
      >
        <a href="#top" className="font-mono text-sm text-ink">
          clickstream<span className="text-accent">/</span>funnel
        </a>
        <div className="flex items-center gap-3 sm:gap-5">
          {preview ? (
            <a
              href="#about-data"
              className="inline-flex items-center gap-2 whitespace-nowrap rounded-full border border-rule-2 px-3 py-1 font-mono text-xs text-ink-2 transition-colors hover:border-ink-3 hover:text-ink"
            >
              <span aria-hidden className="size-1.5 rounded-full bg-data-dup" />
              Preview<span className="hidden sm:inline"> data</span>
            </a>
          ) : null}
          <a
            href={site.repoUrl}
            className="inline-flex items-center gap-2 whitespace-nowrap text-sm text-ink-2 transition-colors hover:text-ink"
          >
            <GithubLogo size={18} weight="regular" aria-hidden />
            <span className="sr-only sm:not-sr-only">Read the code</span>
          </a>
        </div>
      </nav>
    </header>
  );
}
