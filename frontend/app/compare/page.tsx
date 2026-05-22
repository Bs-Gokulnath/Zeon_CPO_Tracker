export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { CompareShell } from "./CompareShell";

export default function ComparePage() {
  return (
    <Suspense>
      <CompareShell />
    </Suspense>
  );
}
