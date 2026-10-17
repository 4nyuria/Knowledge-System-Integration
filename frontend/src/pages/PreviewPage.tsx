
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Alert,
  Card,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Button,
} from "@mui/material";
import * as XLSX from "xlsx";
import { importSource } from "../services/api";
type NavigationState = {
  file?: File;
  sourceType?: string;
};

type PreviewData = {
  columns: string[];
  rows: string[][];
  allRows: string[][];
  totalRows: number;
};
export default function PreviewPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const { file, sourceType } = (location.state ?? {}) as NavigationState;

  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
const [importing, setImporting] = useState(false);
  useEffect(() => {
    if (!file) {
      setError(
        "No se recibió ningún archivo. Volvé a la pantalla anterior y seleccioná uno.",
      );
      return;
    }

    let cancelled = false;

    const readFile = async () => {
      setLoading(true);
      setError("");
      setPreview(null);

      try {
        const buffer = await file.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const firstSheetName = workbook.SheetNames[0];

        if (!firstSheetName) {
          throw new Error("El archivo no contiene hojas con datos.");
        }

        const worksheet = workbook.Sheets[firstSheetName];
        const data = XLSX.utils.sheet_to_json<unknown[]>(worksheet, {
          header: 1,
          defval: "",
          raw: false,
        });

        if (data.length < 2) {
          throw new Error(
            "El archivo debe tener encabezados y al menos un registro.",
          );
        }

        const columns = data[0].map((value) => String(value).trim());

        if (columns.some((column) => !column)) {
          throw new Error(
            "Hay encabezados vacíos. Completá los nombres de todas las columnas.",
          );
        }

        const rows = data.slice(1).filter((row) =>
          row.some((cell) => String(cell).trim() !== ""),
        );

        const allRows = rows.map((row) =>
  columns.map((_, index) => String(row[index] ?? "")),
);

if (!cancelled) {
  setPreview({
    columns,
    rows: allRows.slice(0, 5),
    allRows,
    totalRows: allRows.length,
  });
}
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "No se pudo leer el archivo.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void readFile();

    return () => {
      cancelled = true;
    };
  }, [file]);
const handleContinue = async () => {
  if (!file || !preview || importing) return;

  setImporting(true);
  setError("");

  try {
    await importSource({
      fileName: file.name,
      columns: preview.columns,
      rows: preview.allRows,
      sourceType: sourceType ?? "Excel / CSV",
    });

    navigate("/fuentes");
  } catch (err) {
    setError(
      err instanceof Error
        ? err.message
        : "No se pudo importar el archivo.",
    );
  } finally {
    setImporting(false);
  }
};
  return (
    <Box>
      <Typography variant="h4">Vista previa</Typography>

      <Typography color="text.secondary" sx={{ mb: 3 }}>
        {file
          ? `${file.name} · ${sourceType ?? "Archivo"}`
          : "Archivo no seleccionado"}
      </Typography>

      {loading && <Alert severity="info">Leyendo archivo...</Alert>}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {preview && (
        <>
          <Alert severity="success" sx={{ mb: 3 }}>
            Archivo leído correctamente: {preview.totalRows} registros y{" "}
            {preview.columns.length} columnas. Se muestran las primeras{" "}
            {preview.rows.length} filas.
          </Alert>

          <Card variant="outlined" sx={{ mb: 3, overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {preview.columns.map((column, index) => (
                    <TableCell
                      key={`${column}-${index}`}
                      sx={{ fontWeight: 700 }}
                    >
                      {column}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>

              <TableBody>
                {preview.rows.map((row, rowIndex) => (
                  <TableRow key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <TableCell key={cellIndex}>{cell}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </>
      )}

      <Box sx={{ display: "flex", gap: 1 }}>
        <Button onClick={() => navigate("/fuentes/nueva")}>
          Volver
        </Button>

       <Button
  variant="contained"
  disabled={!preview || loading || importing}
  onClick={handleContinue}
>
  {importing ? "Importando..." : "Continuar"}
</Button>
      </Box>
    </Box>
  );
}
