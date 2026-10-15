"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import ProgressPanel from "@/components/ProgressPanel";
import { ErrorBox } from "@/components/ui";
import { createTest } from "@/lib/api";
import type { NewTestInput } from "@/lib/types";

const CHANNELS = ["Quick commerce", "E-commerce marketplace", "Supermarket / retail", "D2C website", "Local kirana store", "Café / restaurant"];
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const LIVE_PERSONAS = 30;

const field = "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";

export default function NewTestForm() {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [image, setImage] = useState<{ base64: string; mime: string; preview: string } | null>(null);

  function onImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    setError(null);
    if (!file) return setImage(null);
    if (!file.type.startsWith("image/")) return setError("Please choose an image file (JPG, PNG or WebP).");
    if (file.size > MAX_IMAGE_BYTES) return setError("Image is too large. Please use one under 3 MB.");
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result);
      setImage({ base64: url.split(",")[1], mime: file.type, preview: url });
    };
    reader.readAsDataURL(file);
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const input: NewTestInput = {
      name: String(f.get("name")).trim(),
      description: String(f.get("description")).trim(),
      price_inr: Number(f.get("price_inr")),
      pack_size: String(f.get("pack_size")).trim(),
      channel: String(f.get("channel")),
      competitors: String(f.get("competitors") ?? "").trim() || undefined,
      ...(image && { image_base64: image.base64, image_mime: image.mime }),
    };
    setError(null);
    setRunning(true);
    try {
      const result = await createTest(input);
      router.push(`/test/${result.test_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      setRunning(false);
    }
  }

  return (
    <>
    {running && <ProgressPanel personas={LIVE_PERSONAS} />}
    {/* Kept mounted while running so the inputs survive an error. */}
    <form onSubmit={onSubmit} hidden={running} className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {error && <ErrorBox message={error} />}

      <label className="block text-sm font-medium text-slate-800">
        Product name
        <input name="name" required maxLength={80} placeholder="e.g. BrewChill Cold Coffee" className={field} />
      </label>

      <label className="block text-sm font-medium text-slate-800">
        Description
        <textarea name="description" required maxLength={600} rows={4} className={field}
          placeholder="What is it, who is it for, and what makes it different? e.g. Ready-to-drink Arabica cold coffee, less sugar than café drinks." />
      </label>

      <div className="grid gap-5 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-800">
          Price (₹)
          <input name="price_inr" type="number" required min={1} max={1000000} step="1" inputMode="numeric" placeholder="149" className={field} />
        </label>
        <label className="block text-sm font-medium text-slate-800">
          Pack size
          <input name="pack_size" required maxLength={60} placeholder="e.g. 300 ml can" className={field} />
        </label>
      </div>

      <label className="block text-sm font-medium text-slate-800">
        Sales channel
        <select name="channel" required defaultValue={CHANNELS[0]} className={field}>
          {CHANNELS.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>

      <label className="block text-sm font-medium text-slate-800">
        Similar products customers know <span className="font-normal text-slate-500">(optional)</span>
        <input name="competitors" maxLength={200} placeholder="e.g. Café cold coffee ₹180, canned cold brew ₹150" className={field} />
      </label>

      <div className="text-sm font-medium text-slate-800">
        Product or packaging image <span className="font-normal text-slate-500">(optional, under 3 MB)</span>
        <div className="mt-1 flex items-center gap-4">
          <input type="file" accept="image/png,image/jpeg,image/webp" onChange={onImage}
            className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:font-medium file:text-slate-800 hover:file:bg-slate-200" />
          {image && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={image.preview} alt="Selected product" className="h-16 w-16 rounded-md object-cover ring-1 ring-slate-200" />
          )}
        </div>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-500">Results are AI-simulated customers, a fast early signal before testing with real customers.</p>
        <button type="submit" className="rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-indigo-500">
          Run test on {LIVE_PERSONAS} AI customers
        </button>
      </div>
    </form>
    </>
  );
}
