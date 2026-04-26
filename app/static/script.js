// =========================================================
// script.js
// SalvageIQ front-end behavior
// =========================================================

const form = document.getElementById("lookupForm");
const submitBtn = document.getElementById("submitBtn");
const statusText = document.getElementById("statusText");
const summary = document.getElementById("summary");
const results = document.getElementById("results");
const caveats = document.getElementById("caveats");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = buildPayload();
  setLoading(true);
  clearOutput();

  try {
    const response = await fetch("/api/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Lookup failed.");
    }

    renderSummary(data);
    renderResults(data.ranked_parts || []);
    renderCaveats(data.caveats || []);
  } catch (error) {
    results.innerHTML = `<div class="alert alert-danger rounded-4">${escapeHtml(error.message)}</div>`;
  } finally {
    setLoading(false);
  }
});

function buildPayload() {
  const vin = document.getElementById("vin").value.trim();
  const year = document.getElementById("year").value.trim();
  const make = document.getElementById("make").value.trim();
  const model = document.getElementById("model").value.trim();
  const topN = Number(document.getElementById("topN").value || 10);

  return {
    vin: vin || null,
    year: year ? Number(year) : null,
    make: make || null,
    model: model || null,
    top_n: topN,
    max_pages_per_search: 2,
  };
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  statusText.textContent = isLoading
    ? "Running scrape and scoring pipeline. This is not instant coffee."
    : "";
}

function clearOutput() {
  summary.innerHTML = "";
  results.innerHTML = "";
  caveats.innerHTML = "";
}

function renderSummary(data) {
  const v = data.vehicle || {};
  summary.innerHTML = `
    <div class="alert alert-info rounded-4">
      <strong>${escapeHtml(v.year)} ${escapeHtml(v.make)} ${escapeHtml(v.model)}</strong>
      <span class="text-secondary"> | Run ID: ${escapeHtml(data.run_id)}</span>
    </div>
  `;
}

function renderResults(parts) {
  if (!parts.length) {
    results.innerHTML = `<div class="alert alert-warning rounded-4">No ranked parts returned.</div>`;
    return;
  }

  const rows = parts.map((part) => {
    return `
      <tr>
        <td class="fw-semibold">${escapeHtml(part.vehicle_rank)}</td>
        <td>${escapeHtml(part.part)}</td>
        <td>${formatMoney(part.median_sold_price)}</td>
        <td>${escapeHtml(part.sold_count)}</td>
        <td>${escapeHtml(part.active_count)}</td>
        <td>${formatPercent(part.str)}</td>
        <td>${escapeHtml(part.confidence_score)}</td>
        <td class="fw-semibold">${escapeHtml(part.opportunity_score)}</td>
      </tr>
    `;
  }).join("");

  results.innerHTML = `
    <div class="card shadow-sm rounded-4">
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Part</th>
                <th>Median Sold Price</th>
                <th>Sold</th>
                <th>Active</th>
                <th>STR</th>
                <th>Confidence</th>
                <th>Opportunity</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function renderCaveats(items) {
  if (!items.length) return;

  caveats.innerHTML = `
    <div class="small text-secondary">
      <div class="fw-semibold mb-1">Reality checks</div>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function formatMoney(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return "";
  return number.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function formatPercent(value) {
  const number = Number(value);
  if (Number.isNaN(number)) return "";
  return `${(number * 100).toFixed(1)}%`;
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
