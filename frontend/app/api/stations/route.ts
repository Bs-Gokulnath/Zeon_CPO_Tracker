import { NextRequest, NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams.toString();
  const url = `${API}/stations${params ? `?${params}` : ""}`;
  const res = await fetch(url, { next: { revalidate: 0 } });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
