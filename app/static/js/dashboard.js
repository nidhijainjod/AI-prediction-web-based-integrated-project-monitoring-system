$(function () {
    // --- Risk distribution donut ---
    const riskCtx = document.getElementById("riskChart");
    if (riskCtx && typeof RISK_DATA !== "undefined") {
        new Chart(riskCtx, {
            type: "doughnut",
            data: {
                labels: RISK_DATA.labels,
                datasets: [{ data: RISK_DATA.values, backgroundColor: RISK_DATA.colors }],
            },
            options: { plugins: { legend: { position: "bottom" } } },
        });
    }

    // --- Planned vs predicted cost bar chart ---
    const costCtx = document.getElementById("costChart");
    if (costCtx && typeof COST_DATA !== "undefined") {
        new Chart(costCtx, {
            type: "bar",
            data: {
                labels: COST_DATA.labels,
                datasets: [
                    { label: "Planned Budget", data: COST_DATA.planned, backgroundColor: "#8fa8f7" },
                    { label: "AI-Predicted Final Cost", data: COST_DATA.predicted, backgroundColor: "#d84315" },
                ],
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
                plugins: { legend: { position: "bottom" } },
            },
        });
    }

    // --- Client-side search / filter / sort of the project summary table ---
    const $rows = $("#projectTable tbody tr");

    function applyFilters() {
        const search = $("#searchInput").val().toLowerCase();
        const risk = $("#riskFilter").val();
        const status = $("#statusFilter").val();
        let visibleCount = 0;

        $rows.each(function () {
            const $row = $(this);
            const matchesSearch =
                !search ||
                $row.data("name").toString().includes(search) ||
                $row.data("manager").toString().includes(search);
            const matchesRisk = !risk || $row.data("risk") === risk;
            const matchesStatus = !status || $row.data("status") === status;
            const visible = matchesSearch && matchesRisk && matchesStatus;
            $row.toggle(visible);
            if (visible) visibleCount++;
        });

        $("#noResults").toggle(visibleCount === 0);
    }

    $("#searchInput, #riskFilter, #statusFilter").on("input change", applyFilters);

    // --- Sortable columns ---
    let sortDir = {};
    $("th.sortable").on("click", function () {
        const key = $(this).data("sort");
        sortDir[key] = !sortDir[key];
        const dir = sortDir[key] ? 1 : -1;
        const keyMap = {
            name: "name",
            manager: "manager",
            status: "status",
            percent: "percent",
            budget: "budget",
            predicted_cost: "predicted_cost",
            overrun: "overrun",
            delay: "delay",
            risk: "risk_score",
        };
        const dataKey = keyMap[key] || key;
        const $tbody = $("#projectTable tbody");
        const rows = $tbody.find("tr").get();

        rows.sort(function (a, b) {
            let av = $(a).data(dataKey);
            let bv = $(b).data(dataKey);
            if (typeof av === "string") av = av.toLowerCase();
            if (typeof bv === "string") bv = bv.toLowerCase();
            if (av < bv) return -1 * dir;
            if (av > bv) return 1 * dir;
            return 0;
        });

        $.each(rows, function (i, row) {
            $tbody.append(row);
        });
    });
});
