"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from "recharts";
import { Zap, MapPin, Users, Activity, Star, Plug } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useOverview, useStateDistribution, useOperatorDistribution,
  useAcDcBreakdown, useChargerSpeed,
} from "@/hooks/useAnalytics";

// ── KPI card ─────────────────────────────────────────────────────────────────
function KPI({
  label, value, sub, icon: Icon, loading,
}: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; loading?: boolean;
}) {
  return (
    <div className="rounded-xl border border-border bg-card/50 px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </div>
      {loading ? (
        <Skeleton className="h-7 w-20" />
      ) : (
        <p className="text-2xl font-bold">{value}</p>
      )}
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">{title}</h2>
      {children}
    </div>
  );
}

// ── Colours ───────────────────────────────────────────────────────────────────
const AC_COLOR   = "#60a5fa";
const DC_COLOR   = "#fb923c";
const MIX_COLOR  = "#c084fc";
const PIE_COLORS = [AC_COLOR, DC_COLOR, MIX_COLOR];

// ── Custom tooltip ────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  );
}

// ── State distribution bar chart ──────────────────────────────────────────────
function StateChart() {
  const { data = [], isLoading } = useStateDistribution();

  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;

  const top15 = [...data].sort((a, b) => b.total_stations - a.total_stations).slice(0, 15);

  return (
    <div className="rounded-xl border border-border bg-card/50 p-4">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={top15} margin={{ top: 4, right: 8, bottom: 40, left: 0 }}>
          <XAxis
            dataKey="state_name"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            angle={-35}
            textAnchor="end"
            interval={0}
          />
          <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} width={30} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted)/0.3)" }} />
          <Bar dataKey="total_stations" name="Stations" radius={[4, 4, 0, 0]} fill={AC_COLOR} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── AC / DC / Mixed pie ───────────────────────────────────────────────────────
function AcDcPie() {
  const { data, isLoading } = useAcDcBreakdown();

  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;
  if (!data) return null;

  const pieData = [
    { name: "AC",    value: data.ac_stations },
    { name: "DC",    value: data.dc_stations },
    { name: "Mixed", value: data.mixed_stations },
  ].filter((d) => d.value > 0);

  return (
    <div className="rounded-xl border border-border bg-card/50 p-4">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%" cy="50%"
            innerRadius={55} outerRadius={85}
            paddingAngle={3}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {pieData.map((_, i) => (
              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
      {data.avg_highest_power_kw && (
        <p className="text-center text-xs text-muted-foreground mt-1">
          Avg peak power <span className="font-semibold text-foreground">{Number(data.avg_highest_power_kw).toFixed(1)} kW</span>
        </p>
      )}
    </div>
  );
}

// ── Operator bar chart (top 10) ───────────────────────────────────────────────
function OperatorChart() {
  const { data = [], isLoading } = useOperatorDistribution();

  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;

  const top10 = [...data].sort((a, b) => b.total_stations - a.total_stations).slice(0, 10);

  return (
    <div className="rounded-xl border border-border bg-card/50 p-4">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={top10} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 80 }}>
          <XAxis type="number" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
          <YAxis
            type="category" dataKey="operator_name"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            width={80}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted)/0.3)" }} />
          <Bar dataKey="total_stations" name="Stations" radius={[0, 4, 4, 0]} fill={DC_COLOR} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Charger speed breakdown ───────────────────────────────────────────────────
function SpeedChart() {
  const { data = [], isLoading } = useChargerSpeed();

  if (isLoading) return <Skeleton className="h-64 w-full rounded-xl" />;

  const grouped: Record<string, { ac: number; dc: number }> = {};
  for (const item of data) {
    if (!grouped[item.speed_category]) grouped[item.speed_category] = { ac: 0, dc: 0 };
    if (item.charger_type === "AC") grouped[item.speed_category].ac += item.charger_count;
    else grouped[item.speed_category].dc += item.charger_count;
  }
  const chartData = Object.entries(grouped).map(([cat, v]) => ({ cat, ...v }));

  return (
    <div className="rounded-xl border border-border bg-card/50 p-4">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <XAxis dataKey="cat" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
          <YAxis tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} width={40} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "hsl(var(--muted)/0.3)" }} />
          <Bar dataKey="ac" name="AC" stackId="a" fill={AC_COLOR} radius={[0, 0, 0, 0]} />
          <Bar dataKey="dc" name="DC" stackId="a" fill={DC_COLOR} radius={[4, 4, 0, 0]} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Price comparison ──────────────────────────────────────────────────────────
function PriceCard({ data }: { data: { avg_min_ac_price: number | null; avg_min_dc_price: number | null } }) {
  return (
    <div className="rounded-xl border border-border bg-card/50 p-4 space-y-3">
      <p className="text-xs text-muted-foreground uppercase tracking-wider">Avg Price / kWh</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 px-3 py-2 text-center">
          <p className="text-xs text-blue-400 mb-1">AC</p>
          <p className="text-lg font-bold">
            {data.avg_min_ac_price != null ? `₹${Number(data.avg_min_ac_price).toFixed(1)}` : "—"}
          </p>
        </div>
        <div className="rounded-lg bg-orange-500/10 border border-orange-500/20 px-3 py-2 text-center">
          <p className="text-xs text-orange-400 mb-1">DC</p>
          <p className="text-lg font-bold">
            {data.avg_min_dc_price != null ? `₹${Number(data.avg_min_dc_price).toFixed(1)}` : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Availability ring ─────────────────────────────────────────────────────────
function AvailabilityRing({ total, available }: { total: number; available: number }) {
  const pct = total > 0 ? Math.round((available / total) * 100) : 0;
  const pieData = [
    { name: "Available", value: available },
    { name: "Offline",   value: total - available },
  ];
  return (
    <div className="rounded-xl border border-border bg-card/50 p-4">
      <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Availability</p>
      <div className="flex items-center gap-4">
        <div className="relative w-24 h-24 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={28} outerRadius={42} dataKey="value" paddingAngle={2} startAngle={90} endAngle={-270}>
                <Cell fill="#4ade80" />
                <Cell fill="hsl(var(--muted))" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-base font-bold">{pct}%</span>
          </div>
        </div>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400 shrink-0" />
            <span className="text-muted-foreground">Available</span>
            <span className="font-semibold ml-auto">{available.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-muted shrink-0" />
            <span className="text-muted-foreground">Offline</span>
            <span className="font-semibold ml-auto">{(total - available).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main shell ────────────────────────────────────────────────────────────────
export function AnalyticsShell() {
  const { data: ov, isLoading: ovLoading } = useOverview();
  const { data: breakdown } = useAcDcBreakdown();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">

        <div>
          <h1 className="text-xl font-bold mb-0.5">Analytics</h1>
          <p className="text-sm text-muted-foreground">Network-wide stats from the scraped Statiq dataset.</p>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KPI label="Stations"   value={ov?.total_stations?.toLocaleString() ?? "—"}  icon={Zap}      loading={ovLoading} />
          <KPI label="Chargers"   value={ov?.total_chargers?.toLocaleString() ?? "—"}  icon={Plug}     loading={ovLoading} />
          <KPI label="States"     value={ov?.states_covered ?? "—"}                    icon={MapPin}   loading={ovLoading} />
          <KPI label="Cities"     value={ov?.cities_covered ?? "—"}                    icon={MapPin}   loading={ovLoading} />
          <KPI label="Operators"  value={ov?.operators_count ?? "—"}                   icon={Users}    loading={ovLoading} />
          <KPI label="Avg Rating" value={ov?.avg_rating != null ? Number(ov.avg_rating).toFixed(2) : "—"} icon={Star} loading={ovLoading} />
        </div>

        {/* Availability + Price */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {ovLoading
            ? <Skeleton className="h-32 rounded-xl" />
            : ov && <AvailabilityRing total={ov.total_stations} available={ov.available_stations} />
          }
          {breakdown
            ? <PriceCard data={breakdown} />
            : <Skeleton className="h-32 rounded-xl" />
          }
        </div>

        {/* State distribution */}
        <Section title="Stations by State (Top 15)">
          <StateChart />
        </Section>

        {/* AC/DC type + Charger speed */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Section title="Station Type Breakdown">
            <AcDcPie />
          </Section>
          <Section title="Charger Speed Categories">
            <SpeedChart />
          </Section>
        </div>

        {/* Operator distribution */}
        <Section title="Top Operators by Station Count">
          <OperatorChart />
        </Section>

      </div>
    </div>
  );
}
