import { useContext, useEffect, useRef, useState } from "react";
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
  const [jobId, setJobId] = useState(() => sessionStorage.getItem("parseJobId"));
  const [progress, setProgress] = useState("");
  const [paused, setPaused] = useState(false);
  const [retryVersion, setRetryVersion] = useState(0);
  const submittedFile = useRef(null);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    setIsLoading(true);
    setPaused(false);
    const poll = async () => {
      let lastContact = Date.now();
      let failures = 0;
      try {
        while (!cancelled) {
          let job;
          try {
            const response = await httpRequest.get(`/invoices/parse-jobs/${jobId}`, { params: { summary: 1 }, timeout: 20000 });
            job = response.data;
            if (!["queued", "running", "completed", "failed"].includes(job?.status)) {
              throw new Error("API trả về phản hồi không hợp lệ.");
            }
            if (job.status === "completed") {
              setProgress("OCR đã xong, đang tải kết quả...");
              const localFile = submittedFile.current?.jobId === jobId ? submittedFile.current.file : null;
              const result = await httpRequest.get(`/invoices/parse-jobs/${jobId}/result`, {
                params: { include_source: localFile ? 0 : 1 },
                timeout: 120000,
              });
              job.result = result.data;
              if (localFile) {
                job.result.source_base64 = await new Promise((resolve, reject) => {
                  const reader = new FileReader();
                  reader.onload = () => resolve(reader.result.split(",", 2)[1]);
                  reader.onerror = () => reject(new Error("Không thể đọc lại file gốc trong trình duyệt."));
                  reader.readAsDataURL(localFile);
                });
              }
            }
            failures = 0;
            lastContact = Date.now();
          } catch (error) {
            if (cancelled) return;
            if (error.response?.status && error.response.status < 500 && ![408, 429].includes(error.response.status)) throw error;
            failures += 1;
            const detail = error.response?.status ? `HTTP ${error.response.status}` : (error.code || error.message || "mất mạng");
            if (failures >= 6 || Date.now() - lastContact > 90000) {
              setPaused(true);
              setProgress(`Chưa kết nối được với máy chủ (${detail}). Mã tác vụ đã được giữ lại. Kiểm tra runtime Colab rồi bấm thử kết nối lại; file sẽ không bị upload lần nữa.`);
              return;
            }
            setProgress(`Kết nối gián đoạn (${detail}), đang thử lại lần ${failures}/6...`);
            await new Promise(resolve => setTimeout(resolve, 5000));
            continue;
          }
          if (cancelled) return;
          if (job.status === "completed") {
            sessionStorage.removeItem("parseJobId");
            setJobId(null);
            ocrCtx.setDraft(job.result);
            ocrCtx.setActivePage(1);
            job.result.warnings?.forEach(warning => enqueueSnackbar(warning, { variant: "warning" }));
            return;
          }
          if (job.status === "failed") throw new Error(job.error);
          setProgress(job.message || (job.status === "queued" ? "Đang chờ xử lý..." : "Đang đọc hóa đơn. Bạn không cần tải lại file."));
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      } catch (error) {
        if (!cancelled) {
          sessionStorage.removeItem("parseJobId");
          setJobId(null);
          enqueueSnackbar(error.response?.data?.error || error.message, { variant: "error" });
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    poll();
    return () => { cancelled = true; };
    // Each job owns its polling loop; context changes must not restart it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, retryVersion]);

  const handleImageUpload = (event) => {
    const file = event.target.files?.[0] || null;
    ocrCtx.setFile(file);
  };

  const handleParse = async () => {
    if (jobId) {
      setRetryVersion(value => value + 1);
      return;
    }
    if (!ocrCtx.file) {
      enqueueSnackbar("Vui lòng chọn file hóa đơn", { variant: "warning" });
      return;
    }
    const form = new FormData();
    form.append("file", ocrCtx.file);
    form.append("use_ocr", String(useOcr));
    setIsLoading(true);
    setProgress("Đang tải file lên...");
    try {
      const response = await httpRequest.post("/invoices/parse-jobs", form, { timeout: 120000 });
      sessionStorage.setItem("parseJobId", response.data.id);
      submittedFile.current = { jobId: response.data.id, file: ocrCtx.file };
      setJobId(response.data.id);
    } catch (error) {
      enqueueSnackbar(error.response?.data?.error || `Không thể tải file (HTTP ${error.response?.status || "mất kết nối"}).`, { variant: "error" });
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
            disabled={isLoading || !!jobId}
            type="file"
            onChange={(e) => handleImageUpload(e)}
            className={classes.fileInput}
            accept=".pdf,.xml,.json,.txt,.csv,image/*"
          />
        </div>
        <FormControlLabel
          control={<Switch disabled={isLoading || !!jobId} checked={useOcr} onChange={(event) => setUseOcr(event.target.checked)} color="secondary" />}
          label="Bật OCR cho PDF scan / ảnh"
        />
        <Alert severity="info" sx={{ mx: 3, textAlign: "left" }}>
          XML được đọc trực tiếp. PDF được đọc theo bố cục và bảng; khi bật OCR, chỉ các trang thiếu lớp chữ rõ ràng mới cần nhận dạng ảnh.
        </Alert>
        {(isLoading || paused) && (
          <div className={classes.loader} role="status" aria-live="polite">
            {isLoading && <BarLoader color={COLORS.PRIMARY} width={150} />}
            <Typography variant="body2" sx={{ mt: 1 }}>{progress}</Typography>
          </div>
        )}
        <ButtonContained
          style={{
            margin: "20px",
            padding: "5px 35px",
          }}
          onClick={handleParse}
          disabled={isLoading || (!!jobId && !paused)}
        >
          {paused ? "THỬ KẾT NỐI LẠI" : isLoading ? "ĐANG ĐỌC..." : "ĐỌC FILE"}
        </ButtonContained>
      </div>
    </>
  );
};

export default UploadCard;
