import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.indexOf("node_modules") === -1) return undefined;
          if (id.indexOf("@mui/icons-material") !== -1) return "mui-icons";
          if (id.indexOf("@mui/") !== -1 || id.indexOf("@emotion/") !== -1) return "mui-vendor";
          if (id.indexOf("react") !== -1 || id.indexOf("scheduler") !== -1) return "react-vendor";
          if (id.indexOf("qrcode") !== -1) return "qrcode-vendor";
          return "vendor";
        },
      },
    },
  },
});
