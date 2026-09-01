const catalog = JSON.parse(document.getElementById("catalog-data").textContent);
let clients = JSON.parse(document.getElementById("clients-data").textContent);
const statusEl = document.getElementById("status");

function namedTable(tbody, items) {
  tbody.innerHTML = "";
  (items || []).forEach((item) => addNamedRow(tbody, item.name || "", item.price ?? ""));
}

function addNamedRow(tbody, name = "", price = "") {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input class="name" value="${name}" /></td>
    <td><input class="price" type="number" step="0.01" value="${price}" /></td>
    <td><button type="button" class="btn-x">×</button></td>
  `;
  tr.querySelector(".btn-x").addEventListener("click", () => tr.remove());
  tbody.appendChild(tr);
}

function readNamed(tbody) {
  return [...tbody.querySelectorAll("tr")]
    .map((tr) => ({
      name: tr.querySelector(".name").value.trim(),
      price: Number(tr.querySelector(".price").value || 0),
    }))
    .filter((row) => row.name);
}

function renderColors(list) {
  const wrap = document.getElementById("colors-list");
  wrap.innerHTML = "";
  (list || []).forEach((color) => addColor(color));
}

function addColor(value = "") {
  const wrap = document.getElementById("colors-list");
  const chip = document.createElement("div");
  chip.className = "chip";
  chip.innerHTML = `<input value="${value}" /><button type="button" class="btn-x">×</button>`;
  chip.querySelector(".btn-x").addEventListener("click", () => chip.remove());
  wrap.appendChild(chip);
}

function readColors() {
  return [...document.querySelectorAll("#colors-list input")]
    .map((el) => el.value.trim())
    .filter(Boolean);
}

function renderClients() {
  const tbody = document.querySelector("#clients-table tbody");
  tbody.innerHTML = "";
  clients.forEach((client) => {
    const tr = document.createElement("tr");
    tr.dataset.id = client.id;
    tr.innerHTML = `
      <td><input class="c-name" value="${client.name || ""}" /></td>
      <td><input class="c-phone" value="${client.phone || ""}" /></td>
      <td><input class="c-email" value="${client.email || ""}" /></td>
      <td><input class="c-address" value="${client.address || ""}" /></td>
      <td><input class="c-notes" value="${client.notes || ""}" /></td>
      <td><button type="button" class="btn-x" title="Remove">×</button></td>
    `;
    tr.querySelector(".btn-x").addEventListener("click", async () => {
      const name = client.name || "this client";
      if (!window.confirm(`Remove ${name} from the client list? Their saved quotes will stay on disk.`)) {
        return;
      }
      await fetch(`/api/clients/${encodeURIComponent(client.id)}`, { method: "DELETE" });
      clients = clients.filter((c) => c.id !== client.id);
      renderClients();
    });
    tbody.appendChild(tr);
  });
}

document.querySelectorAll("[data-add]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const kind = btn.dataset.add;
    if (kind === "glass") addNamedRow(document.querySelector("#glass-table tbody"));
    if (kind === "grids") addNamedRow(document.querySelector("#grids-table tbody"));
    if (kind === "colors") addColor();
  });
});

document.getElementById("btn-save-settings").addEventListener("click", async () => {
  const payload = {
    company: {
      name: document.getElementById("co-name").value,
      tagline: document.getElementById("co-tagline").value,
      phone: document.getElementById("co-phone").value,
      email: document.getElementById("co-email").value,
      city: document.getElementById("co-city").value,
      website: document.getElementById("co-website").value,
      fax: document.getElementById("co-fax").value,
      hours: document.getElementById("co-hours").value,
      webmail: document.getElementById("co-webmail").value,
    },
    emails: catalog.emails || [],
    manufacturer: catalog.manufacturer || { name: "Trulite", email: "kbloink@trulite.com" },
    multipliers: {
      tfee: Number(document.getElementById("m-tfee").value || 1),
      factor: Number(document.getElementById("m-factor").value || 1),
      mup: Number(document.getElementById("m-mup").value || 1),
    },
    glass_types: readNamed(document.querySelector("#glass-table tbody")),
    grids: readNamed(document.querySelector("#grids-table tbody")),
    colors: readColors(),
    vert: document
      .getElementById("vert-list")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((n) => Number(n) || n),
    hori: document
      .getElementById("hori-list")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((n) => Number(n) || n),
  };
  const res = await fetch("/api/catalog", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    statusEl.textContent = "Could not save catalog.";
    return;
  }
  const rows = [...document.querySelectorAll("#clients-table tbody tr")];
  for (const tr of rows) {
    await fetch(`/api/clients/${encodeURIComponent(tr.dataset.id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: tr.querySelector(".c-name").value,
        phone: tr.querySelector(".c-phone").value,
        email: tr.querySelector(".c-email").value,
        address: tr.querySelector(".c-address").value,
        notes: tr.querySelector(".c-notes").value,
      }),
    });
  }
  statusEl.textContent = "Settings saved.";
});

(function init() {
  const co = catalog.company || {};
  document.getElementById("co-name").value = co.name || "";
  document.getElementById("co-tagline").value = co.tagline || "";
  document.getElementById("co-phone").value = co.phone || "";
  document.getElementById("co-email").value = co.email || "";
  document.getElementById("co-city").value = co.city || "";
  document.getElementById("co-website").value = co.website || "";
  document.getElementById("co-fax").value = co.fax || "";
  document.getElementById("co-hours").value = co.hours || "";
  document.getElementById("co-webmail").value = co.webmail || "";
  const m = catalog.multipliers || {};
  document.getElementById("m-tfee").value = m.tfee ?? 1.06;
  document.getElementById("m-factor").value = m.factor ?? 1.75;
  document.getElementById("m-mup").value = m.mup ?? 1.2;
  namedTable(document.querySelector("#glass-table tbody"), catalog.glass_types);
  namedTable(document.querySelector("#grids-table tbody"), catalog.grids);
  renderColors(catalog.colors);
  document.getElementById("vert-list").value = (catalog.vert || []).join(", ");
  document.getElementById("hori-list").value = (catalog.hori || []).join(", ");
  renderClients();
})();
