import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

import { ChatShell } from "@/components/chat-shell";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";

export default function ChatPage() {
  return (
    <main className="flex min-h-dvh flex-col bg-surface">
      <header className="flex h-16 items-center justify-between border-b border-line bg-paper px-4 md:px-6">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="icon-button"
            aria-label="Quay về trang pitch"
            title="Về trang pitch"
          >
            <ArrowLeft size={17} weight="bold" />
          </Link>
          <Logo />
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-muted sm:inline">
            MVP · Discord snapshot đã chuẩn hóa
          </span>
          <ThemeToggle />
        </div>
      </header>
      <div className="mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 p-0 md:p-5">
        <ChatShell />
      </div>
    </main>
  );
}
