import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProductAnalysisForm } from "@/components/product-analysis-form";

describe("ProductAnalysisForm", () => {
  it("requires a product description", async () => {
    render(
      <ProductAnalysisForm
        isSubmitting={false}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(
      await screen.findByText("Description is required."),
    ).toBeInTheDocument();
  });

  it("previews and removes uploaded images", async () => {
    render(
      <ProductAnalysisForm
        isSubmitting={false}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    const file = new File(["image"], "lamp.png", { type: "image/png" });
    await userEvent.upload(screen.getByLabelText(/product images/i), file);
    expect(screen.getByText("lamp.png")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /remove lamp.png/i }),
    );
    expect(screen.queryByText("lamp.png")).not.toBeInTheDocument();
  });
});
