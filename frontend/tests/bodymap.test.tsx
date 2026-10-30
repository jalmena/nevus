import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BodyMap } from "@/features/bodymap/BodyMap";
import { bodyMap, zoneByCode, zonesForView } from "@/features/bodymap/zones";
import i18n from "@/lib/i18n";
import en from "@/lib/i18n/locales/en.json";
import es from "@/lib/i18n/locales/es.json";
import pt from "@/lib/i18n/locales/pt.json";

describe("body map data", () => {
  it("carries the zones of each body view, and the detail views", () => {
    expect(bodyMap.version).toBe("nevus-body-map/4");
    expect(zonesForView("front")).toHaveLength(35);
    expect(zonesForView("back")).toHaveLength(30);
    // One figure, but seen from behind the gaps under the arms climb higher: there is no armpit to unroll there.
    expect(bodyMap.views.back.silhouette).not.toBe(bodyMap.views.front.silhouette);
    expect(zoneByCode("1250")?.side).toBe("right");
    expect(zoneByCode("2250")?.side).toBe("left");
    expect(zonesForView("head").map((zone) => zone.code)).toEqual([
      "3150",
      "3151",
      "3170",
      "3171",
      "3172",
      "3173",
    ]);
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
        !(code in (en.zones as Record<string, string>)) ||
        !(code in (es.zones as Record<string, string>)) ||
        !(code in (pt.zones as Record<string, string>)),
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
    // The head, the hands and the feet are only sketched here: they have views of their own.
    expect(within(map).getAllByRole("button")).toHaveLength(26);
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

  it("draws each part of the person's anatomy on the front, and none when none is set", () => {
    const layers = (anatomy?: ("breasts" | "vulva" | "penis")[]) => {
      const { container, unmount } = render(<BodyMap view="front" anatomy={anatomy} />);
      const paths = Array.from(container.querySelectorAll("path[aria-hidden='true']:not([data-under])")).map(
        (path) => path.getAttribute("d"),
      );
      unmount();
      return paths;
    };
    const none = layers();
    expect(layers(["breasts"])).toHaveLength(none.length + 1);
    expect(layers(["breasts", "penis"])).toHaveLength(none.length + 2);
    expect(layers(["vulva"]).at(-1)).not.toEqual(layers(["penis"]).at(-1));
  });

  it("lays each zone of the anatomy over what is under it", () => {
    const { container } = render(<BodyMap view="front" anatomy={["penis"]} />);
    const under = Array.from(container.querySelectorAll("[data-under]")).map((path) =>
      path.getAttribute("data-under"),
    );
    expect(under).toEqual(["1370", "1371"]);
  });

  it("offers the breasts, penis and scrotum as zones only for a person who has them", () => {
    const zoneCodes = (anatomy?: ("breasts" | "vulva" | "penis")[]) => {
      const { container, unmount } = render(<BodyMap view="front" anatomy={anatomy} />);
      const codes = Array.from(container.querySelectorAll("[data-zone]")).map((zone) =>
        zone.getAttribute("data-zone"),
      );
      unmount();
      return codes;
    };
    expect(zoneCodes()).not.toContain("1260");
    expect(zoneCodes(["breasts"])).toEqual(expect.arrayContaining(["1260", "1261"]));
    expect(zoneCodes(["penis"])).toEqual(expect.arrayContaining(["1370", "1371"]));
    expect(zoneCodes(["vulva"])).not.toContain("1370");
    // Over the zones under them: drawn last, so a tap there lands on the part.
    expect(zoneCodes(["breasts"]).slice(-2)).toEqual(["1260", "1261"]);
  });

  it("opens the hands view from a hand sketched on the front, and places no mark there", async () => {
    await i18n.changeLanguage("en");
    const onOpenView = vi.fn();
    const onPlace = vi.fn();
    render(<BodyMap view="front" onPlace={onPlace} onOpenView={onOpenView} />);
    const hands = screen.getAllByRole("button", { name: "Hands" });
    expect(hands).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "Feet" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Head" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(hands[0] as HTMLElement);
    expect(onOpenView).toHaveBeenCalledWith("hands");
    expect(onPlace).not.toHaveBeenCalled();
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
