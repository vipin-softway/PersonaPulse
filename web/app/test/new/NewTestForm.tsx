"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import ProgressPanel from "@/components/ProgressPanel";
import { ErrorBox } from "@/components/ui";
import { createTest } from "@/lib/api";
import { PANELS, suggestPanel, type PanelId } from "@/lib/panels";
import type { NewTestInput } from "@/lib/types";

const CHANNELS = ["E-commerce marketplace", "Quick commerce", "D2C website", "Electronics store", "Local retail store", "Instagram / social ads"];
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const LIVE_PERSONAS = 30;

type Example = { label: string; panel: PanelId; name: string; description: string; price_inr: number; pack_size: string; channel: string; competitors: string };

// One-click examples, one per customer panel, so judges can try a live test without inventing a product.
const EXAMPLES: Example[] = [
  {
    label: "Wireless earbuds", panel: "accessories", name: "BudPro ENC Wireless Earbuds",
    description: "True wireless earbuds with environmental noise cancellation for calls, 40-hour total playtime, Type-C fast charging (10 min = 2 hours) and IPX5 sweat resistance.",
    price_inr: 1299, pack_size: "1 pair with charging case", channel: "E-commerce marketplace",
    competitors: "Budget earbuds ₹799–1,499, popular Indian audio brands ₹1,299–1,999",
  },
  {
    label: "Personal air cooler", panel: "home", name: "CoolNest 20L Personal Air Cooler",
    description: "Compact 20-litre air cooler for bedrooms and study rooms, honeycomb cooling pads, 3 fan speeds, runs on an inverter during power cuts, 110W.",
    price_inr: 4999, pack_size: "1 unit, 20 L tank", channel: "E-commerce marketplace",
    competitors: "Tower fans ₹2,500–4,000, branded personal coolers ₹5,500–7,500",
  },
  {
    label: "Smartwatch", panel: "electronics", name: "PulseFit AMOLED Smartwatch",
    description: "1.43-inch AMOLED smartwatch with Bluetooth calling, heart-rate and SpO2 tracking, 100+ sports modes and up to 7 days of battery life.",
    price_inr: 1999, pack_size: "1 watch with magnetic charger", channel: "E-commerce marketplace",
    competitors: "Entry smartwatches ₹1,299–2,499, mid-range AMOLED watches ₹2,999–4,999",
  },
];

const field = "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";

export default function NewTestForm() {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [image, setImage] = useState<{ base64: string; mime: string; preview: string } | null>(null);
  const [preset, setPreset] = useState<Example | null>(null);
  // ?panel=home from the home page's panel cards preselects that panel.
  const panelParam = useSearchParams().get("panel");
  const fromUrl = PANELS.find((p) => p.id === panelParam)?.id;
  const [panel, setPanel] = useState<PanelId>(fromUrl ?? PANELS[0].id);
  const [panelPicked, setPanelPicked] = useState(Boolean(fromUrl)); // stop auto-suggesting once a panel is chosen

  function applyExample(ex: Example) {
    setPreset(ex);
    setPanel(ex.panel);
    setPanelPicked(false);
    setError(null);
  }

  function onTyping(e: React.FormEvent<HTMLFormElement>) {
    if (panelPicked) return;
    const f = new FormData(e.currentTarget);
    setPanel(suggestPanel(String(f.get("name") ?? ""), String(f.get("description") ?? "")));
  }

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
      panel,
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
    <div hidden={running} className="mb-4 flex flex-wrap items-center gap-2 text-sm">
      <span className="text-slate-600">Try an example:</span>
      {EXAMPLES.map((ex) => (
        <button key={ex.label} type="button" onClick={() => applyExample(ex)}
          className={`rounded-full px-3 py-1 font-medium ring-1 ${preset?.label === ex.label ? "bg-indigo-600 text-white ring-indigo-600" : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50"}`}>
          {ex.label}
        </button>
      ))}
    </div>
    {/* key: remount with the example's values when one is picked. */}
    <form key={preset?.label ?? "blank"} onSubmit={onSubmit} onInput={onTyping} hidden={running}
      className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {error && <ErrorBox message={error} />}

      <label className="block text-sm font-medium text-slate-800">
        Product name
        <input name="name" required maxLength={80} defaultValue={preset?.name} placeholder="e.g. WeaveCharge 65W USB-C Cable" className={field} />
      </label>

      <label className="block text-sm font-medium text-slate-800">
        Description
        <textarea name="description" required maxLength={600} rows={4} defaultValue={preset?.description} className={field}
          placeholder="What is it, who is it for, and what makes it different? e.g. 2 m nylon-braided USB-C cable, 65W fast charging for phones and laptops." />
      </label>

      <div className="grid gap-5 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-800">
          Price (₹)
          <input name="price_inr" type="number" required min={1} max={1000000} step="1" inputMode="numeric" defaultValue={preset?.price_inr} placeholder="799" className={field} />
        </label>
        <label className="block text-sm font-medium text-slate-800">
          Pack size
          <input name="pack_size" required maxLength={60} defaultValue={preset?.pack_size} placeholder="e.g. 1 cable, 2 m" className={field} />
        </label>
      </div>

      <label className="block text-sm font-medium text-slate-800">
        Sales channel
        <select name="channel" required defaultValue={preset?.channel ?? CHANNELS[0]} className={field}>
          {CHANNELS.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>

      <fieldset>
        <legend className="text-sm font-medium text-slate-800">Who should test it?</legend>
        <p className="text-xs text-slate-500">Suggested from your product name. Each panel is built from real reviews in that category.</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {PANELS.map((p) => (
            <label key={p.id}
              className={`cursor-pointer rounded-lg border p-3 text-sm ${panel === p.id ? "border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500" : "border-slate-300 hover:bg-slate-50"}`}>
              <input type="radio" name="panel" value={p.id} checked={panel === p.id} className="sr-only"
                onChange={() => { setPanel(p.id); setPanelPicked(true); }} />
              <span className="block font-medium text-slate-900">{p.shoppers}</span>
              <span className="block text-xs text-slate-500">{p.examples}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="block text-sm font-medium text-slate-800">
        Similar products customers know <span className="font-normal text-slate-500">(optional)</span>
        <input name="competitors" maxLength={200} defaultValue={preset?.competitors} placeholder="e.g. Basic USB-C cables ₹199–399, branded braided cables ₹499–999" className={field} />
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
