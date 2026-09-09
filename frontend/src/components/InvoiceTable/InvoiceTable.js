import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import {
  Box, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  IconButton, Paper, Table, TableBody, TableCell, TableContainer, TableHead,
  TablePagination, TableRow, TableSortLabel, TextField, Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import httpRequest from "../../httpRequest";
import ButtonOutlined from "../StyledComponents/ButtonOutlined";
import { COLORS } from "../../styles/constants";

const columns = [
  { id: "invoiceNumber", label: "Số hóa đơn" },
  { id: "sellerName", label: "Người bán" },
  { id: "sellerTaxCode", label: "MST người bán" },
  { id: "buyerName", label: "Người mua" },
  { id: "issueDate", label: "Ngày lập" },
  { id: "grandTotal", label: "Tổng tiền" },
  { id: "sourceFilename", label: "File nguồn" },
];

const InvoiceTable = ({ invoiceData, openSummary, onSearch, refreshInvoiceData }) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [search, setSearch] = useState("");
  const [order, setOrder] = useState("desc");
  const [orderBy, setOrderBy] = useState("createdAt");
  const [deleteRow, setDeleteRow] = useState(null);
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    const timer = setTimeout(() => onSearch(search), 350);
    return () => clearTimeout(timer);
  }, [search, onSearch]);

  const sorted = [...invoiceData].sort((a, b) => {
    const first = a[orderBy] ?? ""; const second = b[orderBy] ?? "";
    return (first < second ? -1 : first > second ? 1 : 0) * (order === "asc" ? 1 : -1);
  });

  const confirmDelete = async () => {
    try {
      await httpRequest.delete(`/invoices/${deleteRow.id}`);
      enqueueSnackbar("Đã xóa hóa đơn", { variant: "success" });
      refreshInvoiceData(search);
    } catch (error) {
      enqueueSnackbar(error.response?.data?.error || "Không thể xóa hóa đơn", { variant: "error" });
    } finally { setDeleteRow(null); }
  };

  return (
    <Paper sx={{ width: "100%", overflow: "hidden", mt: 4, borderRadius: 4 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 2 }}>
        <SearchIcon color="action" />
        <TextField fullWidth size="small" label="Tìm theo số HĐ, tên/MST người bán, người mua, mã CQT hoặc dữ liệu XML"
          value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} />
      </Box>
      <TableContainer sx={{ maxHeight: "calc(100vh - 230px)" }}><Table stickyHeader>
        <TableHead><TableRow>
          {columns.map((column) => <TableCell key={column.id} sx={{ minWidth: column.id.includes("Name") ? 180 : 120 }}>
            <TableSortLabel active={orderBy === column.id} direction={orderBy === column.id ? order : "asc"}
              onClick={() => { setOrder(orderBy === column.id && order === "asc" ? "desc" : "asc"); setOrderBy(column.id); }}>
              <Typography fontWeight={700}>{column.label}</Typography>
            </TableSortLabel>
          </TableCell>)}
          <TableCell align="right">Thao tác</TableCell>
        </TableRow></TableHead>
        <TableBody>
          {sorted.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((row) => (
            <TableRow hover key={row.id} onClick={() => openSummary(row)} sx={{ cursor: "pointer" }}>
              {columns.map((column) => <TableCell key={column.id}>{row[column.id] ?? ""}</TableCell>)}
              <TableCell align="right"><IconButton onClick={(event) => { event.stopPropagation(); setDeleteRow(row); }}><DeleteIcon sx={{ color: COLORS.PRIMARY }} /></IconButton></TableCell>
            </TableRow>
          ))}
          {!invoiceData.length && <TableRow><TableCell colSpan={columns.length + 1} align="center">Chưa có hóa đơn phù hợp.</TableCell></TableRow>}
        </TableBody>
      </Table></TableContainer>
      <TablePagination component="div" rowsPerPageOptions={[10, 25, 50]} count={invoiceData.length}
        rowsPerPage={rowsPerPage} page={page} onPageChange={(_, value) => setPage(value)}
        onRowsPerPageChange={(event) => { setRowsPerPage(Number(event.target.value)); setPage(0); }} />
      <Dialog open={Boolean(deleteRow)} onClose={() => setDeleteRow(null)}>
        <DialogTitle>Xóa hóa đơn</DialogTitle>
        <DialogContent><DialogContentText>Bản ghi và file nguồn sẽ bị xóa khỏi SQL Server. Bạn có chắc không?</DialogContentText></DialogContent>
        <DialogActions><ButtonOutlined onClick={() => setDeleteRow(null)}>HỦY</ButtonOutlined><ButtonOutlined onClick={confirmDelete}>XÓA</ButtonOutlined></DialogActions>
      </Dialog>
    </Paper>
  );
};

export default InvoiceTable;
