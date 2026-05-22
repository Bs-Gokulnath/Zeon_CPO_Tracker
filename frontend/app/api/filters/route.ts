import { NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function GET() {
  const res = await fetch(`${API}/filters`, { next: { revalidate: 1800 } });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
