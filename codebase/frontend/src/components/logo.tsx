import Link from "next/link";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      href="/"
      className="group inline-flex items-center gap-2.5 font-semibold tracking-tight"
      aria-label="ZicZord, về trang chủ"
    >
      <span className="logo-mark" aria-hidden="true">
        Z
      </span>
      {!compact && (
        <span className="text-[15px] font-bold">
          Zic<span className="text-accent-strong">Zord</span>
        </span>
      )}
    </Link>
  );
}
