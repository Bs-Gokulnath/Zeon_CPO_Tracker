import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatKw(kw: number | null | undefined): string {
  if (kw == null) return "—";
  return kw >= 1000 ? `${(kw / 1000).toFixed(0)} MW` : `${kw} kW`;
}

export function formatPrice(price: number | null | undefined, currency = "₹"): string {
  if (price == null) return "—";
  return `${currency}${price}/kWh`;
}

export function formatRating(rating: number | null | undefined): string {
  if (rating == null) return "—";
  return rating.toFixed(1);
}

export function formatDistance(km: number): string {
  return km < 1 ? `${Math.round(km * 1000)}m` : `${km.toFixed(1)}km`;
}
