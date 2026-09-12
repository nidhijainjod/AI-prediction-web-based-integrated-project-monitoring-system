// Global jQuery AJAX setup: attach CSRF token to every mutating request.
$(function () {
    const csrfToken = $('meta[name="csrf-token"]').attr("content");
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrfToken);
            }
        },
    });

    // auto-dismiss alerts after a few seconds
    setTimeout(function () {
        $(".alert").alert("close");
    }, 6000);
});
