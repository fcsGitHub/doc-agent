import React, { useState, useMemo, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { IssuePopover, ExtendedReviewIssue } from "./issue-popover";

interface AnnotationOverlayProps {
  content: string;
  issues: ExtendedReviewIssue[];
  visible: boolean;
}

export function AnnotationOverlay({ content, issues, visible }: AnnotationOverlayProps) {
  const [currentIssueIndex, setCurrentIssueIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter issues that actually have an excerpt to match
  const matchableIssues = useMemo(() => {
    return issues.filter(issue => !!issue.location_excerpt);
  }, [issues]);

  // Pre-process content to inject markdown links for issues
  const annotatedContent = useMemo(() => {
    if (!visible || !content || matchableIssues.length === 0) return content;
    
    let processed = content;
    // We iterate backwards or just replace all to avoid overlapping issues messing up indices
    // For simplicity, just replace literal strings
    matchableIssues.forEach((issue, index) => {
      if (issue.location_excerpt && processed.includes(issue.location_excerpt)) {
        // Use a unique marker prefix to ensure it does not conflict with existing markdown links
        processed = processed.replace(
          issue.location_excerpt,
          `[${issue.location_excerpt}](#issue-${index})`
        );
      }
    });
    
    return processed;
  }, [content, matchableIssues, visible]);

  // Close popover when clicking outside
  useEffect(() => {
    if (currentIssueIndex === null) return;
    
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setCurrentIssueIndex(null);
      }
    };
    
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [currentIssueIndex]);

  // Standard markdown components from section-content
  const components = useMemo(() => ({
    h1: ({ node, ...props }: any) => <h1 className="text-2xl font-bold mt-6 mb-4" {...props} />,
    h2: ({ node, ...props }: any) => <h2 className="text-xl font-bold mt-5 mb-3" {...props} />,
    h3: ({ node, ...props }: any) => <h3 className="text-lg font-bold mt-4 mb-2" {...props} />,
    p: ({ node, ...props }: any) => <p className="mb-4 leading-relaxed" {...props} />,
    ul: ({ node, ...props }: any) => <ul className="list-disc pl-5 mb-4 space-y-1" {...props} />,
    ol: ({ node, ...props }: any) => <ol className="list-decimal pl-5 mb-4 space-y-1" {...props} />,
    li: ({ node, ...props }: any) => <li {...props} />,
    strong: ({ node, ...props }: any) => <strong className="font-semibold" {...props} />,
    em: ({ node, ...props }: any) => <em className="italic" {...props} />,
    blockquote: ({ node, ...props }: any) => (
      <blockquote className="border-l-4 border-gray-200 pl-4 italic text-gray-600 mb-4" {...props} />
    ),
    // Custom link component to render the highlighted spans
    a: ({ node, href, children, ...props }: any) => {
      if (visible && href?.startsWith("#issue-")) {
        const indexStr = href.replace("#issue-", "");
        const index = parseInt(indexStr, 10);
        const issue = matchableIssues[index];
        
        if (issue) {
          let highlightClass = "";
          switch (issue.severity) {
            case "critical": highlightClass = "text-red-600 underline decoration-red-600 decoration-2 cursor-pointer bg-red-50"; break;
            case "major": highlightClass = "text-orange-500 underline decoration-orange-500 decoration-2 cursor-pointer bg-orange-50"; break;
            case "minor": highlightClass = "text-yellow-500 underline decoration-yellow-500 decoration-2 cursor-pointer bg-yellow-50"; break;
            case "info": highlightClass = "text-blue-500 underline decoration-blue-500 decoration-2 cursor-pointer bg-blue-50"; break;
            default: highlightClass = "text-gray-600 underline decoration-gray-500 decoration-2 cursor-pointer bg-gray-50"; break;
          }
          
          return (
            <span 
              className={highlightClass}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setCurrentIssueIndex(index);
              }}
              data-testid={`issue-highlight-${index}`}
            >
              {children}
            </span>
          );
        }
      }
      // Fallback for normal links
      return <a href={href} className="text-blue-600 hover:underline" {...props}>{children}</a>;
    }
  }), [visible, matchableIssues]);

  const handlePrev = () => {
    if (currentIssueIndex !== null && currentIssueIndex > 0) {
      setCurrentIssueIndex(currentIssueIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentIssueIndex !== null && currentIssueIndex < matchableIssues.length - 1) {
      setCurrentIssueIndex(currentIssueIndex + 1);
    }
  };

  const activeIssue = currentIssueIndex !== null ? matchableIssues[currentIssueIndex] : null;

  return (
    <div className="relative text-gray-800 space-y-4" ref={containerRef}>
      <ReactMarkdown components={components}>
        {annotatedContent}
      </ReactMarkdown>
      
      {activeIssue && (
        <IssuePopover 
          issue={activeIssue}
          onClose={() => setCurrentIssueIndex(null)}
          onPrev={handlePrev}
          onNext={handleNext}
          hasPrev={currentIssueIndex !== null && currentIssueIndex > 0}
          hasNext={currentIssueIndex !== null && currentIssueIndex < matchableIssues.length - 1}
        />
      )}
    </div>
  );
}

