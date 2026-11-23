import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "file:///C:/Users/mebalci/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const inputPath = "C:/Users/mebalci/Desktop/fzd-xml-filter/docs/fzd-urunler-test.xlsx";
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const summary = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 6000,
  tableMaxRows: 8,
  tableMaxCols: 22,
  tableMaxCellChars: 80,
});
console.log(summary.ndjson);
workbook.recalculate();
const preview = await workbook.render({sheetName: "Ürünler", range: "A1:F7", scale: 1.4, format: "png"});
await fs.writeFile("C:/Users/mebalci/Desktop/fzd-xml-filter/docs/fzd-urunler-preview.png", new Uint8Array(await preview.arrayBuffer()));
