import { useContext } from "react";
import { Paper, Typography } from "@mui/material";
import OCRContext from "../../context/ocr-context";
import AppLayout from "../../components/AppLayout/AppLayout";
import Tabbar from "../../components/Tabbar/Tabbar";
import UploadCard from "../../components/UploadCard/UploadCard";
import SummaryCard from "../../components/SummaryCard/SummaryCard";
import ButtonContained from "../../components/StyledComponents/ButtonContained";
import { useStyles } from "./styles";

const HomePage = () => {
  const classes = useStyles();
  const ocrCtx = useContext(OCRContext);

  return (
    <>
      <AppLayout>
        <Tabbar />
        <div className={classes.content}>
          {ocrCtx.activePage === 0 && <UploadCard />}
          {ocrCtx.activePage === 1 && <SummaryCard />}
          {ocrCtx.activePage === 2 && (
            <Paper sx={{ maxWidth: 620, mx: "auto", mt: 6, p: 5, borderRadius: 5 }}>
              <Typography variant="h4" sx={{ mb: 1 }}>Đã lưu hóa đơn</Typography>
              <Typography color="text.secondary" sx={{ mb: 3 }}>
                Mã bản ghi: {ocrCtx.savedId}
              </Typography>
              <ButtonContained onClick={ocrCtx.reset}>ĐỌC HÓA ĐƠN KHÁC</ButtonContained>
            </Paper>
          )}
        </div>
      </AppLayout>
    </>
  );
};

export default HomePage;
