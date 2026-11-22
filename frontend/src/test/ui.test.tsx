import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { EmptyState } from "../components/common/EmptyState";
import { LoadingState } from "../components/common/LoadingState";
import { ConfirmationDialog } from "../components/common/ConfirmationDialog";

describe("UI Design Primitives", () => {
  it("renders Button component with variant styles and handles clicks", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click Me</Button>);
    const btn = screen.getByRole("button", { name: /click me/i });
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("renders Card component with title and content", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Workstation Card</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Card body content</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText("Workstation Card")).toBeInTheDocument();
    expect(screen.getByText("Card body content")).toBeInTheDocument();
  });

  it("renders Badge component with correct text", () => {
    render(<Badge variant="success">Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders Progress bar with appropriate aria values", () => {
    render(<Progress value={45} max={100} />);
    const progress = screen.getByRole("progressbar");
    expect(progress).toHaveAttribute("aria-valuenow", "45");
  });

  it("renders EmptyState with icon, title, description, and action button", () => {
    const handleAction = vi.fn();
    render(
      <EmptyState
        title="No Videos"
        description="Please upload your first video."
        actionLabel="Upload Now"
        onAction={handleAction}
      />
    );
    expect(screen.getByText("No Videos")).toBeInTheDocument();
    expect(screen.getByText("Please upload your first video.")).toBeInTheDocument();
    const actionBtn = screen.getByRole("button", { name: /upload now/i });
    fireEvent.click(actionBtn);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  it("renders LoadingState with custom title", () => {
    render(<LoadingState title="Analyzing Video..." />);
    expect(screen.getByText("Analyzing Video...")).toBeInTheDocument();
  });

  it("renders ConfirmationDialog and calls onConfirm when confirmed", () => {
    const handleConfirm = vi.fn();
    render(
      <ConfirmationDialog
        open={true}
        onOpenChange={() => {}}
        title="Confirm Deletion"
        description="Are you sure you want to delete this clip?"
        confirmLabel="Yes, Delete"
        onConfirm={handleConfirm}
      />
    );
    expect(screen.getByText("Confirm Deletion")).toBeInTheDocument();
    expect(screen.getByText("Are you sure you want to delete this clip?")).toBeInTheDocument();
    const confirmBtn = screen.getByRole("button", { name: /yes, delete/i });
    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });
});
