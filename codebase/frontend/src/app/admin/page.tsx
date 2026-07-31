import type { Metadata } from "next";

import { AdminConsole } from "@/components/admin-console";

export const metadata: Metadata = {
  title: "AI Evaluation | ZicZord",
  description:
    "Theo dõi evaluation, context, retrieval tools và confirmed memory của ZicZord.",
};

export default function AdminPage() {
  return <AdminConsole />;
}
