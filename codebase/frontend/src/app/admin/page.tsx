import type { Metadata } from "next";

import { AdminConsole } from "@/components/admin-console";

export const metadata: Metadata = {
  title: "Context Admin | Kute",
  description: "Quản lý context, retrieval tools và confirmed memory của Kute.",
};

export default function AdminPage() {
  return <AdminConsole />;
}
