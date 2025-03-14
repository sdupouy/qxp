document.getElementById("edit-comment-btn").addEventListener("click", function() {
    this.classList.add("d-none");
    document.getElementById("comment-text").classList.add("d-none");
    document.getElementById("comment-form").classList.remove("d-none");
});