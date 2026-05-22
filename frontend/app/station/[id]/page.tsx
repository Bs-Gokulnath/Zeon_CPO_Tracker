export const dynamic = "force-dynamic";

import { Suspense }              from "react";
import { StationDetailShell }   from "./StationDetailShell";
import { StationDetailSkeleton } from "@/components/station/StationDetailSkeleton";

export default async function StationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const stationId = parseInt(id, 10);

  return (
    <Suspense fallback={<StationDetailSkeleton />}>
      <StationDetailShell id={isNaN(stationId) ? -1 : stationId} />
    </Suspense>
  );
}
