export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { AnalyticsShell } from "./AnalyticsShell";

export default function AnalyticsPage() {
  return (
    <Suspense>
      <AnalyticsShell />
    </Suspense>
  );
}
