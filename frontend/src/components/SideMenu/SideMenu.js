import { Divider } from "@mui/material";

import DashboardIcon from "@mui/icons-material/Dashboard";
import HistoryIcon from "@mui/icons-material/History";
import IconButton from "@mui/material/IconButton";
import ArrowBackIosIcon from "@mui/icons-material/ArrowBackIos";
import { useMediaQuery } from "@mui/material";

import { useStyles } from "./styles";
import LinkItem from "./LinkItem/LinkItem";
import OCR_LOGO from "../../images/OCR-logo.png";
import { Link } from 'react-router-dom';
import { COLORS } from "../../styles/constants";

const SideMenu = (props) => {
  const classes = useStyles();
  const isSmallScreen = useMediaQuery("(max-width:540px)");
  const isExtraSmallScreen = useMediaQuery("(max-width:470px)");

  return (
    <div
      className={`${classes.rootContainer} ${
        props.visible ? "" : classes.rootContainerCollapsed
      }`}
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      {props.visible && (
        <>
          <div>
            <div className={classes.closeContainer}>
              <IconButton onClick={props.onClose} className={classes.closeButton}>
                <ArrowBackIosIcon
                  sx={{
                    color: "white",
                    "&:hover": {
                      color: COLORS.PRIMARY,
                    },
                  }}
                />
              </IconButton>
            </div>
            <Link to="/">
              <img
                src={OCR_LOGO}
                alt="logo"
                className={classes.logo}
                width={isSmallScreen ? "40px" : "60px"}
                style={{
                  marginTop: isExtraSmallScreen ? "5px" : "-16px",
                  marginBottom: "24px",
                }}
              />
            </Link>
            <Divider />
            <div className={classes.linkContainer}>
              <LinkItem to="/" Icon={DashboardIcon} text="Đọc hóa đơn" />
              <LinkItem to="/history" Icon={HistoryIcon} text="Kho hóa đơn" />
            </div>
          </div>
          <div className={classes.footerContainer}>Invoice OCR · SQL Server</div>
        </>
      )}
    </div>
  );
};

export default SideMenu;
