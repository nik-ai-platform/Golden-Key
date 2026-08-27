const apiBase = "/api/v1";
let accessToken = "";

const views = {
  dashboard: loadDashboard,
  predictions: loadPredictions,
  teams: loadTeams,
  games: loadGames,
  analytics: loadAnalytics,
  trends: loadTrends,
};

function setActiveButton(page) {
  document.querySelectorAll("nav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
  });
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${apiBase}${path}`, { ...options, headers });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || JSON.stringify(data));
  }
  return data;
}

function renderPre(data) {
  document.getElementById("content").innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

function renderTable(columns, rows) {
  const head = `<tr>${columns.map((c) => `<th>${c}</th>`).join("")}</tr>`;
  const body = rows
    .map((row) => `<tr>${columns.map((c) => `<td>${row[c] ?? ""}</td>`).join("")}</tr>`)
    .join("");
  document.getElementById("content").innerHTML = `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
}

async function loadDashboard() {
  const data = await request("/dashboard");
  renderPre(data);
}

async function loadPredictions() {
  const controls = document.getElementById("controls");
  controls.innerHTML = `<input id="predictionGameId" placeholder="Game ID" /><button id="predictionFetch">Fetch Prediction</button>`;
  document.getElementById("predictionFetch").onclick = async () => {
    const gameId = document.getElementById("predictionGameId").value || "1";
    try {
      const data = await request(`/predictions/${gameId}`);
      renderPre(data);
    } catch (error) {
      renderPre({ error: error.message });
    }
  };
  renderPre({ hint: "Enter a game ID and click Fetch Prediction" });
}

async function loadTeams() {
  const teams = await request("/teams/");
  renderTable(["id", "name", "league", "sport"], teams);
}

async function loadGames() {
  const games = await request("/games/");
  renderTable(["id", "sport", "league", "home_team_id", "away_team_id"], games);
}

async function loadAnalytics() {
  const [accuracy, confidence] = await Promise.all([
    request("/analytics/accuracy"),
    request("/analytics/confidence"),
  ]);
  renderPre({ accuracy, confidence });
}

async function loadTrends() {
  const [daily, weekly, monthly, sport, model] = await Promise.all([
    request("/analytics/trends/daily"),
    request("/analytics/trends/weekly"),
    request("/analytics/trends/monthly"),
    request("/analytics/trends/sport"),
    request("/analytics/trends/model"),
  ]);
  renderPre({ daily, weekly, monthly, sport, model });
}

async function loadPage(page) {
  setActiveButton(page);
  document.getElementById("pageTitle").textContent = page
    .replace(/^./, (c) => c.toUpperCase())
    .replace("predictions", "Live Predictions")
    .replace("trends", "Historical Trends");
  document.getElementById("controls").innerHTML = "";

  try {
    await views[page]();
  } catch (error) {
    renderPre({ error: error.message });
  }
}

document.querySelectorAll("nav button").forEach((btn) => {
  btn.onclick = () => loadPage(btn.dataset.page);
});

document.getElementById("loginBtn").onclick = async () => {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  try {
    const token = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    accessToken = token.access_token;
    document.getElementById("authInfo").textContent = JSON.stringify(token, null, 2);
  } catch (error) {
    document.getElementById("authInfo").textContent = error.message;
  }
};

document.getElementById("meBtn").onclick = async () => {
  try {
    const me = await request("/auth/me");
    document.getElementById("authInfo").textContent = JSON.stringify(me, null, 2);
  } catch (error) {
    document.getElementById("authInfo").textContent = error.message;
  }
};

loadPage("dashboard");
