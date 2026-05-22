import { NextRequest, NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const res = await fetch(`${API}/stations/${id}`, { next: { revalidate: 60 } });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
