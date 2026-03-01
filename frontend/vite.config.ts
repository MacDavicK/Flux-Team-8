import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

// Dev-only Babel plugin: injects data-component="ComponentName" onto the root JSX element
// of every React component so component boundaries are visible in the browser DevTools.
function babelPluginDataComponent(): object {
  return {
    name: "data-component",
    visitor: {
      "FunctionDeclaration|ArrowFunctionExpression|FunctionExpression"(
        // biome-ignore lint/suspicious/noExplicitAny: vite plugin typing
        path: any,
      ) {
        const componentName: string | null =
          path.node.id?.name ??
          path.parentPath?.node?.id?.name ??
          path.parentPath?.node?.key?.name ??
          null;

        if (!componentName || !/^[A-Z]/.test(componentName)) return;

        path.traverse({
          // biome-ignore lint/suspicious/noExplicitAny: Babel node types
          ReturnStatement(returnPath: any) {
            const arg = returnPath.node.argument;
            if (!arg || arg.type !== "JSXElement") return;

            const openingEl = arg.openingElement;
            const alreadyHasAttr = openingEl.attributes.some(
              // biome-ignore lint/suspicious/noExplicitAny: Babel node types
              (attr: any) =>
                attr.type === "JSXAttribute" &&
                attr.name?.name === "data-component",
            );

            if (!alreadyHasAttr) {
              openingEl.attributes.unshift({
                type: "JSXAttribute",
                name: { type: "JSXIdentifier", name: "data-component" },
                value: { type: "StringLiteral", value: componentName },
              });
            }
          },
        });
      },
    },
  };
}

export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      // Forward all /api/* requests to the FastAPI backend.
      "/api": {
        target: process.env.VITE_API_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [
    tsConfigPaths(),
    tailwindcss(),
    tanstackStart(),
    // React's Vite plugin must come after Start's plugin
    viteReact(
      process.env.NODE_ENV !== "production"
        ? { babel: { plugins: [babelPluginDataComponent] } }
        : {},
    ),
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
