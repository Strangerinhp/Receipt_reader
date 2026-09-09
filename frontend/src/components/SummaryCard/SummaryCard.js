import { useContext, useEffect, useMemo, useState } from "react";
import { useSnackbar } from "notistack";
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Chip, Divider,
  Grid, IconButton, Paper, Tab, Tabs, TextField, Tooltip, Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SaveIcon from "@mui/icons-material/Save";
import OCRContext from "../../context/ocr-context";
import httpRequest from "../../httpRequest";
import ButtonContained from "../StyledComponents/ButtonContained";
import { useStyles } from "./styles";

const LABELS = {
  PBan: "Phiên bản", THDon: "Tên loại hóa đơn", KHMSHDon: "Ký hiệu mẫu số",
  KHHDon: "Ký hiệu hóa đơn", SHDon: "Số hóa đơn", NLap: "Ngày lập",
  DVTTe: "Đơn vị tiền tệ", TGia: "Tỷ giá", HTTToan: "Hình thức thanh toán",
  MSTTCGP: "MST tổ chức cung cấp giải pháp", MSTDVNUNLHDon: "MST đơn vị nhận ủy nhiệm",
  TDVNUNLHDon: "Tên đơn vị nhận ủy nhiệm", DCDVNUNLHDon: "Địa chỉ đơn vị nhận ủy nhiệm",
  HDCTTChinh: "Hóa đơn chiết khấu thương mại", Ten: "Tên", MST: "Mã số thuế",
  DChi: "Địa chỉ", MKHang: "Mã khách hàng", SDThoai: "Số điện thoại",
  DCTDTu: "Email", HVTNMHang: "Họ tên người mua hàng", STKNHang: "Số tài khoản ngân hàng",
  TNHang: "Tên ngân hàng", Fax: "Fax", Website: "Website", TChat: "Tính chất",
  STT: "STT", MHHDVu: "Mã hàng hóa, dịch vụ", THHDVu: "Tên hàng hóa, dịch vụ",
  DVTinh: "Đơn vị tính", SLuong: "Số lượng", DGia: "Đơn giá", TLCKhau: "Tỷ lệ chiết khấu",
  STCKhau: "Số tiền chiết khấu", ThTien: "Thành tiền", TSuat: "Thuế suất",
  TThue: "Tiền thuế", TgTCThue: "Tổng tiền chưa thuế", TgTThue: "Tổng tiền thuế",
  TTCKTMai: "Tổng chiết khấu thương mại", TgTTTBSo: "Tổng tiền thanh toán bằng số",
  TgTTTBChu: "Tổng tiền thanh toán bằng chữ", MCCQT: "Mã của cơ quan thuế",
};

const EMPTY_ITEM = {
  TChat: "1", STT: "", MHHDVu: "", THHDVu: "", DVTinh: "", SLuong: "",
  DGia: "", TLCKhau: "", STCKhau: "", ThTien: "", TSuat: "", TThue: "", TTKhac: [],
};
const SELLER_FIELDS = [
  "Ten", "MST", "DChi", "SDThoai", "DCTDTu", "STKNHang", "TNHang", "Fax", "Website",
];
const BUYER_FIELDS = [
  "Ten", "MST", "DChi", "MKHang", "SDThoai", "DCTDTu", "HVTNMHang", "STKNHang", "TNHang",
];
const labelFor = (key) => `${LABELS[key] || key} (${key})`;

const setAtPath = (source, path, value) => {
  const root = Array.isArray(source) ? [...source] : { ...source };
  let cursor = root;
  path.forEach((part, index) => {
    if (index === path.length - 1) cursor[part] = value;
    else {
      const child = cursor[part];
      cursor[part] = Array.isArray(child) ? [...child] : { ...(child || {}) };
      cursor = cursor[part];
    }
  });
  return root;
};

const PrimitiveFields = ({ value = {}, path, onChange, exclude = [], include }) => (
  <Grid container spacing={1.5}>
    {(include ? include.map((key) => [key, value[key] ?? ""]) : Object.entries(value))
      .filter(([key, item]) => !exclude.includes(key) && (item === null || typeof item !== "object"))
      .map(([key, item]) => (
        <Grid item xs={12} md={["DChi", "THHDVu", "TgTTTBChu"].includes(key) ? 12 : 6} key={key}>
          <TextField fullWidth size="small" label={labelFor(key)} value={item ?? ""}
            multiline={["Ten", "DChi", "THHDVu", "TgTTTBChu", "TNHang"].includes(key)}
            maxRows={8}
            onChange={(event) => onChange([...path, key], event.target.value)} />
        </Grid>
      ))}
  </Grid>
);

const ExtraFields = ({ value = [], path, onChange }) => {
  const extras = Array.isArray(value) ? value : [];
  return (
    <Box sx={{ mt: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="subtitle2">Thông tin khác (TTKhac)</Typography>
        <ButtonContained onClick={() => onChange(path, [...extras, { TTruong: "", KDLieu: "string", DLieu: "" }])}
          style={{ padding: "4px 12px" }}><AddIcon fontSize="small" /> THÊM</ButtonContained>
      </Box>
      {!extras.length && <Typography variant="body2" color="text.secondary">Chưa có trường mở rộng.</Typography>}
      {extras.map((extra, index) => (
        <Paper variant="outlined" sx={{ p: 1.5, mb: 1 }} key={index}>
          <Grid container spacing={1} alignItems="center">
            {["TTruong", "KDLieu", "DLieu"].map((key) => (
              <Grid item xs={12} md={key === "DLieu" ? 5 : 3} key={key}>
                <TextField fullWidth size="small"
                  label={key === "TTruong" ? "Tên trường" : key === "KDLieu" ? "Kiểu dữ liệu" : "Dữ liệu"}
                  value={extra?.[key] ?? ""}
                  onChange={(event) => onChange([...path, index, key], event.target.value)} />
              </Grid>
            ))}
            <Grid item xs={12} md={1}>
              <IconButton onClick={() => onChange(path, extras.filter((_, i) => i !== index))} aria-label="Xóa trường">
                <DeleteIcon color="error" />
              </IconButton>
            </Grid>
          </Grid>
        </Paper>
      ))}
    </Box>
  );
};

const Section = ({ title, code, children, defaultExpanded = false }) => (
  <Accordion defaultExpanded={defaultExpanded} sx={{ mb: 1, borderRadius: "12px !important" }}>
    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
      <Typography fontWeight={700}>{title} <Typography component="span" color="text.secondary">· {code}</Typography></Typography>
    </AccordionSummary>
    <AccordionDetails>{children}</AccordionDetails>
  </Accordion>
);

const SourcePreview = ({ draft }) => {
  const [tab, setTab] = useState(0);
  const sourceUrl = draft?.source_base64 ? `data:${draft.content_type || "application/octet-stream"};base64,${draft.source_base64}` : "";
  const isPdf = draft?.content_type === "application/pdf" || draft?.filename?.toLowerCase().endsWith(".pdf");
  const isImage = draft?.content_type?.startsWith("image/");
  return (
    <Paper elevation={3} sx={{ borderRadius: 4, overflow: "hidden", height: "calc(100vh - 190px)", minHeight: 620 }}>
      <Tabs value={tab} onChange={(_, value) => setTab(value)} centered>
        <Tab label="File gốc" /><Tab label={draft?.ocr_used ? "Văn bản OCR" : "Văn bản đọc được"} />
      </Tabs>
      <Divider />
      {tab === 0 && <Box sx={{ height: "calc(100% - 49px)", bgcolor: "#f5f5f5", overflow: "auto", p: isImage ? 2 : 0 }}>
        {isPdf && sourceUrl && <iframe title="Hóa đơn PDF" src={sourceUrl} style={{ width: "100%", height: "100%", border: 0 }} />}
        {isImage && sourceUrl && <img src={sourceUrl} alt="Hóa đơn" style={{ width: "100%", height: "auto" }} />}
        {!isPdf && !isImage && <TextField multiline fullWidth minRows={24} value={draft?.extracted_text || "Không có bản xem trước."} InputProps={{ readOnly: true }} />}
      </Box>}
      {tab === 1 && <TextField multiline fullWidth value={draft?.extracted_text || "Không đọc được văn bản."} minRows={26} InputProps={{ readOnly: true }} />}
    </Paper>
  );
};

const SummaryCard = ({ dataFromDB, dataChanged, onClose }) => {
  const classes = useStyles();
  const ocrCtx = useContext(OCRContext);
  const { enqueueSnackbar } = useSnackbar();
  const initialDraft = useMemo(() => dataFromDB ? {
    filename: dataFromDB.sourceFilename, content_type: dataFromDB.sourceType,
    ocr_enabled: dataFromDB.ocrEnabled, extracted_text: dataFromDB.ocrText,
    source_base64: dataFromDB.source_base64, document: dataFromDB.document,
    parser: dataFromDB.ocrEnabled ? "OCR" : "XML/PDF parser",
  } : ocrCtx.draft, [dataFromDB, ocrCtx.draft]);
  const [draft, setDraft] = useState(initialDraft);
  const [saving, setSaving] = useState(false);
  useEffect(() => setDraft(initialDraft), [initialDraft]);
  if (!draft?.document) return <Alert severity="warning" sx={{ m: 4 }}>Chưa có dữ liệu hóa đơn để kiểm tra.</Alert>;

  const document = draft.document;
  const general = document.TTChung || {};
  const content = document.NDHDon || {};
  const seller = content.NBan || {};
  const buyer = content.NMua || {};
  const items = Array.isArray(content.DSHHDVu) ? content.DSHHDVu : [];
  const totals = content.TToan || {};
  const handleChange = (path, value) => setDraft((current) => ({ ...current, document: setAtPath(current.document, path, value) }));

  const handleSave = async () => {
    setSaving(true);
    try {
      if (dataFromDB?.id) {
        await httpRequest.put(`/invoices/${dataFromDB.id}`, { document: draft.document });
        enqueueSnackbar("Đã cập nhật hóa đơn", { variant: "success" });
        dataChanged?.();
      } else {
        const response = await httpRequest.post("/invoices", draft);
        ocrCtx.setDraft(draft); ocrCtx.setSavedId(response.data.id); ocrCtx.setActivePage(2);
        enqueueSnackbar("Đã lưu hóa đơn vào database", { variant: "success" });
      }
    } catch (error) {
      enqueueSnackbar(error.response?.data?.error || "Không thể lưu hóa đơn", { variant: "error" });
    } finally { setSaving(false); }
  };

  const downloadSource = () => {
    if (!draft.source_base64) return;
    const anchor = window.document.createElement("a");
    anchor.href = `data:${draft.content_type};base64,${draft.source_base64}`;
    anchor.download = draft.filename || "invoice"; anchor.click();
  };
  const openSource = () => {
    if (!draft.source_base64) return;
    const bytes = Uint8Array.from(atob(draft.source_base64), (character) => character.charCodeAt(0));
    window.open(URL.createObjectURL(new Blob([bytes], { type: draft.content_type })), "_blank", "noopener,noreferrer");
  };

  return (
    <div className={classes.rootContainer}>
      <Box className={classes.bar}>
        <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
          <Chip label={draft.parser || "Đã đọc"} color="secondary" />
          <Chip label={draft.ocr_used ? "OCR đã bật" : "Không dùng OCR"} variant="outlined" />
          <Typography variant="body2" color="text.secondary">{draft.filename}</Typography>
        </Box>
        <Box>
          {onClose && <ButtonContained onClick={onClose} style={{ marginRight: 8 }}>QUAY LẠI</ButtonContained>}
          <Tooltip title="Tải file gốc"><span><IconButton onClick={downloadSource} disabled={!draft.source_base64}><DownloadIcon /></IconButton></span></Tooltip>
          <Tooltip title="Mở file gốc"><span><IconButton onClick={openSource} disabled={!draft.source_base64}><OpenInNewIcon /></IconButton></span></Tooltip>
          <ButtonContained onClick={handleSave} disabled={saving} style={{ marginLeft: 8 }}>
            <SaveIcon sx={{ mr: 0.5 }} /> {saving ? "ĐANG LƯU" : dataFromDB ? "CẬP NHẬT" : "LƯU SQL SERVER"}
          </ButtonContained>
        </Box>
      </Box>
      {draft.warnings?.map((warning, index) => <Alert severity="warning" key={index} sx={{ mb: 1 }}>{warning}</Alert>)}
      <Grid container spacing={2}>
        <Grid item xs={12} lg={5}><SourcePreview draft={draft} /></Grid>
        <Grid item xs={12} lg={7}><Box className={classes.editorContainer}>
          <Section title="Thông tin chung" code="TTChung" defaultExpanded>
            <PrimitiveFields value={general} path={["TTChung"]} onChange={handleChange} exclude={["TTKhac"]} />
            <ExtraFields value={general.TTKhac} path={["TTChung", "TTKhac"]} onChange={handleChange} />
          </Section>
          <Section title="Người bán" code="NDHDon.NBan" defaultExpanded>
            <PrimitiveFields value={seller} path={["NDHDon", "NBan"]} onChange={handleChange} include={SELLER_FIELDS} />
            <ExtraFields value={seller.TTKhac} path={["NDHDon", "NBan", "TTKhac"]} onChange={handleChange} />
          </Section>
          <Section title="Người mua" code="NDHDon.NMua">
            <PrimitiveFields value={buyer} path={["NDHDon", "NMua"]} onChange={handleChange} include={BUYER_FIELDS} />
            <ExtraFields value={buyer.TTKhac} path={["NDHDon", "NMua", "TTKhac"]} onChange={handleChange} />
          </Section>
          <Section title={`Hàng hóa, dịch vụ (${items.length})`} code="NDHDon.DSHHDVu">
            <Box sx={{ textAlign: "right", mb: 1 }}><ButtonContained onClick={() => handleChange(["NDHDon", "DSHHDVu"], [...items, { ...EMPTY_ITEM, STT: String(items.length + 1) }])}><AddIcon /> THÊM DÒNG</ButtonContained></Box>
            {items.map((item, index) => <Paper variant="outlined" sx={{ p: 2, mb: 1.5 }} key={index}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}><Typography fontWeight={700}>{item.TChat === "4" ? "Ghi chú" : `Dòng ${item.STT || index + 1}`}{item.ExtractionSource?.page ? ` · Trang ${item.ExtractionSource.page}` : ""}</Typography>
                <IconButton onClick={() => handleChange(["NDHDon", "DSHHDVu"], items.filter((_, i) => i !== index))}><DeleteIcon color="error" /></IconButton></Box>
              <PrimitiveFields value={item} path={["NDHDon", "DSHHDVu", index]} onChange={handleChange} exclude={["TTKhac"]} />
              <ExtraFields value={item.TTKhac} path={["NDHDon", "DSHHDVu", index, "TTKhac"]} onChange={handleChange} />
            </Paper>)}
          </Section>
          <Section title="Tổng hợp thanh toán" code="NDHDon.TToan" defaultExpanded>
            <PrimitiveFields value={totals} path={["NDHDon", "TToan"]} onChange={handleChange} exclude={["TTKhac", "THTTLTSuat", "DSLPhi"]} />
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Tổng hợp theo thuế suất (THTTLTSuat)</Typography>
            {(totals.THTTLTSuat || []).map((rate, index) => <Paper variant="outlined" sx={{ p: 1.5, mb: 1 }} key={index}>
              <PrimitiveFields value={rate} path={["NDHDon", "TToan", "THTTLTSuat", index]} onChange={handleChange} />
            </Paper>)}
            <ExtraFields value={totals.TTKhac} path={["NDHDon", "TToan", "TTKhac"]} onChange={handleChange} />
          </Section>
          <Section title="Thông tin khác của nội dung" code="NDHDon.TTKhac"><ExtraFields value={content.TTKhac} path={["NDHDon", "TTKhac"]} onChange={handleChange} /></Section>
          <Section title="Thông tin cơ quan thuế" code="MCCQT"><TextField fullWidth size="small" label={labelFor("MCCQT")} value={document.MCCQT || ""} onChange={(event) => handleChange(["MCCQT"], event.target.value)} /></Section>
          <Section title="Dữ liệu kỹ thuật & chữ ký số" code="DSCKS">
            <Alert severity="info" sx={{ mb: 1 }}>Nhóm này được giữ nguyên để không làm mất dữ liệu chữ ký số.</Alert>
            <Paper component="pre" variant="outlined" sx={{ p: 2, maxHeight: 420, overflow: "auto", textAlign: "left", whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(document.DSCKS || {}, null, 2)}</Paper>
          </Section>
          <Section title="Toàn bộ cây dữ liệu" code="DocumentJson">
            <Alert severity="info" sx={{ mb: 1 }}>Chế độ này hiển thị cả tag/nhóm mở rộng chưa có form riêng, bảo đảm mọi dữ liệu đầu vào đều có thể kiểm tra.</Alert>
            <Paper component="pre" variant="outlined" sx={{ p: 2, maxHeight: 560, overflow: "auto", textAlign: "left", whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(document, null, 2)}</Paper>
          </Section>
        </Box></Grid>
      </Grid>
    </div>
  );
};

export default SummaryCard;
