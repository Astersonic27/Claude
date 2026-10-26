(() => {
  const root = document.getElementById("app");
  const csrf = root.dataset.csrf;
  const isAdmin = root.dataset.admin === "1";
  const $ = (id) => document.getElementById(id);
  const feed = $("feed"), loadMore = $("load-more");
  let nextBefore = null;

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) { location.href = "/login"; }
    return { ok: res.ok, status: res.status, body };
  }

  // All dynamic text goes through textContent / createTextNode => no HTML injection.
  function el(tag, props = {}, ...kids) {
    const n = Object.assign(document.createElement(tag), props);
    kids.forEach((k) => n.append(k));
    return n;
  }

  function renderItem(k) {
    const when = new Date(k.created_at).toLocaleString();
    const li = el("li", { className: k.is_visible === false ? "hidden-item" : "" });
    li.append(
      el("div", { className: "meta" }, el("strong", { textContent: k.sender.name }), " → ",
         el("strong", { textContent: k.recipient.name }), ` · ${when}`),
      el("p", { className: "msg", textContent: k.message })
    );
    if (k.is_visible === false) li.append(el("span", { className: "tag", textContent: "Hidden " }));
    if (isAdmin) {
      const act = (label, cls, fn) => el("button", { className: "small " + cls, textContent: label, onclick: fn });
      const reason = () => prompt("Reason (optional):") ?? null;
      li.append(el("div", {},
        k.is_visible === false
          ? act("Unhide", "secondary", async () => { await api(`/api/admin/kudos/${k.id}/unhide`, { method: "POST", body: "{}" }); reload(); })
          : act("Hide", "secondary", async () => { const r = reason(); if (r === null) return; await api(`/api/admin/kudos/${k.id}/hide`, { method: "POST", body: JSON.stringify({ reason: r }) }); reload(); }),
        act("Delete", "danger", async () => { if (!confirm("Permanently delete this kudos?")) return; await api(`/api/admin/kudos/${k.id}`, { method: "DELETE", body: JSON.stringify({ reason: "deleted by admin" }) }); reload(); })
      ));
    }
    return li;
  }

  async function loadFeed(append = false) {
    const qs = append && nextBefore ? `?before_id=${nextBefore}` : "";
    // Admins see hidden items (flagged) via the admin endpoint on first page; others use the public feed.
    const url = isAdmin && !append ? "/api/admin/kudos" : "/api/kudos" + qs;
    const { ok, body } = await api(url);
    if (!ok) return;
    if (!append) feed.replaceChildren();
    body.kudos.forEach((k) => feed.append(renderItem(k)));
    nextBefore = body.next_before_id ?? null;
    loadMore.hidden = nextBefore === null;
    $("feed-empty").hidden = feed.children.length > 0;
  }
  const reload = () => loadFeed(false);
  loadMore.onclick = () => loadFeed(true);

  async function loadUsers() {
    const { body } = await api("/api/users");
    (body.users || []).forEach((u) => $("recipient").append(el("option", { value: u.id, textContent: u.name })));
  }

  $("message").addEventListener("input", () => { $("counter").textContent = `${$("message").value.length}/500`; });

  $("kudos-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    ["recipient-error", "message-error", "form-status"].forEach((i) => ($(i).textContent = ""));
    const recipient = $("recipient").value, message = $("message").value.trim();
    let bad = false;
    if (!recipient) { $("recipient-error").textContent = "Select a colleague."; bad = true; }
    if (!message) { $("message-error").textContent = "Message is required."; bad = true; }
    if (bad) return;
    $("submit-btn").disabled = true;
    const { ok, body } = await api("/api/kudos", { method: "POST", body: JSON.stringify({ recipient_id: Number(recipient), message }) });
    $("submit-btn").disabled = false;
    if (ok) {
      $("message").value = ""; $("counter").textContent = "0/500"; $("recipient").value = "";
      $("form-status").textContent = "Kudos sent!";
      reload();
    } else if (body.fields) {
      $("recipient-error").textContent = body.fields.recipient_id || "";
      $("message-error").textContent = body.fields.message || "";
    } else {
      $("form-status").textContent = body.error || "Something went wrong.";
    }
  });

  loadUsers();
  reload();
})();
