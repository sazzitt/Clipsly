import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Input,
  Kbd,
  Label,
  Progress,
  Select,
  Slider,
  StatusIndicator,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
} from "../components/ui";

describe("Design System & UI Components", () => {
  describe("Button Component", () => {
    it("renders loading state with spinner and disables button", () => {
      const handleClick = vi.fn();
      render(
        <Button loading onClick={handleClick}>
          Submit Video
        </Button>
      );
      const btn = screen.getByRole("button", { name: /submit video/i });
      expect(btn).toBeDisabled();
      expect(btn).toHaveAttribute("aria-busy", "true");
      expect(screen.getByTestId("button-spinner")).toBeInTheDocument();
      fireEvent.click(btn);
      expect(handleClick).not.toHaveBeenCalled();
    });

    it("renders disabled button without firing click handlers", () => {
      const handleClick = vi.fn();
      render(
        <Button disabled onClick={handleClick}>
          Disabled Action
        </Button>
      );
      const btn = screen.getByRole("button", { name: /disabled action/i });
      expect(btn).toBeDisabled();
      fireEvent.click(btn);
      expect(handleClick).not.toHaveBeenCalled();
    });

    it("renders destructive variant correctly", () => {
      render(<Button variant="destructive">Delete Video</Button>);
      const btn = screen.getByRole("button", { name: /delete video/i });
      expect(btn).toHaveClass("bg-destructive");
    });
  });

  describe("Card Variants", () => {
    it("renders interactive card with hover styling", () => {
      render(
        <Card variant="interactive" data-testid="interactive-card">
          Interactive Card Content
        </Card>
      );
      const card = screen.getByTestId("interactive-card");
      expect(card).toHaveClass("cursor-pointer");
    });

    it("renders metric card", () => {
      render(
        <Card variant="metric" data-testid="metric-card">
          Metric Card Content
        </Card>
      );
      const card = screen.getByTestId("metric-card");
      expect(card).toBeInTheDocument();
    });
  });

  describe("Badge Variants", () => {
    it("renders disabled feature badge", () => {
      render(<Badge variant="disabled">Upcoming</Badge>);
      expect(screen.getByText("Upcoming")).toHaveClass("cursor-not-allowed");
    });

    it("renders warning and info badges", () => {
      render(
        <>
          <Badge variant="warning">Warning Tag</Badge>
          <Badge variant="info">Info Tag</Badge>
        </>
      );
      expect(screen.getByText("Warning Tag")).toBeInTheDocument();
      expect(screen.getByText("Info Tag")).toBeInTheDocument();
    });
  });

  describe("Input, Label & Textarea", () => {
    it("renders invalid input with aria-invalid and error border", () => {
      render(<Input error placeholder="Enter title" />);
      const input = screen.getByPlaceholderText("Enter title");
      expect(input).toHaveAttribute("aria-invalid", "true");
      expect(input).toHaveClass("border-destructive");
    });

    it("renders Label with required indicator", () => {
      render(<Label required htmlFor="test-id">Required Field</Label>);
      expect(screen.getByText("Required Field")).toBeInTheDocument();
      expect(screen.getByText("*")).toBeInTheDocument();
    });

    it("renders Textarea component", () => {
      render(<Textarea placeholder="Subtitle text..." defaultValue="Sample line" />);
      const textarea = screen.getByPlaceholderText("Subtitle text...");
      expect(textarea).toHaveValue("Sample line");
    });
  });

  describe("Form Controls (Select, Checkbox, Switch, Slider)", () => {
    it("renders Select dropdown with options", () => {
      const handleChange = vi.fn();
      render(
        <Select onChange={handleChange} defaultValue="small">
          <option value="tiny">Tiny</option>
          <option value="small">Small</option>
        </Select>
      );
      const select = screen.getByRole("combobox");
      expect(select).toHaveValue("small");
      fireEvent.change(select, { target: { value: "tiny" } });
      expect(handleChange).toHaveBeenCalled();
    });

    it("toggles Checkbox on change", () => {
      const handleChecked = vi.fn();
      render(<Checkbox label="Enable NVENC" onCheckedChange={handleChecked} />);
      const label = screen.getByText("Enable NVENC");
      fireEvent.click(label);
      expect(handleChecked).toHaveBeenCalledWith(true);
    });

    it("toggles Switch component", () => {
      const handleToggle = vi.fn();
      render(<Switch label="Auto Framing" checked={false} onCheckedChange={handleToggle} />);
      const switchBtn = screen.getByRole("switch");
      fireEvent.click(switchBtn);
      expect(handleToggle).toHaveBeenCalledWith(true);
    });

    it("renders Slider with label and value", () => {
      render(<Slider label="Volume" value={75} showValue valueSuffix="%" onChange={() => {}} />);
      expect(screen.getByText("Volume")).toBeInTheDocument();
      expect(screen.getByText("75%")).toBeInTheDocument();
    });
  });

  describe("Progress, Kbd & StatusIndicator", () => {
    it("renders indeterminate progress bar with aria-busy", () => {
      render(<Progress indeterminate />);
      const progress = screen.getByRole("progressbar");
      expect(progress).toHaveAttribute("aria-busy", "true");
    });

    it("renders Kbd keyboard shortcut badge", () => {
      render(<Kbd>Ctrl + K</Kbd>);
      expect(screen.getByText("Ctrl + K")).toBeInTheDocument();
    });

    it("renders StatusIndicator with label and healthy status", () => {
      render(<StatusIndicator status="healthy" label="System Ready" pulse />);
      expect(screen.getByText("System Ready")).toBeInTheDocument();
    });
  });

  describe("Table Primitive", () => {
    it("renders semantic table structure", () => {
      render(
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Resolution</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>1080x1920</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      expect(screen.getByText("Resolution")).toBeInTheDocument();
      expect(screen.getByText("1080x1920")).toBeInTheDocument();
    });
  });
});
