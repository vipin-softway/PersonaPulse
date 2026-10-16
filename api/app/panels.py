"""Customer panels: separate AI-customer crowds, each built from one slice of the review data.

A product is tested on one panel, so a fan is judged by home-appliance
shoppers and a cable by accessory shoppers. Keep ids in sync with web/lib/panels.ts.
"""

from __future__ import annotations

PANELS: dict[str, dict] = {
    "accessories": {
        "label": "Electronics accessories",
        "shoppers": "Electronics-accessory shoppers",
        "category": "electronics accessories",  # {{category}} in Prompts 1-3 and 8
        "examples": "cables, chargers, earphones, mice, power banks",
        "price_p10": 169, "price_p90": 1565,  # middle 80% of training-product prices (reviews_raw)
    },
    "home": {
        "label": "Home & kitchen appliances",
        "shoppers": "Home & kitchen shoppers",
        "category": "home and kitchen appliances",
        "examples": "fans, heaters, water heaters, mixers, kettles, irons, purifiers",
        "price_p10": 279, "price_p90": 5999,
    },
    "electronics": {
        "label": "Consumer electronics",
        "shoppers": "Consumer-electronics shoppers",
        "category": "consumer electronics",
        "examples": "smartwatches, smartphones, TVs, speakers",
        "price_p10": 1049, "price_p90": 28999,
    },
}
DEFAULT_PANEL = "accessories"

# Devices, as opposed to the accessories around them (Amazon category leaves / level-2 names).
_DEVICE_LEAVES = {
    "Smartphones", "BasicMobiles", "SmartTelevisions", "StandardTelevisions", "SmartWatches", "FitnessTrackers",
    "BluetoothSpeakers", "OutdoorSpeakers", "Projectors", "DomeCameras", "BulletCameras", "SatelliteReceivers",
    "Soundbars", "StreamingClients", "Laptops", "Tablets", "Monitors",
}
_DEVICE_L2 = {"WearableTechnology", "HomeAudio", "Monitors", "Laptops", "Tablets"}


def assign(category_path: str) -> str | None:
    """Map an Amazon category path ("A|B|...|Leaf") to a panel id, or None if out of scope."""
    levels = str(category_path).split("|")
    l1, l2, leaf = levels[0], (levels[1] if len(levels) > 1 else ""), levels[-1]
    if l1 == "Home&Kitchen":
        return "home"
    if leaf in _DEVICE_LEAVES or l2 in _DEVICE_L2:
        return "electronics"
    if l1 in ("Electronics", "Computers&Accessories"):
        return "accessories"
    return None
