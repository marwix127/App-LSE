import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" para que las rutas funcionen al cargar desde file:// en producción.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  build: { outDir: "dist" },
});
