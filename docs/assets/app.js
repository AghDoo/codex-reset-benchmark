(() => {
  const body = document.body;
  const relativeDataBase = body.dataset.dataBase || "generated";
  const liveDataBase = body.dataset.liveDataBase || "";
  const isLocal = ["", "localhost", "127.0.0.1"].includes(window.location.hostname);
  const dataBases = !isLocal && liveDataBase ? [liveDataBase, relativeDataBase] : [relativeDataBase];
  const locale = body.dataset.locale || "en";
  const t = {
    en: { noData: "No archived forecast yet.", provisional: "provisional", eligible: "ranked", stale: "stale", live: "fresh", never: "not collected", window: "window" },
    "zh-TW": { noData: "尚未封存任何預測資料。", provisional: "暫定", eligible: "已納入排名", stale: "資料過舊", live: "新鮮", never: "尚未蒐集", window: "區間" }
  }[locale];
  const fmtPct = value => value == null ? "—" : `${(value * 100).toFixed(value * 100 % 1 ? 1 : 0)}%`;
  const fmtNum = value => value == null ? "—" : Number(value).toFixed(4);
  const esc = value => String(value ?? "").replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  async function loadJson(name) {
    let lastError = null;
    for (const dataBase of dataBases) {
      try {
        const response = await fetch(`${dataBase}/${name}`, {cache: "no-store"});
        if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
        return await response.json();
      } catch (error) { lastError = error; }
    }
    throw lastError || new Error(`${name}: unavailable`);
  }
  function renderRanking(targetId, rows) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = (rows || []).map(row => `<tr><td>${row.rank ?? "—"}</td><td><a href="${esc(row.url)}" rel="noopener noreferrer">${esc(row.name)}</a></td><td>${fmtNum(row.brier)}</td><td>${fmtNum(row.log_loss)}</td><td>${fmtPct(row.hit_rate)}</td><td>${row.samples}</td><td>${fmtPct(row.availability)}</td><td><span class="badge ${row.eligible ? "good" : "warn"}">${row.eligible ? t.eligible : t.provisional}</span></td></tr>`).join("");
  }
  function renderLatest(payload) {
    const reset = payload.latest_confirmed_reset;
    const resetEl = document.getElementById("latest-reset");
    if (resetEl) resetEl.textContent = reset ? new Date(reset.occurred_at).toLocaleString() : "—";
    const sourceTarget = document.getElementById("latest-sources");
    if (!sourceTarget) return;
    sourceTarget.innerHTML = (payload.sources || []).filter(s => s.enabled).map(source => {
      const latest = source.latest;
      let forecast = t.noData;
      if (latest) {
        const windowForecast = latest.window_forecast;
        if (windowForecast) {
          forecast = `${t.window}: ${fmtPct(windowForecast.probability)} · ${esc(windowForecast.forecast_window)}`;
        } else {
          const fixed = Object.entries(latest.forecasts || {}).map(([h, p]) => `${h}: ${fmtPct(p)}`);
          forecast = fixed.length ? fixed.join(" · ") : t.noData;
        }
      }
      const freshness = latest ? (source.stale ? t.stale : t.live) : t.never;
      return `<div class="card"><div class="source-row"><strong><a href="${esc(source.url)}" rel="noopener noreferrer">${esc(source.name)}</a></strong><span class="badge ${source.stale ? "warn" : latest ? "good" : ""}">${freshness}</span></div><div class="metric">${forecast}</div><div class="small muted">${latest ? esc(latest.observed_at) : "—"}</div></div>`;
    }).join("");
  }
  Promise.all([loadJson("leaderboard.json"), loadJson("latest.json"), loadJson("meta.json")]).then(([leaderboard, latest, meta]) => {
    const rankings = leaderboard.rankings || {};
    renderRanking("ranking-5h", rankings["5h"] || []);
    renderRanking("ranking-24h", rankings["24h"] || []);
    renderRanking("ranking-48h", rankings["48h"] || []);
    renderLatest(latest || {});
    const updated = document.getElementById("updated-at"); if (updated) updated.textContent = meta.generated_at ? new Date(meta.generated_at).toLocaleString() : "—";
    const count = document.getElementById("snapshot-count"); if (count) count.textContent = meta.snapshot_count ?? 0;
  }).catch(error => { const errorEl = document.getElementById("load-error"); if (errorEl) errorEl.textContent = error.message; console.error(error); });
})();
