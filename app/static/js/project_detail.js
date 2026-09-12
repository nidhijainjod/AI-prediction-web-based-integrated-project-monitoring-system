$(function () {
    const trendCtx = document.getElementById("trendChart");
    if (trendCtx && typeof TREND_DATA !== "undefined") {
        new Chart(trendCtx, {
            type: "line",
            data: {
                labels: TREND_DATA.labels,
                datasets: [
                    {
                        label: "Planned cost pace",
                        data: TREND_DATA.planned,
                        borderColor: "#8fa8f7",
                        tension: 0.25,
                    },
                    {
                        label: "Actual cost",
                        data: TREND_DATA.actual,
                        borderColor: "#d84315",
                        tension: 0.25,
                    },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: "bottom" } } },
        });
    }
});
