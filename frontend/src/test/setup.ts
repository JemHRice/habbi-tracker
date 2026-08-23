import "@testing-library/jest-dom/vitest";

// jsdom has no matchMedia, and the reduced-motion checks in CSS-adjacent code
// as well as some libraries expect it to exist.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
