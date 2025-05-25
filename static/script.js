async function sendQuery() {
    const query = document.getElementById("query").value;
    const responseBox = document.getElementById("response");
    responseBox.innerHTML = "Processing...";

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ query })
        });

        const data = await res.json();
        if (res.ok) {
            const rawMarkdown = data.answer || "";
            const html = marked.parse(rawMarkdown);  // Render Markdown to HTML
            responseBox.innerHTML = `<strong>Answer:</strong><br>${html}`;
        } else {
            responseBox.innerHTML = `<span style="color:red;">Error: ${data.detail}</span>`;
        }
    } catch (err) {
        console.error(err);
        responseBox.innerHTML = `<span style="color:red;">Network or server error</span>`;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const textarea = document.querySelector("textarea");

    function autoResize() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
    }

    textarea.addEventListener("input", autoResize);
});
