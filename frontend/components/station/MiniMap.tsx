import dynamic from "next/dynamic";

const MiniMapInner = dynamic(
  () => import("./MiniMapInner").then((m) => ({ default: m.MiniMapInner })),
  {
    ssr:     false,
    loading: () => <div className="h-[220px] bg-muted animate-pulse rounded-xl" />,
  }
);

interface Props {
  lat:  number;
  lon:  number;
  name: string;
}

export function MiniMap({ lat, lon, name }: Props) {
  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
        Location
      </h2>
      <div className="rounded-xl overflow-hidden border border-border">
        <MiniMapInner lat={lat} lon={lon} name={name} />
      </div>
    </section>
  );
}
