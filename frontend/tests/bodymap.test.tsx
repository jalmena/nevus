import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BodyMap } from "@/features/bodymap/BodyMap";
import { bodyMap, zoneByCode, zonesForView } from "@/features/bodymap/zones";
import i18n from "@/lib/i18n";

describe("body map data", () => {
  it("carries 28 zones per view that tile the same silhouette", () => {
    expect(bodyMap.version).toBe("nevus-body-map/1");
    expect(zonesForView("front")).toHaveLength(28);
    expect(zonesForView("back")).toHaveLength(28);
    expect(bodyMap.views.front.silhouette).toBe(bodyMap.views.back.silhouette);
    expect(zoneByCode("1250")?.side).toBe("right");
    expect(zoneByCode("2250")?.side).toBe("left");
  });
});

describe("<BodyMap>", () => {
  it("offers every zone as a named button and reports the tapped zone with a point inside it", async () => {
    await i18n.changeLanguage("en");
    const onSelectZone = vi.fn();
    const onPlace = vi.fn();
    render(<BodyMap view="front" onSelectZone={onSelectZone} onPlace={onPlace} />);
    expect(screen.getAllByRole("button")).toHaveLength(28);
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
