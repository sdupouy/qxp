document.getElementById("warmup-btn").addEventListener("click", function() {
    let entryId = this.getAttribute("data-entry-id");

    fetch(`/warmup/${entryId}`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"), // CSRF token for security
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        }
    })
    .catch(error => console.error("Error:", error));
});