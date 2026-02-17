import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  server: {
    port: 3000,
  },
  plugins: [
    tsConfigPaths(),
    tailwindcss(),
    tanstackStart(),
    // React's Vite plugin must come after Start's plugin
    viteReact(),
  ],
  build: {
    rollupOptions: {
      onwarn(warning, warn) {
        // TODO - remove this when tanstack start fixes this
        // Suppress unused import warnings from @tanstack packages in node_modules
        if (
          warning.code === "UNUSED_EXTERNAL_IMPORT" &&
          warning.names?.some((name) =>
            [
              "createRequestHandler",
              "defineHandlerCallback",
              "transformPipeableStreamWithRouter",
              "transformReadableStreamWithRouter",
              "RawStream",
              "hydrate",
              "json",
            ].includes(name),
          ) &&
          warning.id?.includes("node_modules/@tanstack")
        ) {
          return;
        }
        warn(warning);
      },
    },
  },
});
