document.querySelectorAll(".valid-measurement-btn").forEach(button => {
    button.addEventListener("click", function() {
        let entryId = this.getAttribute("data-entry-id");

        fetch(`/measurement/${entryId}/toggle_is_valid`, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"), // CSRF token for security
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.is_valid) {
                    this.classList.remove("btn-danger")
                    this.classList.add("btn-success")
                    this.innerHTML = '<i class="bi bi-check"></i>';
                } else {
                    this.classList.remove("btn-success")
                    this.classList.add("btn-danger")
                    this.innerHTML = '<i class="bi bi-x"></i>'
                }
            }
        })
        .catch(error => console.error("Error:", error));
    });
});

document.getElementById("validate-all-measurements-btn").addEventListener("click", function() {
    document.querySelectorAll(".valid-measurement-btn.btn-danger").forEach(button => {
        button.click();
    });
});

document.getElementById("invalidate-all-measurements-btn").addEventListener("click", function() {
    document.querySelectorAll(".valid-measurement-btn.btn-success").forEach(button => {
        button.click();
    });
});
