import Link from "next/link";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      href="/"
      className="group inline-flex items-center gap-2.5 font-semibold tracking-tight"
      aria-label="Kute, về trang chủ"
    >
      <span className="logo-mark" aria-hidden="true">
        K
      </span>
      {!compact && (
        <span className="text-[15px] font-bold">
          Kute<span className="text-muted">.memory</span>
        </span>
      )}
    </Link>
  );
}
