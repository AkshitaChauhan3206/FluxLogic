document.addEventListener("DOMContentLoaded", () => {
  const sales = window.FLUX_SALES || [];
  const top = window.FLUX_TOP || [];
  const expense = window.FLUX_EXPENSE || [];

  const salesLabels = sales.map(x => x.day);
  const salesValues = sales.map(x => Number(x.total));

  const topLabels = top.map(x => x.name);
  const topValues = top.map(x => Number(x.profit));

  const expLabels = expense.map(x => x.category);
  const expValues = expense.map(x => Number(x.total));

  const salesCtx = document.getElementById("salesChart");
  if (salesCtx) {
    new Chart(salesCtx, {
      type: "line",
      data: {
        labels: salesLabels,
        datasets: [{
          label: "Sales",
          data: salesValues,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56,189,248,0.15)",
          tension: 0.35,
          fill: true
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#e2e8f0" } } },
        scales: {
          x: { ticks: { color: "#cbd5e1" } },
          y: { ticks: { color: "#cbd5e1" } }
        }
      }
    });
  }

  const topCtx = document.getElementById("topProductsChart");
  if (topCtx) {
    new Chart(topCtx, {
      type: "bar",
      data: {
        labels: topLabels,
        datasets: [{
          label: "Profit",
          data: topValues,
          backgroundColor: "#4ade80"
        }]
      },
      options: {
        responsive: true,
        indexAxis: "y",
        plugins: { legend: { labels: { color: "#e2e8f0" } } },
        scales: {
          x: { ticks: { color: "#cbd5e1" } },
          y: { ticks: { color: "#cbd5e1" } }
        }
      }
    });
  }

  const expCtx = document.getElementById("expenseChart");
  if (expCtx) {
    new Chart(expCtx, {
      type: "doughnut",
      data: {
        labels: expLabels,
        datasets: [{
          data: expValues,
          backgroundColor: ["#38bdf8", "#4ade80", "#f97316", "#a78bfa", "#f43f5e"]
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#e2e8f0" } } }
      }
    });
  }
});