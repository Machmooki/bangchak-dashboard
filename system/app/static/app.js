const state = {
  socket: null,
  reconnectTimer: null,
  pingTimer: null,
  lastPayload: null,
  activeView: "dashboard",
  activeTab: "connected",
};

const elements = {
  pageShell: document.querySelector(".page-shell"),
  summaryPanel: document.getElementById("summary-panel"),
  metricTabs: document.getElementById("metric-tabs"),
  detailTitle: document.getElementById("detail-title"),
  detailNote: document.getElementById("detail-note"),
  detailGrid: document.getElementById("detail-grid"),
  leadDonut: document.getElementById("lead-donut"),
  leadLegend: document.getElementById("lead-legend"),
  syncNote: document.getElementById("sync-note"),
  buLegend: document.getElementById("bu-legend"),
  buChart: document.getElementById("bu-chart"),
  divisionLegend: document.getElementById("division-legend"),
  divisionChart: document.getElementById("division-chart"),
  navLinks: Array.from(document.querySelectorAll("[data-view-link]")),
  pageViews: Array.from(document.querySelectorAll("[data-view]")),
};

const palette = {
  connected: "#25724a",
  reconnect: "#84bd00",
  notCalled: "#ffb81c",
  closedBusiness: "#f96015",
  processed: "#a9d18e",
  pending: "#ffd966",
  track: "#e4e4e4",
  header: "#1d623a",
};

const divisionOrder = ["FCD", "CID", "LCD", "AVD", "MRD", "ASD", "LBD", "ILD"];
const iconBasePath = "/static/assets/Icon-badge/";

const iconFiles = {
  totalLeads: "ICON Total Leads.svg",
  processedTop: "ICON Processed Top.svg",
  notProcessedTop: "ICON Not Processed Top.svg",
  fleet_card: "ICON Fleet Card.svg",
  clean_oil: "ICON Bulk.svg",
  lube: "ICON Lube.svg",
  marine: "ICON Marine.svg",
  contact_number_unreachable: "ICON Contact number unreach.svg",
  unable_to_reach_coordinator: "ICON Unable reach coordinator.svg",
  customer_not_interested: "ICON Customer not interest.svg",
  not_processed: "ICON Not processed.svg",
  unable_to_find_contact_number: "ICON Unable find contact.svg",
  business_closed: "ICON Closed.svg",
};

function formatNumber(value) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function formatCompact(value) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 1,
    notation: Number(value || 0) >= 100000 ? "compact" : "standard",
  }).format(Number(value || 0));
}

function formatPercent(value) {
  return `${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value || 0) * 100)}%`;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(value, max));
}

function iconSrc(fileName) {
  return `${iconBasePath}${encodeURIComponent(fileName)}`;
}

function iconImg(fileName, className) {
  return `<img class="${className}" src="${iconSrc(fileName)}" alt="" aria-hidden="true" />`;
}

function flowValue(data, key) {
  const item = asArray(data?.overview?.lead_flow).find((row) => row.key === key);
  return Number(item?.value || 0);
}

function detailItems(data, key) {
  return asArray(data?.details?.[key]?.items);
}

function detailTitle(data, key) {
  return data?.details?.[key]?.title || "";
}

function detailIconFile(item) {
  if (iconFiles[item.key]) {
    return iconFiles[item.key];
  }
  return {
    fleet: iconFiles.fleet_card,
    bulk: iconFiles.clean_oil,
    lube: iconFiles.lube,
    marine: iconFiles.marine,
    green: iconFiles.not_processed,
    yellow: iconFiles.contact_number_unreachable,
    orange: iconFiles.customer_not_interested,
    blue: iconFiles.unable_to_reach_coordinator,
  }[item.tone] || iconFiles.not_processed;
}

function formatDetailLabel(label) {
  const text = String(label || "");
  if (text.includes("/")) {
    return text
      .split("/")
      .map((part) => escapeHtml(part.trim()))
      .filter(Boolean)
      .join("/<wbr>");
  }
  return escapeHtml(text);
}

function colorForTone(tone) {
  return {
    fleet: "#37b74a",
    bulk: "#ffb81c",
    lube: "#f96015",
    marine: "#005b99",
    green: "#84bd00",
    yellow: "#ffb81c",
    orange: "#f96015",
    blue: "#005b99",
  }[tone] || palette.header;
}

function backgroundForTone(tone) {
  return {
    fleet: "rgba(132, 189, 0, 0.14)",
    bulk: "rgba(255, 184, 28, 0.2)",
    lube: "rgba(249, 96, 21, 0.15)",
    marine: "rgba(0, 91, 153, 0.18)",
    green: "rgba(132, 189, 0, 0.14)",
    yellow: "rgba(255, 184, 28, 0.22)",
    orange: "rgba(249, 96, 21, 0.14)",
    blue: "rgba(0, 91, 153, 0.16)",
  }[tone] || "rgba(29, 98, 58, 0.12)";
}

function displayBuName(name) {
  return String(name || "").replace(/^CB(\d)$/i, "CB $1");
}

function normalizePerformanceRows(rows, labelKey) {
  return asArray(rows).map((row) => {
    const processed = Number(row.processed || 0);
    const notProcessed = Number(row.not_processed || row.not_called || 0);
    const total = Number(row.total_leads || processed + notProcessed || 0);
    return {
      label: labelKey === "name" ? displayBuName(row.name) : row.division,
      total,
      processed,
      notProcessed,
      processedRate: total > 0 ? processed / total : 0,
      notProcessedRate: total > 0 ? notProcessed / total : 0,
    };
  });
}

function buildModel(payload) {
  const data = payload.data || {};
  const summary = data.summary || {};
  const totalLeads = Number(summary.total_leads || data?.overview?.lead_flow_root?.value || 0);
  const processed = Number(summary.processed || data?.business_units?.total?.processed || 0);
  const notProcessed = Number(summary.not_processed || data?.business_units?.total?.not_processed || 0);

  return {
    totalLeads,
    processed,
    processedRate: Number(summary.processed_rate || 0),
    notProcessed,
    notProcessedRate: Number(summary.not_processed_rate || 0),
    tabs: [
      { id: "connected", title: "Called", subtitle: "(Connected)", value: flowValue(data, "connected") },
      { id: "reconnect", title: "Called", subtitle: "(Reconnect)", value: flowValue(data, "reconnect") },
      { id: "not_called", title: "Not called", subtitle: "", value: flowValue(data, "not_called") },
      { id: "business_closed", title: "Closed", subtitle: "", value: flowValue(data, "business_closed") },
    ],
    donutSegments: [
      { key: "connected", label: "Called", sublabel: "(Connected)", value: flowValue(data, "connected"), color: palette.connected },
      { key: "reconnect", label: "Called", sublabel: "(Reconnect)", value: flowValue(data, "reconnect"), color: palette.reconnect },
      { key: "not_called", label: "Not called", sublabel: "", value: flowValue(data, "not_called"), color: palette.notCalled },
      { key: "business_closed", label: "Closed", sublabel: "", value: flowValue(data, "business_closed"), color: palette.closedBusiness },
    ],
    details: {
      connected: {
        title: detailTitle(data, "connected"),
        items: detailItems(data, "connected").map((item) => ({ ...item, cardType: "product" })),
      },
      reconnect: {
        title: detailTitle(data, "reconnect"),
        items: detailItems(data, "reconnect").map((item) => ({ ...item, cardType: "reason" })),
      },
      not_called: {
        title: detailTitle(data, "not_called"),
        items: detailItems(data, "not_called").map((item) => ({ ...item, cardType: "reason" })),
      },
      business_closed: {
        title: detailTitle(data, "business_closed"),
        items: detailItems(data, "business_closed").map((item) => ({ ...item, cardType: "reason" })),
      },
    },
    buRows: normalizePerformanceRows(data?.business_units?.items, "name"),
    divisionRows: normalizePerformanceRows(
      divisionOrder
        .map((division) => asArray(data.divisions).find((row) => row.division === division))
        .filter(Boolean),
      "division",
    ),
  };
}

function renderSummaryPanel(model) {
  elements.summaryPanel.innerHTML = `
    <div class="summary-primary">
      <div class="summary-icon">${iconImg(iconFiles.totalLeads, "summary-icon-img")}</div>
      <div class="summary-total">
        <div class="summary-total-value">${formatNumber(model.totalLeads)}</div>
        <div class="summary-total-label">Total Leads</div>
      </div>
    </div>
    <article class="summary-stat summary-stat--processed">
      <div class="summary-stat-icon">${iconImg(iconFiles.processedTop, "summary-stat-icon-img")}</div>
      <div class="summary-stat-copy">
        <div class="summary-stat-label">PROCESSED</div>
        <div class="summary-stat-row">
          <div class="summary-stat-value">${formatNumber(model.processed)}</div>
          <div class="summary-stat-rate">${formatPercent(model.processedRate)}</div>
        </div>
        <div class="summary-progress"><span style="width:${Math.min(model.processedRate * 100, 100)}%"></span></div>
      </div>
    </article>
    <article class="summary-stat summary-stat--pending">
      <div class="summary-stat-icon">${iconImg(iconFiles.notProcessedTop, "summary-stat-icon-img")}</div>
      <div class="summary-stat-copy">
        <div class="summary-stat-label">NOT PROCESSED</div>
        <div class="summary-stat-row">
          <div class="summary-stat-value">${formatNumber(model.notProcessed)}</div>
          <div class="summary-stat-rate">${formatPercent(model.notProcessedRate)}</div>
        </div>
        <div class="summary-progress"><span style="width:${Math.min(model.notProcessedRate * 100, 100)}%"></span></div>
      </div>
    </article>
  `;
}

function renderTabs(model) {
  elements.metricTabs.innerHTML = model.tabs
    .map((tab) => {
      const head = `<span class="metric-tab-title">${escapeHtml(tab.title)}</span>${tab.subtitle ? `<span class="metric-tab-subtitle">${escapeHtml(tab.subtitle)}</span>` : ""}`;
      return `
        <button class="metric-tab ${state.activeTab === tab.id ? "is-active" : ""}" data-tab="${escapeHtml(tab.id)}" type="button">
          <span class="metric-tab-head">${head}</span>
          <span class="metric-tab-value">${formatNumber(tab.value)}</span>
        </button>
      `;
    })
    .join("");

  elements.metricTabs.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTab = button.dataset.tab;
      renderTabs(model);
      renderDetail(model.details[state.activeTab]);
    });
  });
}

function renderDetail(detail) {
  const variant = state.activeTab || "connected";

  elements.detailTitle.innerHTML = escapeHtml(detail.title).replace(
    "PRODUCT OPPORTUNITY ANALYSIS",
    '<span class="detail-title-highlight">PRODUCT OPPORTUNITY ANALYSIS</span>',
  );
  elements.detailNote.textContent = "";
  elements.detailGrid.className = `detail-grid detail-grid--${variant}`;

  const detailTotal =
    variant === "not_called" || variant === "reconnect" || variant === "business_closed"
      ? detail.items.reduce((total, item) => total + Number(item.value || 0), 0)
      : 0;

  elements.detailGrid.innerHTML = detail.items
    .map((item) => {
      const color = colorForTone(item.tone);
      const bg = backgroundForTone(item.tone);
      const progressRate = detailTotal > 0 ? Number(item.value || 0) / detailTotal : 0;
      const progressWidth = clampNumber(progressRate * 100, 0, 100);
      const progressMarkup =
        variant === "not_called" || variant === "reconnect" || variant === "business_closed"
          ? `
            <div class="detail-card-progress" style="--detail-color:${color};">
              <div class="detail-card-progress-track">
                <span style="width:${progressWidth}%;"></span>
              </div>
              <div class="detail-card-progress-percent">${formatPercent(progressRate)}</div>
            </div>
          `
          : "";
      const hasProgressClass =
        variant === "not_called" || variant === "reconnect" || variant === "business_closed"
          ? " detail-card--has-progress"
          : "";
      return `
        <article class="detail-card detail-card--${item.cardType} detail-card--${variant}${hasProgressClass}">
          <div class="detail-icon" style="background:${bg};">
            ${iconImg(detailIconFile(item), "detail-icon-img")}
          </div>
          <div class="detail-card-title" ${item.cardType === "product" ? `style="color:${color};"` : ""}>${formatDetailLabel(item.label)}</div>
          <div class="detail-card-number">${formatNumber(item.value)}</div>
          ${progressMarkup}
        </article>
      `;
    })
    .join("");
}

function arrangeDonutBadges(candidates) {
  const minDistance = 44;
  for (let iteration = 0; iteration < 10; iteration += 1) {
    for (let i = 0; i < candidates.length; i += 1) {
      for (let j = i + 1; j < candidates.length; j += 1) {
        const a = candidates[i];
        const b = candidates[j];
        const deltaX = a.x - b.x;
        const deltaY = a.y - b.y;
        const distance = Math.hypot(deltaX, deltaY) || 1;
        if (distance >= minDistance) {
          continue;
        }
        const push = (minDistance - distance) / 2;
        const unitX = deltaX / distance;
        const unitY = deltaY / distance;
        a.x += unitX * push;
        a.y += unitY * push;
        b.x -= unitX * push;
        b.y -= unitY * push;
      }
    }

    candidates.forEach((candidate) => {
      const deltaX = candidate.x - 150;
      const deltaY = candidate.y - 150;
      const distanceFromCenter = Math.hypot(deltaX, deltaY) || 1;
      if (distanceFromCenter < 136) {
        candidate.x = 150 + (deltaX / distanceFromCenter) * 136;
        candidate.y = 150 + (deltaY / distanceFromCenter) * 136;
      }
      candidate.x = clampNumber(candidate.x, 16, 284);
      candidate.y = clampNumber(candidate.y, 16, 284);
    });
  }
  return candidates;
}

function renderLeadDonut(model) {
  const total = Math.max(model.totalLeads, 1);
  const segmentValues = model.donutSegments.map((segment) => Math.max(Number(segment.value || 0), 0));
  const segmentTotal = segmentValues.reduce((sum, value) => sum + value, 0);
  const chartTotal = Math.max(total, segmentTotal, 1);
  const radius = 112;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  const activeSegmentCount = segmentValues.filter((value) => value > 0).length;
  const segmentGap = activeSegmentCount > 1 ? 4 : 0;

  const circles = model.donutSegments
    .map((segment, index) => {
      const share = segmentValues[index] / chartTotal;
      const rawLength = share * circumference;
      const length = Math.max(rawLength - segmentGap, 0);
      const markup = `
        <circle
          class="donut-segment"
          cx="150"
          cy="150"
          r="${radius}"
          stroke="${segment.color}"
          stroke-dasharray="${length} ${Math.max(circumference - length, 0)}"
          stroke-dashoffset="${-(offset + segmentGap / 2)}"
        ></circle>
      `;
      offset += rawLength;
      return markup;
    })
    .join("");

  const badgeCandidates = [];
  let running = 0;
  model.donutSegments.forEach((segment, index) => {
    const share = segmentValues[index] / chartTotal;
    if (share < 0.01) {
      running += share;
      return;
    }
    const angle = (running + share / 2) * Math.PI * 2 - Math.PI / 2;
    const badgeRadius = 140;
    badgeCandidates.push({
      x: 150 + Math.cos(angle) * badgeRadius,
      y: 150 + Math.sin(angle) * badgeRadius,
      share,
    });
    running += share;
  });
  const badges = arrangeDonutBadges(badgeCandidates).map((badge) => {
    const left = (badge.x / 300) * 100;
    const top = (badge.y / 300) * 100;
    return `<div class="donut-badge" style="left:${left}%; top:${top}%;">${formatPercent(badge.share)}</div>`;
  });

  elements.leadDonut.innerHTML = `
    <div class="donut-wrap">
      <svg viewBox="0 0 300 300" aria-hidden="true">
        <circle class="donut-track" cx="150" cy="150" r="${radius}"></circle>
        ${circles}
      </svg>
      <div class="donut-center">
        <div>
          <div class="donut-center-label">Total Count</div>
          <div class="donut-center-value">${formatNumber(model.totalLeads)}</div>
        </div>
      </div>
      ${badges.join("")}
    </div>
  `;

  const legendOrder = ["connected", "not_called", "reconnect", "business_closed"];
  elements.leadLegend.innerHTML = legendOrder
    .map((key) => model.donutSegments.find((segment) => segment.key === key))
    .filter(Boolean)
    .map(
      (segment) => `
        <div class="legend-entry">
          <span class="legend-dot" style="background:${segment.color}"></span>
          <div>
            <div class="legend-text">${escapeHtml(segment.label)}</div>
            <div class="legend-subtext">${escapeHtml(segment.sublabel || "")}</div>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderPerformanceLegend(target) {
  target.innerHTML = `
    <span class="performance-legend-item"><span class="performance-legend-dot performance-legend-dot--processed"></span>Proceeded</span>
    <span class="performance-legend-item"><span class="performance-legend-dot performance-legend-dot--pending"></span>Not Proceeded</span>
  `;
}

function niceAxisMax(maxValue) {
  if (maxValue <= 0) return 100;
  const step = maxValue > 3000 ? 1000 : maxValue > 1200 ? 500 : 250;
  return Math.ceil(maxValue / step) * step;
}

function renderPerformanceChart(target, rows) {
  const maxTotal = niceAxisMax(Math.max(...rows.map((row) => row.total), 0));
  const ticks = [maxTotal, maxTotal * 0.75, maxTotal * 0.5, maxTotal * 0.25, 0];
  const barMarkup = rows
    .map((row) => {
      const totalRatio = maxTotal > 0 ? row.total / maxTotal : 0;
      const totalPct = Math.max(totalRatio * 100, row.total > 0 ? 3 : 0);
      const processedPct = row.total > 0 ? (row.processed / row.total) * 100 : 0;
      const pendingPct = row.total > 0 ? (row.notProcessed / row.total) * 100 : 0;
      const processedVisiblePct = (totalPct * processedPct) / 100;
      const pendingVisiblePct = (totalPct * pendingPct) / 100;
      const showProcessedLabel = processedPct >= 12 && processedVisiblePct >= 5;
      const showPendingLabel = pendingPct >= 12 && pendingVisiblePct >= 5;
      return `
        <article class="stacked-column">
          <div class="stacked-bar" style="height:${totalPct}%;" title="${escapeHtml(row.label)} total ${formatNumber(row.total)}">
            <div class="stacked-segment stacked-segment--pending" style="height:${pendingPct}%;">
              ${showPendingLabel ? `<span>${formatPercent(row.notProcessedRate)}</span>` : ""}
            </div>
            <div class="stacked-segment stacked-segment--processed" style="height:${processedPct}%;">
              ${showProcessedLabel ? `<span>${formatPercent(row.processedRate)}</span>` : ""}
            </div>
          </div>
          <div class="stacked-label">${escapeHtml(row.label)}</div>
        </article>
      `;
    })
    .join("");

  target.innerHTML = `
    <div class="chart-y-axis">
      ${ticks.map((tick) => `<span>${formatCompact(tick)}</span>`).join("")}
    </div>
    <div class="chart-plot">
      <div class="chart-grid-lines" aria-hidden="true"></div>
      <div class="chart-bars" style="grid-template-columns: repeat(${Math.max(rows.length, 1)}, minmax(54px, 1fr));">
        ${barMarkup}
      </div>
    </div>
  `;
}

function renderDashboard(payload) {
  state.lastPayload = payload;
  const model = buildModel(payload);

  if (!model.details[state.activeTab]) {
    state.activeTab = "connected";
  }

  renderSummaryPanel(model);
  renderTabs(model);
  renderDetail(model.details[state.activeTab]);
  renderLeadDonut(model);
  renderPerformanceLegend(elements.buLegend);
  renderPerformanceChart(elements.buChart, model.buRows);
  renderPerformanceLegend(elements.divisionLegend);
  renderPerformanceChart(elements.divisionChart, model.divisionRows);

  elements.syncNote.textContent = `Live from ${payload.meta.source_file} | Refreshed ${formatDate(payload.meta.refreshed_at)} | Source updated ${formatDate(payload.meta.file_modified_at)}`;
}

function renderView() {
  if (elements.pageShell) {
    elements.pageShell.dataset.view = state.activeView;
  }
  elements.pageViews.forEach((section) => {
    section.classList.toggle("page-view--active", section.dataset.view === state.activeView);
  });
  elements.navLinks.forEach((link) => {
    link.classList.toggle("topnav-item--active", link.dataset.viewLink === state.activeView);
  });
}

function bindViewNavigation() {
  const hashView = window.location.hash.replace("#", "").trim();
  if (hashView === "analytic" || hashView === "dashboard") {
    state.activeView = hashView;
  }
  renderView();

  elements.navLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const nextView = link.dataset.viewLink;
      if (!nextView || nextView === state.activeView) {
        return;
      }
      state.activeView = nextView;
      window.location.hash = nextView;
      renderView();
    });
  });

  window.addEventListener("hashchange", () => {
    const nextView = window.location.hash.replace("#", "").trim();
    if (!nextView || nextView === state.activeView) {
      return;
    }
    if (nextView === "analytic" || nextView === "dashboard") {
      state.activeView = nextView;
      renderView();
    }
  });
}

async function fetchDashboard() {
  const response = await fetch("/api/dashboard", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Dashboard request failed with ${response.status}`);
  }
  renderDashboard(await response.json());
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/dashboard`);
  state.socket = socket;

  socket.addEventListener("open", () => {
    window.clearInterval(state.pingTimer);
    state.pingTimer = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 20000);
  });

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.payload && (message.type === "dashboard.snapshot" || message.type === "dashboard.updated")) {
      renderDashboard(message.payload);
      return;
    }
    if (message.type === "dashboard.error") {
      elements.syncNote.textContent = message.payload.message;
    }
  });

  socket.addEventListener("close", () => {
    window.clearInterval(state.pingTimer);
    state.reconnectTimer = window.setTimeout(connectWebSocket, 2500);
  });
}

fetchDashboard().catch((error) => {
  console.error(error);
  elements.syncNote.textContent = error.message;
});
bindViewNavigation();
connectWebSocket();
