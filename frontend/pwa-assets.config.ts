import { defineConfig, minimal2023Preset } from "@vite-pwa/assets-generator/config";

// Generates the PWA icon set from Habbi's head. Run with `npm run icons`;
// the outputs are gitignored because they are derived from habbi-mark.svg.
export default defineConfig({
  preset: minimal2023Preset,
  images: ["public/habbi-mark.svg"],
});
