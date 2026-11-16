const GreenQuote = {
  csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  },

  async postJson(url, body) {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.csrfToken(),
        },
        body: JSON.stringify(body || {}),
      });
    } catch (networkError) {
      return { ok: false, data: { error: "Can't reach the server. Check your connection." } };
    }
    let data = {};
    try {
      data = await response.json();
    } catch (parseError) {
      data = { error: "The server sent an unexpected response." };
    }
    return { ok: response.ok, status: response.status, data };
  },

  money(value) {
    return Number(value || 0).toLocaleString("en-US", { style: "currency", currency: "USD" });
  },

  show(el) {
    el.classList.remove("hidden");
  },

  hide(el) {
    el.classList.add("hidden");
  },
};
