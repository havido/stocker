import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourcesList } from "@/components/SourcesList";

const sources = [
  { source: "reddit", title: "Reddit post about AAPL", url: "https://reddit.com/r/stocks/1" },
  { source: "yahoo", title: "Yahoo Finance article", url: "https://finance.yahoo.com/news/2" },
];

describe("SourcesList", () => {
  it("renders one external link per source", () => {
    render(<SourcesList sources={sources} />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute("href", "https://reddit.com/r/stocks/1");
    expect(links[0]).toHaveAttribute("target", "_blank");
    expect(links[0]).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows each source's title and provider badge", () => {
    render(<SourcesList sources={sources} />);
    expect(screen.getByText("Reddit post about AAPL")).toBeInTheDocument();
    expect(screen.getByText("Yahoo Finance article")).toBeInTheDocument();
    expect(screen.getByText("reddit")).toBeInTheDocument();
    expect(screen.getByText("yahoo")).toBeInTheDocument();
  });

  it("shows the source count", () => {
    render(<SourcesList sources={sources} />);
    expect(screen.getByText(/2 sources used for this grade/i)).toBeInTheDocument();
  });

  it("falls back to the url when the title is empty", () => {
    render(<SourcesList sources={[{ source: "reddit", title: "", url: "https://x/1" }]} />);
    expect(screen.getByText("https://x/1")).toBeInTheDocument();
    expect(screen.getByText(/1 source used/i)).toBeInTheDocument();
  });

  it("renders nothing when there are no sources", () => {
    const { container } = render(<SourcesList sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
