import { makeStyles } from "@mui/styles";
import { COLORS } from "../../styles/constants";

export const useStyles = makeStyles({
  pageWrapper: {
    display: "flex",
    minHeight: "100vh",
    backgroundColor: COLORS.GRAY_DARK,
  },
  contentWrapper: {
    minWidth: 0,
    flex: "1 1 0%",
    backgroundColor: COLORS.GRAY_LIGHT,
  },
  contentWrapperExpanded: {
    marginLeft: "0",
  },
});
