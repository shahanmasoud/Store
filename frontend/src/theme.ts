import { createTheme } from "@mui/material/styles";

export const appTheme = createTheme({
  direction: "rtl",
  palette: {
    mode: "light",
    primary: {
      main: "#087f5b",
      dark: "#056044",
      light: "#dff7ed",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#ef6c57",
      dark: "#c84b3a",
      light: "#fff0ed",
    },
    warning: { main: "#f4a62a" },
    info: { main: "#2f80ed" },
    background: {
      default: "#f5f8f6",
      paper: "#ffffff",
    },
    text: {
      primary: "#17332b",
      secondary: "#60706b",
    },
    divider: "#dce7e2",
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: 'Vazirmatn, IRANSans, "Segoe UI", Tahoma, sans-serif',
    button: { fontWeight: 800, letterSpacing: 0 },
    h1: { fontWeight: 900, letterSpacing: 0 },
    h2: { fontWeight: 900, letterSpacing: 0 },
    h3: { fontWeight: 900, letterSpacing: 0 },
    h4: { fontWeight: 900, letterSpacing: 0 },
    h5: { fontWeight: 900, letterSpacing: 0 },
    h6: { fontWeight: 900, letterSpacing: 0 },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          minHeight: 44,
          borderRadius: 8,
          textTransform: "none",
          paddingInline: 18,
        },
      },
    },
    MuiIconButton: {
      styleOverrides: { root: { borderRadius: 8 } },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid #dce7e2",
          boxShadow: "0 12px 30px rgba(22, 56, 45, 0.08)",
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { borderRadius: 8, fontWeight: 800 } },
    },
    MuiTextField: {
      defaultProps: { variant: "outlined" },
    },
  },
});
