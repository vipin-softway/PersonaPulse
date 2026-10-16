"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import ProgressPanel from "@/components/ProgressPanel";
import { ErrorBox } from "@/components/ui";
import { createTest, lookupProduct } from "@/lib/api";
import { PANELS, panelById, suggestPanel, type PanelId } from "@/lib/panels";
import type { NewTestInput, ProductLookup } from "@/lib/types";

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

// Map the free-text channel from the web lookup onto the form's options.
function toChannel(text = ""): string {
  const t = text.toLowerCase();
  if (/quick|blinkit|zepto|instamart/.test(t)) return "Quick commerce";
  if (/instagram|social/.test(t)) return "Instagram / social ads";
  if (/d2c|brand('s)? (own )?(web)?site|official (web)?site|direct/.test(t)) return "D2C website";
  if (/croma|reliance digital|vijay sales|electronics (store|retail)|apple store/.test(t)) return "Electronics store";
  if (/local|offline|retail|kirana|shop/.test(t)) return "Local retail store";
  return CHANNELS[0];
}

const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

const field = "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200";

export default function NewTestForm() {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [image, setImage] = useState<{ base64: string; mime: string; preview: string } | null>(null);
  // ?panel=home from the home page's panel cards preselects that panel.
  const params = useSearchParams();
  const fromUrl = PANELS.find((p) => p.id === params.get("panel"))?.id;
  const [panel, setPanel] = useState<PanelId>(fromUrl ?? PANELS[0].id);
  const [panelPicked, setPanelPicked] = useState(Boolean(fromUrl)); // stop auto-suggesting once a panel is chosen
  // "Run this demo live yourself" links here with the demo product in the URL.
  const [formKey, setFormKey] = useState(0); // bumped to remount the form with a new preset
  const nameRef = useRef<HTMLInputElement>(null);
  const [lookup, setLookup] = useState<{ loading: boolean; error?: string; result?: ProductLookup }>({ loading: false });
  const [preset, setPreset] = useState<Example | null>(() =>
    params.get("name")
      ? {
          label: "From demo", panel: (fromUrl ?? PANELS[0].id), name: params.get("name") ?? "",
          description: params.get("description") ?? "", price_inr: Number(params.get("price_inr")) || 0,
          pack_size: params.get("pack_size") ?? "", channel: params.get("channel") ?? "", competitors: params.get("competitors") ?? "",
        }
      : null,
  );
  const [price, setPrice] = useState<number>(preset?.price_inr ?? 0);

  function applyExample(ex: Example) {
    setPreset(ex);
    setPrice(ex.price_inr);
    setPanel(ex.panel);
    setPanelPicked(false);
    setError(null);
    setLookup({ loading: false });
    setFormKey((k) => k + 1);
  }

  async function onLookup() {
    const query = nameRef.current?.value.trim() ?? "";
    if (query.length < 2) return setLookup({ loading: false, error: "Type a product name first, e.g. MacBook Pro M4 or boAt Airdopes 141." });
    setLookup({ loading: true });
    try {
      const r = await lookupProduct(query);
      if (!r.found) return setLookup({ loading: false, result: r });
      const ex: Example = {
        label: "From the web",
        panel: PANELS.find((p) => p.id === r.suggested_panel)?.id ?? suggestPanel(r.product_name ?? query, r.product_description),
        name: r.product_name ?? query, description: r.product_description ?? "", price_inr: Math.round(r.price_inr ?? 0) || 0,
        pack_size: r.pack_size ?? "1 unit", channel: toChannel(r.channel), competitors: r.competitors_text ?? "",
      };
      applyExample(ex);
      setLookup({ loading: false, result: r });
    } catch (err) {
      setLookup({ loading: false, error: err instanceof Error ? err.message : "We couldn't search the web right now. Please fill in the details yourself." });
    }
  }

  function onTyping(e: React.FormEvent<HTMLFormElement>) {
    const f = new FormData(e.currentTarget);
    setPrice(Number(f.get("price_inr")) || 0);
    if (panelPicked) return;
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
    {/* key: remount with the example's (or web lookup's) values when one is picked. */}
    <form key={formKey} onSubmit={onSubmit} onInput={onTyping} hidden={running}
      className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {error && <ErrorBox message={error} />}

      <div>
        <label htmlFor="name" className="block text-sm font-medium text-slate-800">Product name</label>
        <div className="mt-1 flex flex-col gap-2 sm:flex-row">
          <input id="name" name="name" ref={nameRef} required maxLength={80} defaultValue={preset?.name} placeholder="e.g. WeaveCharge 65W USB-C Cable"
            className={field.replace("mt-1 ", "")} />
          <button type="button" onClick={onLookup} disabled={lookup.loading}
            className="shrink-0 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 disabled:cursor-wait disabled:opacity-70">
            {lookup.loading ? "Searching the web…" : "Fill from the web"}
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-500">Testing an existing product? Type its name and Gemini fills in the details with Google Search.</p>
        {lookup.error && <p className="mt-2 text-sm text-rose-700">{lookup.error}</p>}
        {lookup.result && !lookup.result.found && (
          <p className="mt-2 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{lookup.result.notes || "We couldn't identify that product."} Please fill in the details yourself.</p>
        )}
        {lookup.result?.found && (
          <div className="mt-2 rounded-lg bg-indigo-50/60 p-3 text-xs text-slate-700 ring-1 ring-indigo-100">
            <p className="font-medium text-slate-800">Filled from Google Search. Check the details before running the test.</p>
            {lookup.result.notes && <p className="mt-1">{lookup.result.notes}</p>}
            {!!lookup.result.searched?.length && <p className="mt-1 text-slate-500">Searched: {lookup.result.searched.join(" · ")}</p>}
            {!!lookup.result.sources?.length && (
              <p className="mt-1 text-slate-500">Sources:{" "}
                {lookup.result.sources.map((src, i) => (
                  <a key={src.url} href={src.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-indigo-700">
                    {src.title}{i < lookup.result!.sources!.length - 1 ? ", " : ""}
                  </a>
                ))}
              </p>
            )}
          </div>
        )}
      </div>

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
        {price > panelById(panel).price_p90 && (
          <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">
            {inr(price)} is above what most products in this panel cost (typically {inr(panelById(panel).price_p10)}–{inr(panelById(panel).price_p90)}).
            These shoppers will likely find it expensive, so read the results as how this crowd reacts, not as a forecast for premium buyers.
          </p>
        )}
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
