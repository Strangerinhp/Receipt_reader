import { makeStyles } from "@mui/styles";

export const useStyles = makeStyles({
  rootContainer: { margin: "0 auto", padding: "16px 22px 28px", textAlign: "left" },
  bar: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 14, flexWrap: "wrap" },
  editorContainer: { height: "calc(100vh - 190px)", minHeight: 620, overflowY: "auto", paddingRight: 5 },
});
