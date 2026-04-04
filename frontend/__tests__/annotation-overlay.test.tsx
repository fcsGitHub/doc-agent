import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AnnotationOverlay } from "@/components/workbench/annotation-overlay";
import { ExtendedReviewIssue } from "@/components/workbench/issue-popover";

describe("AnnotationOverlay Component", () => {
  const mockIssues: ExtendedReviewIssue[] = [
    {
      id: "1",
      severity: "critical",
      category: "Accuracy",
      description: "This is a critical issue.",
      location_excerpt: "critical text",
      requires_human: true,
      reviewer_name: "Agent A"
    },
    {
      id: "2",
      severity: "minor",
      category: "Style",
      description: "This is a minor issue.",
      location_excerpt: "minor text",
      requires_human: false,
    }
  ];

  it("should render normal markdown when visible is false", () => {
    const content = "This has critical text and minor text.";
    render(
      <AnnotationOverlay content={content} issues={mockIssues} visible={false} />
    );

    // It should render text normally without highlights
    expect(screen.getByText("This has critical text and minor text.")).toBeInTheDocument();
    expect(screen.queryByTestId(/issue-highlight/)).not.toBeInTheDocument();
  });

  it("should wrap location_excerpt with highlights when visible is true", () => {
    const content = "This has critical text and minor text.";
    render(
      <AnnotationOverlay content={content} issues={mockIssues} visible={true} />
    );

    // The text should be split and highlighted
    const criticalHighlight = screen.getByTestId("issue-highlight-0");
    expect(criticalHighlight).toBeInTheDocument();
    expect(criticalHighlight).toHaveTextContent("critical text");
    expect(criticalHighlight).toHaveClass("text-red-600");

    const minorHighlight = screen.getByTestId("issue-highlight-1");
    expect(minorHighlight).toBeInTheDocument();
    expect(minorHighlight).toHaveTextContent("minor text");
    expect(minorHighlight).toHaveClass("text-yellow-500");
  });

  it("should show popover when a highlight is clicked", () => {
    const content = "This has critical text and minor text.";
    render(
      <AnnotationOverlay content={content} issues={mockIssues} visible={true} />
    );

    const criticalHighlight = screen.getByTestId("issue-highlight-0");
    fireEvent.click(criticalHighlight);

    // Popover should appear with issue details
    const popover = screen.getByTestId("issue-popover");
    expect(popover).toBeInTheDocument();
    expect(screen.getByText("This is a critical issue.")).toBeInTheDocument();
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
    expect(screen.getByText("致命")).toBeInTheDocument();
    expect(screen.getByText("审核人: Agent A")).toBeInTheDocument();
  });

  it("should close popover when close button is clicked", () => {
    const content = "This has critical text and minor text.";
    render(
      <AnnotationOverlay content={content} issues={mockIssues} visible={true} />
    );

    const minorHighlight = screen.getByTestId("issue-highlight-1");
    fireEvent.click(minorHighlight);

    expect(screen.getByTestId("issue-popover")).toBeInTheDocument();

    const closeBtn = screen.getByTestId("close-popover");
    fireEvent.click(closeBtn);

    expect(screen.queryByTestId("issue-popover")).not.toBeInTheDocument();
  });

  it("should navigate between issues using next/prev buttons", () => {
    const content = "This has critical text and minor text.";
    render(
      <AnnotationOverlay content={content} issues={mockIssues} visible={true} />
    );

    const criticalHighlight = screen.getByTestId("issue-highlight-0");
    fireEvent.click(criticalHighlight);

    // Should be on the first issue
    expect(screen.getByText("This is a critical issue.")).toBeInTheDocument();

    // Click next
    const nextBtn = screen.getByText("下一个问题");
    fireEvent.click(nextBtn);

    // Should be on the second issue
    expect(screen.getByText("This is a minor issue.")).toBeInTheDocument();

    // Click prev
    const prevBtn = screen.getByText("上一个问题");
    fireEvent.click(prevBtn);

    // Should be back on the first issue
    expect(screen.getByText("This is a critical issue.")).toBeInTheDocument();
  });
});

