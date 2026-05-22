export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { MapsShell } from "./MapsShell";

export default function MapsPage() {
  return (
    <Suspense>
      <MapsShell />
    </Suspense>
  );
}
