import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Chip } from "@/design-system/components/Chip";
import { AppBar } from "@/app/Shell";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Sheet } from "@/design-system/components/Sheet";
import i18n from "@/lib/i18n";

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

describe("<PageHeader>", () => {
  it("names the way back after the parent and keeps the title first", () => {
    render(
      <MemoryRouter>
        <AppBar desktop={false} />
        <PageHeader
          back={{ to: "/persons/1", label: "Ana" }}
          title="Chest mark"
          meta={["Right pectoral", "Front"]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Back to Ana" })).toHaveAttribute("href", "/persons/1");
    expect(screen.getByRole("heading", { level: 1, name: "Chest mark" })).toBeInTheDocument();
    expect(screen.getByText("Right pectoral · Front")).toBeInTheDocument();
  });
});

describe("<Sheet>", () => {
  it("opens as a dialog with its title and closes from its button", async () => {
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.removeAttribute("open");
      this.dispatchEvent(new Event("close"));
    });
    const onClose = vi.fn();
    const { rerender } = render(
      <Sheet open={false} title="Reports" onClose={onClose}>
        <p>Body</p>
      </Sheet>,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    rerender(
      <Sheet open title="Reports" onClose={onClose}>
        <p>Body</p>
      </Sheet>,
    );
    expect(screen.getByRole("dialog", { name: "Reports" })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("<Chip>", () => {
  it("is a button that can say it is pressed", () => {
    render(<Chip pressed>Reports</Chip>);
    expect(screen.getByRole("button", { name: "Reports" })).toHaveAttribute("aria-pressed", "true");
  });
});
