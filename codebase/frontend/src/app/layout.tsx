import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistSans = localFont({
  src: "../../node_modules/next/dist/next-devtools/server/font/geist-latin-ext.woff2",
  variable: "--font-geist-sans",
  display: "swap",
  weight: "100 900",
});

const geistMono = localFont({
  src: "../../node_modules/next/dist/next-devtools/server/font/geist-mono-latin-ext.woff2",
  variable: "--font-geist-mono",
  display: "swap",
  weight: "100 900",
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: "ZicZord | Discord Action Copilot",
  description:
    "Biến hội thoại Discord thành action item có owner, deadline và human-confirmed sync qua MCP connectors.",
  keywords: [
    "Discord",
    "MCP",
    "Google Tasks",
    "AI agent",
    "team management",
    "action item",
  ],
  openGraph: {
    title: "ZicZord | Discord Action Copilot",
    description:
      "Từ chat Discord thành task đã chốt, có owner, deadline và quyền hạn rõ ràng.",
    type: "website",
    locale: "vi_VN",
    images: [
      {
        url: "/images/ziczord-mcp-workflow.png",
        width: 1448,
        height: 1086,
        alt: "ZicZord chuyển hội thoại Discord thành action item qua MCP",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "ZicZord | Discord Action Copilot",
    description: "Từ chat Discord thành task đã chốt.",
    images: ["/images/ziczord-mcp-workflow.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
      data-scroll-behavior="smooth"
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
