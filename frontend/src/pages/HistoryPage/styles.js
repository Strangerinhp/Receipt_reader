import { makeStyles } from "@mui/styles";

export const useStyles = makeStyles({
  content: {
    textAlign: "center",
  },
  table: {
    margin: "auto",
    width: "92%",
    height: "100%",
  },
  loader: {
    position: "fixed",
    inset: 0,
    zIndex: 100,
    display: "grid",
    placeItems: "center",
    pointerEvents: "none",
  },
  invoice: {
    textAlign: "center",
    marginTop: "20px",
    width: "35%",
  },
});
