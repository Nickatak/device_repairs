import type { Metadata } from "next";
import { getOptions, type Options } from "@/lib/api/options";
import { getTemplates } from "@/lib/api/templates";
import type { NoteTemplate } from "@/lib/api/repairlog";
import TemplatesView from "@/components/templates/TemplatesView";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Note Templates" };

export default async function TemplatesPage({
  searchParams,
}: {
  searchParams: Promise<{ reference?: string }>;
}) {
  const params = await searchParams;
  let templates: NoteTemplate[] = [];
  let options: Options | null = null;
  let error: string | null = null;
  try {
    [templates, options] = await Promise.all([getTemplates(), getOptions()]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Unknown error";
  }

  return (
    <TemplatesView
      templates={templates}
      options={options}
      error={error}
      initialReference={params.reference ? Number(params.reference) : null}
    />
  );
}
