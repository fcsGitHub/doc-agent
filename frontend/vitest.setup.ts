import "@testing-library/jest-dom";

if (typeof window !== "undefined" && !(window as any).EventSource) {
  (window as any).EventSource = class EventSource {
    constructor() {}
    close() {}
  };
}
