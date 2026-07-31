import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";

export function SiteNav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-line/70 bg-paper/80 backdrop-blur-xl">
      <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-5 md:px-9">
        <Logo />
        <nav className="hidden items-center gap-7 text-sm text-muted md:flex" aria-label="Pitch">
          <a className="nav-link" href="#problem">
            Vấn đề
          </a>
          <a className="nav-link" href="#scope">
            Memory scopes
          </a>
          <a className="nav-link" href="#telegram">
            Telegram
          </a>
          <a className="nav-link" href="#trust">
            Quyền truy cập
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/chat" className="button button-small">
            Mở demo
            <ArrowRight size={16} weight="bold" />
          </Link>
        </div>
      </div>
    </header>
  );
}
