// Customer panels. Keep ids in sync with api/app/panels.py.
export const PANELS = [
  { id: "accessories", label: "Electronics accessories", shoppers: "Electronics-accessory shoppers", examples: "cables, chargers, earphones, mice" },
  { id: "home", label: "Home & kitchen appliances", shoppers: "Home & kitchen shoppers", examples: "fans, coolers, heaters, mixers, kettles" },
  { id: "electronics", label: "Consumer electronics", shoppers: "Consumer-electronics shoppers", examples: "smartwatches, TVs, phones, speakers" },
] as const;

export type PanelId = (typeof PANELS)[number]["id"];
export const DEFAULT_PANEL: PanelId = "accessories";

export const panelById = (id?: string | null) => PANELS.find((p) => p.id === id) ?? PANELS[0];

// Checked in order. Accessories come first: "a cable for phones and laptops" is an accessory, not a phone.
const KEYWORDS: [PanelId, RegExp][] = [
  ["accessories", /\b(cable|charger|charging brick|adapter|earbuds?|earphones?|headphones?|headset|tws|neckband|mouse|mice|keyboard|power ?bank|hub|dongle|case|cover|screen (guard|protector)|tempered glass|stand|holder|mount|tripod|selfie stick|pendrive|memory card|sd card|remote)s?\b/i],
  ["home", /\b(fan|air ?cooler|cooler|heater|geyser|kettle|mixer|grinder|blender|juicer|iron|toaster|sandwich|induction|cooktop|purifier|vacuum|ac|air ?conditioner|humidifier|chopper|egg boiler|appliance)s?\b/i],
  ["electronics", /\b(tv|television|smart ?watch|watch|smart ?phone|phone|mobile|speaker|soundbar|projector|camera|tablet|laptop|monitor|fitness band)s?\b/i],
];

const match = (text: string) => KEYWORDS.find(([, re]) => re.test(text))?.[0];

/** Best-guess panel from what the user has typed (the name counts more than the description); always overridable. */
export function suggestPanel(name: string, description = ""): PanelId {
  return match(name) ?? match(description) ?? DEFAULT_PANEL;
}
