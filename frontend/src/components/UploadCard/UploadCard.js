import { useContext, useState } from "react";
import { Alert, FormControlLabel, Switch, Typography } from "@mui/material";
import { BarLoader } from "react-spinners";
import { useSnackbar } from "notistack";
import ButtonContained from "../StyledComponents/ButtonContained";
import OCRContext from "../../context/ocr-context";
import httpRequest from "../../httpRequest";
import { useStyles } from "./styles";
import { COLORS } from "../../styles/constants";
const UploadCard = () => {
  const classes = useStyles();
  const ocrCtx = useContext(OCRContext);
  const [isLoading, setIsLoading] = useState(false);
  const [useOcr, setUseOcr] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const handleImageUpload = (event) => {
    const file = event.target.files?.[0] || null;
    ocrCtx.setFile(file);
  };

  const handleParse = async () => {
    if (!ocrCtx.file) {
      enqueueSnackbar("Vui lòng chọn file hóa đơn", { variant: "warning" });
      return;
    }
    const form = new FormData();
    form.append("file", ocrCtx.file);
    form.append("use_ocr", String(useOcr));
    setIsLoading(true);
    try {
      const response = await httpRequest.post("/invoices/parse", form, { timeout: 600000 });
      ocrCtx.setDraft(response.data);
      ocrCtx.setActivePage(1);
      response.data.warnings?.forEach((warning) => enqueueSnackbar(warning, { variant: "warning" }));
    } catch (error) {
      enqueueSnackbar(error.response?.data?.error || "Không thể đọc file", { variant: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className={classes.rootContainer}>
        <Typography variant="h5" sx={{ pt: 2 }}>
          Đọc hóa đơn
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ px: 3, mt: 0.5 }}>
          PDF, XML, ảnh, JSON, TXT hoặc input đặc biệt
        </Typography>
        <div className={classes.input}>
          <input
            type="file"
            onChange={(e) => handleImageUpload(e)}
            className={classes.fileInput}
            accept=".pdf,.xml,.json,.txt,.csv,image/*"
          />
        </div>
        <FormControlLabel
          control={<Switch checked={useOcr} onChange={(event) => setUseOcr(event.target.checked)} color="secondary" />}
          label="Bật OCR cho PDF scan / ảnh"
        />
        <Alert severity="info" sx={{ mx: 3, textAlign: "left" }}>
          XML được đọc trực tiếp. PDF được đọc theo bố cục và bảng; khi bật OCR, chỉ các trang thiếu lớp chữ rõ ràng mới cần nhận dạng ảnh.
        </Alert>
        {isLoading && (
          <div className={classes.loader}>
            <BarLoader color={COLORS.PRIMARY} width={150} />
          </div>
        )}
        <ButtonContained
          style={{
            margin: "20px",
            padding: "5px 35px",
          }}
          onClick={handleParse}
          disabled={isLoading}
        >
          {isLoading ? "ĐANG ĐỌC..." : "ĐỌC FILE"}
        </ButtonContained>
      </div>
    </>
  );
};

export default UploadCard;
