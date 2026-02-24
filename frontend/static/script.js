async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (response.ok) {
        localStorage.setItem("token", data.access_token);
        document.getElementById("login-message").innerText = "Login realizado!";
    } else {
        document.getElementById("login-message").innerText = "Erro no login";
    }
}
