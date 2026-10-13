import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Menu } from "@/design-system/components/Menu";

describe("<Menu>", () => {
  it("opens from one button, walks with the arrows, chooses with Enter and closes with Escape", async () => {
    const edit = vi.fn();
    const remove = vi.fn();
    render(
      <Menu
        label="More"
        items={[
          { label: "Edit details", onSelect: edit },
          { label: "Move to the trash", onSelect: remove, danger: true },
        ]}
      />,
    );
    const user = userEvent.setup();
    const trigger = screen.getByRole("button", { name: "More" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menuitem", { name: "Edit details" })).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Move to the trash" })).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("menuitem", { name: "Edit details" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    await user.click(trigger);
    await user.click(screen.getByRole("menuitem", { name: "Move to the trash" }));
    expect(remove).toHaveBeenCalledTimes(1);
    expect(edit).not.toHaveBeenCalled();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes when the pointer goes elsewhere", async () => {
    render(
      <div>
        <p>Elsewhere</p>
        <Menu label="More" items={[{ label: "One", onSelect: () => undefined }]} />
      </div>,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByRole("menu")).toBeInTheDocument();
    await user.click(screen.getByText("Elsewhere"));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
