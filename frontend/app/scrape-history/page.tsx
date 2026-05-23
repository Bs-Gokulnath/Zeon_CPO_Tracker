export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { ScrapeHistoryShell } from "./ScrapeHistoryShell";

export default function ScrapeHistoryPage() {
  return (
    <Suspense>
      <ScrapeHistoryShell />
    </Suspense>
  );
}
