import { redirect } from "next/navigation";

// The standalone parts page folded into /orders as its Stock Orders tab
// (2026-07-23). Old links and bookmarks land there.
export default async function PartsRedirect({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  redirect(`/orders?tab=parts${q ? `&q=${encodeURIComponent(q)}` : ""}`);
}
