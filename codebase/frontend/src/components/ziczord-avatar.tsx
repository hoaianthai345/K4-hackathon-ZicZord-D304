import Image from "next/image";

export function ZicZordAvatar({ className = "" }: { className?: string }) {
  return (
    <span
      className={`avatar avatar-bot avatar-image ${className}`.trim()}
      aria-hidden="true"
    >
      <Image
        src="/images/chatbot-avatar.jpg"
        alt=""
        width={96}
        height={96}
        sizes="96px"
      />
    </span>
  );
}
