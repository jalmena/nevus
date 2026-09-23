import { render, screen } from "@testing-library/react";
import i18n from "@/lib/i18n";
import { App } from "@/app/App";

describe("App shell", () => {
  it("shows the wordmark and the intended-use statement in English", async () => {
    await i18n.changeLanguage("en");
    render(<App />);
    expect(screen.getByRole("img", { name: "neVus" })).toBeInTheDocument();
    expect(screen.getByText(/does not diagnose/)).toBeInTheDocument();
  });

  it("switches to Spanish", async () => {
    await i18n.changeLanguage("es");
    render(<App />);
    expect(screen.getByText(/No diagnostica/)).toBeInTheDocument();
  });
});
