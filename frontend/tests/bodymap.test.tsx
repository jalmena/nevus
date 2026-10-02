import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BodyMap } from "@/features/bodymap/BodyMap";
import { bodyMap, zoneByCode, zonesForView } from "@/features/bodymap/zones";
import i18n from "@/lib/i18n";
import en from "@/lib/i18n/locales/en.json";
import es from "@/lib/i18n/locales/es.json";

describe("body map data", () => {
  it("carries 28 zones per body view that tile the same silhouette, and the detail views", () => {
    expect(bodyMap.version).toBe("nevus-body-map/3");
    expect(zonesForView("front")).toHaveLength(28);
    expect(zonesForView("back")).toHaveLength(28);
    expect(bodyMap.views.front.silhouette).toBe(bodyMap.views.back.silhouette);
    expect(zoneByCode("1250")?.side).toBe("right");
    expect(zoneByCode("2250")?.side).toBe("left");
    expect(zonesForView("head").map((zone) => zone.code)).toEqual(["3150", "3151", "3170", "3171", "3172"]);
    expect(zoneByCode("3150")?.side).toBe("left");
    expect(zonesForView("hands")).toHaveLength(4);
    expect(zonesForView("feet").map((zone) => zone.side)).toEqual(["right", "left", "right", "left"]);
  });
});

describe("zone names", () => {
  it("exist in both catalogues for every zone of every view, so lists need no map geometry", () => {
    const codes = Object.keys(bodyMap.views).flatMap((view) =>
      zonesForView(view as never).map((zone) => zone.code),
    );
    expect(codes.length).toBeGreaterThan(60);
    const missing = codes.filter(
      (code) =>
        !(code in (en.zones as Record<string, string>)) || !(code in (es.zones as Record<string, string>)),
    );
    expect(missing).toEqual([]);
  });
});

describe("<BodyMap>", () => {
  it("offers every zone as a named button and reports the tapped zone with a point inside it", async () => {
    await i18n.changeLanguage("en");
    const onSelectZone = vi.fn();
    const onPlace = vi.fn();
    render(<BodyMap view="front" onSelectZone={onSelectZone} onPlace={onPlace} />);
    const map = screen.getByRole("group");
    expect(within(map).getAllByRole("button")).toHaveLength(28);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Right pectoral" }));
    expect(onSelectZone).toHaveBeenCalledWith(expect.objectContaining({ code: "1250" }));
    const point = onPlace.mock.calls[0]?.[0] as { zone: string; x: number; y: number };
    expect(point.zone).toBe("1250");
    const zone = zoneByCode("1250");
    if (!zone) throw new Error("zone 1250 missing");
    const [left, top, right, bottom] = zone.bbox;
    expect(point.x * 216).toBeGreaterThanOrEqual(left);
    expect(point.x * 216).toBeLessThanOrEqual(right);
    expect(point.y * 404).toBeGreaterThanOrEqual(top);
    expect(point.y * 404).toBeLessThanOrEqual(bottom);
  });

  it("reports a tap on the selected zone or on the background as no selection", async () => {
    await i18n.changeLanguage("en");
    const onSelectZone = vi.fn();
    render(<BodyMap view="front" selectedZone="1250" onSelectZone={onSelectZone} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Right pectoral" }));
    expect(onSelectZone).toHaveBeenLastCalledWith(null);
    await user.click(screen.getByRole("button", { name: "Left pectoral" }));
    expect(onSelectZone).toHaveBeenLastCalledWith(expect.objectContaining({ code: "1251" }));
    await user.click(screen.getByRole("group"));
    expect(onSelectZone).toHaveBeenLastCalledWith(null);
  });

  it("while a mark is placed, the first tap zooms in on the zone and the second places the mark", async () => {
    await i18n.changeLanguage("en");
    const onPlace = vi.fn();
    const onSelectZone = vi.fn();
    render(<BodyMap view="front" placing onSelectZone={onSelectZone} onPlace={onPlace} />);
    const map = screen.getByRole("group");
    const before = map.getAttribute("viewBox");
    const user = userEvent.setup();
    const zone = screen.getByRole("button", { name: "Right pectoral" });
    await user.click(zone);
    expect(onSelectZone).toHaveBeenCalledTimes(1);
    expect(onPlace).not.toHaveBeenCalled();
    expect(map.getAttribute("viewBox")).not.toBe(before);
    expect(screen.getByRole("button", { name: "Show the whole body" })).toBeInTheDocument();
    await user.click(zone);
    expect(onPlace).toHaveBeenCalledTimes(1);
    expect((onPlace.mock.calls[0]?.[0] as { zone: string }).zone).toBe("1250");
    await user.click(screen.getByRole("button", { name: "Show the whole body" }));
    expect(map.getAttribute("viewBox")).toBe(before);
  });

  it("names zones in the account language and marks the selected one", async () => {
    await i18n.changeLanguage("es");
    render(<BodyMap view="back" selectedZone="2350" />);
    expect(screen.getByRole("button", { name: "Glúteo izquierdo" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Hombro derecho" })).toHaveAttribute("aria-pressed", "false");
  });

  it("renders markers at normalised positions and lets them be chosen", async () => {
    await i18n.changeLanguage("en");
    const onSelectMarker = vi.fn();
    render(
      <BodyMap
        view="front"
        markers={[{ id: "m1", x: 0.5, y: 0.25, label: "Chest mark" }]}
        onSelectMarker={onSelectMarker}
      />,
    );
    const marker = screen.getByRole("button", { name: "Chest mark" });
    expect(marker).toHaveAttribute("transform", "translate(108 101)");
    await userEvent.setup().click(marker);
    expect(onSelectMarker).toHaveBeenCalledWith("m1");
  });
});

describe("<BodyMap> zoom and clusters", () => {
  it("groups markers that would overlap and zooms in when the group is chosen", async () => {
    await i18n.changeLanguage("en");
    render(
      <BodyMap
        view="front"
        markers={[
          { id: "a", x: 0.5, y: 0.3, label: "First" },
          { id: "b", x: 0.505, y: 0.302, label: "Second" },
          { id: "c", x: 0.2, y: 0.8, label: "Far" },
        ]}
        onSelectMarker={() => undefined}
      />,
    );
    const group = screen.getByRole("button", { name: "2 marks here: zoom in" });
    expect(screen.getByRole("button", { name: "Far" })).toBeInTheDocument();
    const map = screen.getByRole("group");
    const before = map.getAttribute("viewBox");
    await userEvent.setup().click(group);
    expect(map.getAttribute("viewBox")).not.toBe(before);
    expect(screen.getByRole("button", { name: "Show the whole body" })).toBeInTheDocument();
  });
});
