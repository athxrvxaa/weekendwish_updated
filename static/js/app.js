document.getElementById("go").addEventListener("click", async () => {
  const start = document.getElementById("start").value.trim();
  const budget = Number(document.getElementById("budget").value || 0);
  const people = Number(document.getElementById("people").value || 1);

  const payload = { budget, people, start };

  const res = await fetch("/api/recommend", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  const box = document.getElementById("results");
  box.innerHTML = "";

  if (data.error) {
    box.textContent = "Error: " + (data.error || JSON.stringify(data));
    return;
  }
  if (!data.results || data.results.length===0) {
    box.textContent = "No places found.";
    return;
  }

  for (const p of data.results) {
    const div = document.createElement("div");
    div.className = "card";
    const img = document.createElement("img");
    img.src = p.photo || "https://via.placeholder.com/140x90?text=No+image";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `<strong>${p.name}</strong>
      <div>${p.address || ""}</div>
      <div>Popularity: ${p.popularity || "—"}</div>
      <div>Price level: ${p.price || "unknown"}</div>`;
    div.appendChild(img);
    div.appendChild(meta);
    box.appendChild(div);
  }
});
