import { onReady, safeJsonParse } from "./modules/dom.js";


onReady(() => {
  if (!window.Chart) return;
  const dataNode = document.getElementById("admin-chart-data");
  if (!dataNode) return;

  const data = safeJsonParse(dataNode.textContent || "{}", {});
  if (!data.labels) return;

  const textColor = getComputedStyle(document.documentElement).getPropertyValue("--text").trim();
  const muted = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
  const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
  const accent2 = getComputedStyle(document.documentElement).getPropertyValue("--accent-2").trim();
  const accent3 = getComputedStyle(document.documentElement).getPropertyValue("--accent-3").trim();

  window.Chart.defaults.color = muted;
  window.Chart.defaults.font.family = "Manrope";

  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: textColor, boxWidth: 12 },
      },
    },
    scales: {
      x: {
        ticks: { color: muted },
        grid: { color: "rgba(255,255,255,0.05)" },
      },
      y: {
        ticks: { color: muted },
        grid: { color: "rgba(255,255,255,0.05)" },
      },
    },
  };

  const growthEl = document.getElementById("growthChart");
  if (growthEl) {
    new window.Chart(growthEl, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          { label: "Inquiries", data: data.inquiries, borderColor: accent, backgroundColor: "rgba(30,232,255,.12)", tension: 0.35, fill: true },
          { label: "Applications", data: data.applications, borderColor: accent2, tension: 0.35 },
          { label: "RSVPs", data: data.rsvps, borderColor: accent3, tension: 0.35 },
          { label: "Chatbot", data: data.chatbot, borderColor: "#ffcc66", tension: 0.35 },
          { label: "Successful Logins", data: data.logins, borderColor: "#ff89b5", tension: 0.35 },
        ],
      },
      options: baseOptions,
    });
  }

  const serviceEl = document.getElementById("serviceChart");
  if (serviceEl) {
    new window.Chart(serviceEl, {
      type: "bar",
      data: {
        labels: data.services.labels,
        datasets: [{ label: "Interest", data: data.services.values, backgroundColor: accent }],
      },
      options: {
        ...baseOptions,
        plugins: { legend: { display: false } },
      },
    });
  }

  const countryEl = document.getElementById("countryChart");
  if (countryEl) {
    new window.Chart(countryEl, {
      type: "doughnut",
      data: {
        labels: data.countries.labels,
        datasets: [{ data: data.countries.values, backgroundColor: [accent, accent2, accent3, "#ffcc66", "#5fd4ff", "#87a8ff"] }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
      },
    });
  }
});
