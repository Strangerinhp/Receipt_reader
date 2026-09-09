import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import MenuIcon from "@mui/icons-material/Menu";
import StorageIcon from "@mui/icons-material/Storage";
import { Chip, IconButton, Typography } from "@mui/material";
import { useStyles } from "./styles";
import { COLORS } from "../../styles/constants";
import httpRequest from "../../httpRequest";

const Navbar = (props) => {
  const classes = useStyles();
  const location = useLocation();
  const [databaseEngine, setDatabaseEngine] = useState("Database");

  useEffect(() => {
    httpRequest.get("/health")
      .then((response) => setDatabaseEngine(response.data.database_engine || "Database"))
      .catch(() => setDatabaseEngine("Database unavailable"));
  }, []);

  const getPageTitle = () => {
    switch (location.pathname) {
      case "/":
        return "Đọc & quản lý hóa đơn";
      case "/history":
        return "Kho hóa đơn";
      default:
        return "";
    }
  };

  return (
    <div className={classes.rootContainer}>
      <div className={classes.headingContainer}>
        {!props.sideMenuVisible && (
          <IconButton onClick={props.toggleSideMenu}>
            <MenuIcon
              sx={{
                color: "white",
                "&:hover": {
                  color: COLORS.PRIMARY,
                },
                marginTop: "-4px",
              }}
            />
          </IconButton>
        )}
        <Typography
          variant="h5"
          sx={{
            ml: 4,
            fontSize: { xs: "20px", sm: "24px", md: "26px" },
          }}
        >
          {getPageTitle()}
        </Typography>
      </div>
      <div className={classes.rightButtons}>
        <Chip icon={<StorageIcon />} label={databaseEngine} sx={{ color: "white", bgcolor: "#6336ab" }} />
      </div>
    </div>
  );
};

export default Navbar;
