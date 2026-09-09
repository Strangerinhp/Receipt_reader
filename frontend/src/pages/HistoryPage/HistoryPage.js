import { useCallback, useEffect, useState } from "react";
import { Alert, CircularProgress } from "@mui/material";
import { useSnackbar } from "notistack";
import AppLayout from "../../components/AppLayout/AppLayout";
import InvoiceTable from "../../components/InvoiceTable/InvoiceTable";
import SummaryCard from "../../components/SummaryCard/SummaryCard";
import httpRequest from "../../httpRequest";
import { useStyles } from "./styles";

const HistoryPage = () => {
  const classes = useStyles();
  const [invoices, setInvoices] = useState([]);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { enqueueSnackbar } = useSnackbar();

  const fetchInvoices = useCallback(async (query = "") => {
    setLoading(true); setError("");
    try {
      const response = await httpRequest.get("/invoices", { params: { q: query, page_size: 100 } });
      setInvoices(response.data.items || []);
    } catch (requestError) {
      setError(requestError.response?.data?.error || "Không thể tải danh sách hóa đơn.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  const openSummary = async (row) => {
    setLoading(true);
    try {
      const response = await httpRequest.get(`/invoices/${row.id}`);
      setSelectedInvoice(response.data);
    } catch (requestError) {
      enqueueSnackbar(requestError.response?.data?.error || "Không thể mở hóa đơn", { variant: "error" });
    } finally { setLoading(false); }
  };

  const refreshSelected = async () => {
    if (!selectedInvoice?.id) return;
    const response = await httpRequest.get(`/invoices/${selectedInvoice.id}`);
    setSelectedInvoice(response.data);
    fetchInvoices();
  };

  return (
    <AppLayout>
      {loading && <div className={classes.loader}><CircularProgress color="secondary" /></div>}
      {error && <Alert severity="error" sx={{ m: 3 }}>{error}</Alert>}
      {!selectedInvoice && (
        <div className={classes.table}>
          <InvoiceTable invoiceData={invoices} openSummary={openSummary} onSearch={fetchInvoices} refreshInvoiceData={fetchInvoices} />
        </div>
      )}
      {selectedInvoice && <SummaryCard dataFromDB={selectedInvoice} dataChanged={refreshSelected} onClose={() => setSelectedInvoice(null)} />}
    </AppLayout>
  );
};

export default HistoryPage;
