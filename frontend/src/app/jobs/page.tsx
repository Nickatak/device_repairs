import { redirect } from "next/navigation";

// Customer jobs live on /orders as its Jobs tab — same pattern as /parts.
export default async function JobsRedirect({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  redirect(`/orders?tab=job${q ? `&q=${encodeURIComponent(q)}` : ""}`);
}
