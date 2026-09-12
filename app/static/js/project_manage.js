$(function () {
    const RISK_BADGE_CLASS = { Low: "success", Medium: "warning", High: "danger", Critical: "dark" };

    function applyProjectPayload(project) {
        $("#progressVal").text(Math.round(project.percent_complete || 0) + "%");
        $("#predictedCostVal").text(formatCurrency(project.predicted_final_cost));
        $("#overrunVal")
            .text((project.predicted_overrun_pct || 0).toFixed(1) + "% vs plan")
            .toggleClass("text-danger", (project.predicted_overrun_pct || 0) > 0)
            .toggleClass("text-success", (project.predicted_overrun_pct || 0) <= 0);
        $("#delayVal").text(Math.round(project.predicted_delay_days || 0) + "d");

        const level = project.risk_level || "N/A";
        const cls = RISK_BADGE_CLASS[level] || "secondary";
        $("#riskBadge")
            .attr("class", "badge text-bg-" + cls + " fs-6 mb-2")
            .html(level + " Risk (<span id=\"riskScoreVal\">" + (project.risk_score || 0) + "</span>/100)");

        const $reasons = $("#reasonsList").empty();
        (project.reasons || []).forEach(function (r) {
            $reasons.append(
                '<li class="list-group-item small"><i class="fa-solid fa-circle-exclamation text-warning me-1"></i> ' + r + "</li>"
            );
        });
        const $recs = $("#recommendationsList").empty();
        (project.recommendations || []).forEach(function (r) {
            $recs.append(
                '<li class="list-group-item small"><i class="fa-solid fa-lightbulb text-success me-1"></i> ' + r + "</li>"
            );
        });
    }

    function formatCurrency(value) {
        value = value || 0;
        return "$" + Math.round(value).toLocaleString();
    }

    function pushTaskUpdate($el, payload) {
        const taskId = $el.data("task-id");
        $.ajax({
            url: "/api/tasks/" + taskId + "/quick-update",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify(payload),
            success: function (resp) {
                applyProjectPayload(resp.project);
            },
            error: function () {
                alert("Could not update task. Please try again.");
            },
        });
    }

    $(".task-status-select").on("change", function () {
        pushTaskUpdate($(this), { status: $(this).val() });
        const $row = $(this).closest("tr");
        if ($(this).val() === "Completed") {
            $row.find(".task-progress-range").val(100);
            $row.find(".task-progress-label").text("100%");
        }
    });

    $(".task-progress-range").on("input", function () {
        $(this).closest("tr").find(".task-progress-label").text($(this).val() + "%");
    });

    $(".task-progress-range").on("change", function () {
        pushTaskUpdate($(this), { percent_complete: $(this).val() });
    });

    $("#recalcBtn").on("click", function () {
        const $btn = $(this);
        const projectId = $btn.data("project-id");
        $btn.prop("disabled", true).html('<i class="fa-solid fa-spinner fa-spin"></i> Running...');
        $.ajax({
            url: "/api/projects/" + projectId + "/recalculate",
            method: "POST",
            success: function (resp) {
                applyProjectPayload(resp);
                $btn.prop("disabled", false).html('<i class="fa-solid fa-rotate"></i> Re-run AI');
            },
            error: function () {
                alert("Could not refresh AI prediction.");
                $btn.prop("disabled", false).html('<i class="fa-solid fa-rotate"></i> Re-run AI');
            },
        });
    });
});
