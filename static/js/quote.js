const catalog = JSON.parse(document.getElementById("catalog-data").textContent);
const tbody = document.querySelector("#lines-table tbody");
const statusEl = document.getElementById("status");
let quoteNumber = "";
let quoteFolder = "";
let calcTimer = null;
let saveTimer = null;

function money(n) {
  const v = Number(n || 0);
  return v.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function options(list, selected, valueKey) {
  const blank = `<option value=""></option>`;
  return (
    blank +
    list
      .map((item) => {
        const value = valueKey ? item[valueKey] : item;
        const label = valueKey ? item.name : item;
        return `<option value="${escapeHtml(String(value))}" ${
          String(value) === String(selected || "") ? "selected" : ""
        }>${escapeHtml(String(label))}</option>`;
      })
      .join("")
  );
}

function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function addLine(line = {}) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input class="qty" type="number" min="0" step="1" value="${line.qty ?? 1}" /></td>
    <td><input class="width" type="number" min="0" step="0.01" value="${line.width ?? ""}" /></td>
    <td><input class="height" type="number" min="0" step="0.01" value="${line.height ?? ""}" /></td>
    <td><input class="thick" value="${escapeHtml(String(line.thick ?? ""))}" /></td>
    <td><select class="type">${options(catalog.glass_types || [], line.type, "name")}</select></td>
    <td><select class="grid">${options(catalog.grids || [], line.grid, "name")}</select></td>
    <td><select class="spacer">${options(catalog.spacers || [], line.spacer, "name")}</select></td>
    <td><select class="color">${options(catalog.colors || [], line.color)}</select></td>
    <td><select class="vert">${options(catalog.vert || [], line.vert)}</select></td>
    <td><select class="hori">${options(catalog.hori || [], line.hori)}</select></td>
    <td class="sqft">${line.sqft ?? ""}</td>
    <td class="money">${line.total != null ? money(line.total) : ""}</td>
    <td><button type="button" class="btn-x" title="Remove">×</button></td>
  `;
  tr.querySelector(".btn-x").addEventListener("click", () => {
    tr.remove();
    scheduleCalc();
  });
  tr.querySelectorAll("input, select").forEach((el) => {
    el.addEventListener("input", scheduleCalc);
    el.addEventListener("change", scheduleCalc);
  });
  tbody.appendChild(tr);
}

function collectPayload() {
  const lines = [...tbody.querySelectorAll("tr")].map((tr) => ({
    qty: tr.querySelector(".qty").value,
    width: tr.querySelector(".width").value,
    height: tr.querySelector(".height").value,
    thick: tr.querySelector(".thick").value,
    type: tr.querySelector(".type").value,
    grid: tr.querySelector(".grid").value,
    spacer: tr.querySelector(".spacer").value,
    color: tr.querySelector(".color").value,
    vert: tr.querySelector(".vert").value,
    hori: tr.querySelector(".hori").value,
  }));
  const clientSelect = document.getElementById("client-id");
  const selected = clientSelect.options[clientSelect.selectedIndex];
  return {
    client_id: clientSelect.value,
    client_name: selected && selected.value ? selected.textContent : "",
    date: document.getElementById("quote-date").value,
    notes: document.getElementById("notes").value,
    quote_number: quoteNumber,
    folder: quoteFolder,
    lines,
  };
}

function applyPriced(quote) {
  const rows = [...tbody.querySelectorAll("tr")];
  (quote.lines || []).forEach((line, i) => {
    if (!rows[i]) return;
    rows[i].querySelector(".sqft").textContent = line.sqft || "";
    rows[i].querySelector(".money").textContent = line.total ? money(line.total) : "";
  });
  document.getElementById("qty-total").textContent = quote.qty_total || 0;
  document.getElementById("sqft-total").textContent = quote.sqft_total || 0;
  document.getElementById("grand-total").textContent = money(quote.grand_total || 0);
  quoteNumber = quote.quote_number || quoteNumber;
  quoteFolder = quote.folder || quoteFolder;
  document.getElementById("quote-number-label").textContent = quoteNumber
    ? `Quote ${quoteNumber}`
    : "";
}

async function calculate() {
  const res = await fetch("/api/calculate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectPayload()),
  });
  const quote = await res.json();
  applyPriced(quote);
  return quote;
}

function scheduleCalc() {
  clearTimeout(calcTimer);
  calcTimer = setTimeout(async () => {
    await calculate();
    scheduleLastSave();
  }, 180);
}

function scheduleLastSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch("/api/last-quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });
  }, 800);
}

function setStatus(msg, ok = true) {
  statusEl.textContent = msg;
  statusEl.style.color = ok ? "#3d3832" : "#8b3a2f";
}

async function loadPastQuotes(clientId) {
  const select = document.getElementById("past-quotes");
  select.innerHTML = `<option value="">No saved quotes yet</option>`;
  if (!clientId) return;
  const res = await fetch(`/api/quotes/${encodeURIComponent(clientId)}`);
  const items = await res.json();
  if (!items.length) return;
  select.innerHTML = `<option value="">Select a saved quote…</option>`;
  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.folder;
    const total = item.grand_total != null ? ` · ${money(item.grand_total)}` : "";
    opt.textContent = `${item.quote_number || item.folder}${total}`;
    select.appendChild(opt);
  });
}

function fillForm(quote) {
  tbody.innerHTML = "";
  document.getElementById("quote-date").value = quote.date || "";
  document.getElementById("notes").value = quote.notes || "";
  if (quote.client_id) document.getElementById("client-id").value = quote.client_id;
  (quote.lines && quote.lines.length ? quote.lines : [{}]).forEach(addLine);
  applyPriced(quote);
}

async function download(url, fallbackName) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectPayload()),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Download failed" }));
    setStatus(err.error || "Download failed", false);
    return;
  }
  const blob = await res.blob();
  const disp = res.headers.get("Content-Disposition") || "";
  const match = disp.match(/filename=([^;]+)/i);
  const name = match ? match[1].replace(/"/g, "") : fallbackName;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
  setStatus(`Downloaded ${name}`);
}

document.getElementById("btn-add-line").addEventListener("click", () => {
  addLine();
  scheduleCalc();
});
document.getElementById("btn-clear").addEventListener("click", () => {
  tbody.innerHTML = "";
  quoteNumber = "";
  quoteFolder = "";
  document.getElementById("notes").value = "";
  addLine();
  scheduleCalc();
});
document.getElementById("client-id").addEventListener("change", (e) => {
  loadPastQuotes(e.target.value);
  scheduleCalc();
});
document.getElementById("btn-load-quote").addEventListener("click", async () => {
  const clientId = document.getElementById("client-id").value;
  const folder = document.getElementById("past-quotes").value;
  if (!clientId || !folder) {
    setStatus("Choose a client and a saved quote first.", false);
    return;
  }
  const res = await fetch(`/api/quotes/${encodeURIComponent(clientId)}/${encodeURIComponent(folder)}`);
  if (!res.ok) {
    setStatus("Could not load that quote.", false);
    return;
  }
  fillForm(await res.json());
  setStatus("Quote loaded.");
});
document.getElementById("btn-save").addEventListener("click", async () => {
  const res = await fetch("/api/quotes/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectPayload()),
  });
  const data = await res.json();
  if (!res.ok) {
    setStatus(data.error || "Save failed", false);
    return;
  }
  applyPriced(data.quote);
  await loadPastQuotes(document.getElementById("client-id").value);
  document.getElementById("past-quotes").value = data.folder;
  setStatus(`Saved to ${data.path}`);
});
const downloadFormats = {
  pdf: ["/api/export/pdf", "quote.pdf"],
  xlsx: ["/api/export/xlsx", "quote.xlsx"],
  csv: ["/api/export/csv", "quote.csv"],
};
const downloadBtn = document.getElementById("btn-download");
const downloadList = document.getElementById("download-list");
function closeDownloadMenu() {
  downloadList.hidden = true;
  downloadBtn.setAttribute("aria-expanded", "false");
}
downloadBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const open = downloadList.hidden;
  downloadList.hidden = !open;
  downloadBtn.setAttribute("aria-expanded", open ? "true" : "false");
});
downloadList.querySelectorAll("[data-download]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const spec = downloadFormats[btn.dataset.download];
    closeDownloadMenu();
    if (spec) download(spec[0], spec[1]);
  });
});
document.addEventListener("click", closeDownloadMenu);
document.getElementById("btn-needed").addEventListener("click", () =>
  download("/api/export/glass-needed", "glass_needed.csv")
);
document.getElementById("btn-email").addEventListener("click", async () => {
  const btn = document.getElementById("btn-email");
  const payload = collectPayload();
  if (!payload.client_id) {
    setStatus("Select or add a client first.", false);
    return;
  }
  const res = await fetch("/api/email", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    setStatus(data.error || "Could not create the email.", false);
    return;
  }
  try {
    await navigator.clipboard.writeText(data.body || "");
  } catch (_err) {
    setStatus("Could not copy the message. The mail draft may still have opened.", false);
    return;
  }
  btn.classList.add("copied");
  const original = btn.textContent;
  btn.textContent = "Copied";
  window.setTimeout(() => {
    btn.classList.remove("copied");
    btn.textContent = original;
  }, 1800);
  if (data.opened && data.to) {
    setStatus("Email draft opened with the PDF attached. Message copied.");
  } else if (data.opened) {
    setStatus("Message copied. Draft opened. Add an email on the client to fill in To.");
  } else {
    setStatus("Message copied. Could not open the mail app automatically.");
  }
});

const dialog = document.getElementById("client-dialog");
document.getElementById("btn-add-client").addEventListener("click", () => dialog.showModal());
document.getElementById("btn-cancel-client").addEventListener("click", () => dialog.close());
document.getElementById("client-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const payload = {
    name: form.name.value,
    phone: form.phone.value,
    email: form.email.value,
    address: form.address.value,
    notes: form.notes.value,
  };
  const res = await fetch("/api/clients", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const client = await res.json();
  if (!res.ok) {
    setStatus(client.error || "Could not add client", false);
    return;
  }
  const select = document.getElementById("client-id");
  const opt = document.createElement("option");
  opt.value = client.id;
  opt.textContent = client.name;
  select.appendChild(opt);
  select.value = client.id;
  dialog.close();
  form.reset();
  await loadPastQuotes(client.id);
  setStatus(`Added client ${client.name}`);
});

(async function init() {
  const last = await (await fetch("/api/last-quote")).json();
  if (last && last.lines && last.lines.length) {
    fillForm(last);
    if (last.client_id) await loadPastQuotes(last.client_id);
  } else {
    addLine();
  }
  scheduleCalc();
})();
