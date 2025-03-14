document.getElementById("starred-badge").addEventListener("click", function() {
    let entryId = this.getAttribute("data-entry-id");

    fetch(`/toggle_star_exp_run/${entryId}`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"), // CSRF token for security
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.starred) {
                this.classList.remove("btn-secondary")
                this.classList.add("btn-warning")
                this.innerHTML = 'Starred<i class="bi bi-star-fill ms-2"></i>';
            } else {
                this.classList.remove("btn-warning")
                this.classList.add("btn-secondary")
                this.innerHTML = 'Not starred<i class="bi bi-star ms-2"></i>'
            }
        }
    })
    .catch(error => console.error("Error:", error));
});