import { NextRequest, NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const res = await fetch(`${API}/analytics/${slug}`, { next: { revalidate: 300 } });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
