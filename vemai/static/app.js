const $ = (id) => document.getElementById(id);
const state = { operator: null, stop: null, board: null, boardTimer: null, searchTimer: null };

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function showNotice(text, kind = "") {
  const box = $("notice");
  box.textContent = text;
  box.className = `notice ${kind}`;
  box.hidden = !text;
}

async function api(path, options) {
  let resp;
  try {
    resp = await fetch(path, options);
  } catch {
    throw new Error("Sem conexão com o servidor. Verifique sua internet.");
  }
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : "Erro inesperado.";
    throw new Error(resp.status === 503 ? "A operadora está offline no momento. Tente novamente em instantes." : detail);
  }
  return resp.status === 204 ? null : resp.json();
}

const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
const isStandalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
const pushSupported = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

function checkEnvironment() {
  if (isIos && !isStandalone) {
    showNotice('No iPhone, toque em Compartilhar e escolha "Adicionar à Tela de Início". Abra o app por lá para receber avisos.');
  } else if (!pushSupported) {
    showNotice("Este navegador não suporta notificações push. Você ainda pode consultar os horários.", "error");
  }
}

function urlBase64ToUint8Array(b64) {
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function currentPushSubscription(create = false) {
  const reg = await navigator.serviceWorker.ready;
  const existing = await reg.pushManager.getSubscription();
  if (existing || !create) return existing;
  const { key } = await api("/api/vapid-public-key");
  return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key) });
}

async function loadOperators() {
  const box = $("operators");
  try {
    const operators = await api("/api/operators");
    box.replaceChildren(
      ...operators.map((op) => {
        const btn = el("button", { type: "button", className: "chip", disabled: !op.online, title: op.online ? "" : "Operadora offline" },
          el("span", { className: `dot ${op.online ? "" : "off"}` }), op.name);
        btn.setAttribute("role", "radio");
        btn.onclick = () => selectOperator(op.name);
        return btn;
      })
    );
  } catch (err) {
    showNotice(err.message, "error");
  }
}

function selectOperator(name) {
  state.operator = name;
  [...$("operators").children].forEach((b) => b.classList.toggle("selected", b.textContent === name));
  $("stop-section").hidden = false;
  $("stop-results").replaceChildren();
  stopBoardRefresh();
  $("board-section").hidden = true;
  $("stop-query").focus();
}

async function searchStops(query) {
  const list = $("stop-results");
  if (query.trim().length < 3) return list.replaceChildren();
  try {
    const stops = await api(`/api/operators/${state.operator}/stops?q=${encodeURIComponent(query.trim())}`);
    list.replaceChildren(
      ...(stops.length
        ? stops.map((s) => {
            const btn = el("button", { type: "button", className: "pick" }, `${s.id} · ${s.name}`);
            btn.onclick = () => selectStop(s);
            return el("li", {}, btn);
          })
        : [el("li", { className: "muted" }, "Nenhum ponto encontrado.")])
    );
  } catch (err) {
    showNotice(err.message, "error");
  }
}

function selectStop(stop) {
  state.stop = stop;
  $("stop-results").replaceChildren();
  $("stop-title").textContent = `${stop.id} · ${stop.name}`;
  $("board-section").hidden = false;
  stopBoardRefresh();
  refreshBoard();
  state.boardTimer = setInterval(refreshBoard, 15000);
}

function stopBoardRefresh() {
  clearInterval(state.boardTimer);
}

async function refreshBoard() {
  try {
    state.board = await api(`/api/operators/${state.operator}/stops/${state.stop.id}/board`);
    showNotice("");
  } catch (err) {
    showNotice(err.message, "error");
    return;
  }
  renderBoard(state.board);
}

function renderBoard(board) {
  const rows = board.predictions.map((p) =>
    el("li", {},
      el("span", {}, `Linha ${p.line.label} · veículo ${p.vehicle}`),
      el("span", { className: `eta ${p.eta_min <= 3 ? "soon" : ""}` }, p.eta_min === 0 ? "Chegando" : `${p.eta_min} min`))
  );
  board.other_lines.forEach((l) =>
    rows.push(el("li", {}, el("span", {}, `Linha ${l.label}`), el("span", { className: "muted" }, "mais de 20 min")))
  );
  $("board").replaceChildren(...(rows.length ? rows : [el("li", { className: "muted" }, "Nenhum ônibus previsto agora.")]));
  $("board-updated").textContent = `Atualizado às ${new Date().toLocaleTimeString("pt-BR")}`;

  const lines = new Map();
  [...board.predictions.map((p) => p.line), ...board.other_lines].forEach((l) => lines.set(l.id, l));
  const select = $("line");
  const chosen = select.value;
  select.replaceChildren(...[...lines.values()].map((l) => el("option", { value: l.id }, l.label)));
  if (lines.has(chosen)) select.value = chosen;
}

async function activateAlert(event) {
  event.preventDefault();
  if (isIos && !isStandalone) return showNotice('Adicione o app à Tela de Início para ativar alertas no iPhone.', "error");
  if (!pushSupported) return showNotice("Este navegador não suporta notificações push.", "error");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return showNotice("Sem permissão de notificação não é possível avisar você. Libere nas configurações do navegador.", "error");
  }
  const line = $("line").selectedOptions[0];
  try {
    const subscription = await currentPushSubscription(true);
    await api("/api/subscriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...subscription.toJSON(),
        operator: state.operator,
        stop_id: state.stop.id,
        stop_name: state.stop.name,
        line_id: line.value,
        line_label: line.textContent,
        time: $("time").value,
        lead_min: Number($("lead").value),
      }),
    });
    showNotice("Alerta ativado!", "ok");
    loadAlerts();
  } catch (err) {
    showNotice(err.message, "error");
  }
}

async function loadAlerts() {
  const list = $("alerts");
  try {
    const subscription = pushSupported ? await currentPushSubscription() : null;
    if (!subscription) return list.replaceChildren(el("li", { className: "muted" }, "Nenhum alerta neste aparelho."));
    const alerts = await api(`/api/subscriptions?endpoint=${encodeURIComponent(subscription.endpoint)}`);
    list.replaceChildren(
      ...(alerts.length
        ? alerts.map((a) => {
            const test = el("button", { type: "button", className: "secondary" }, "Testar");
            test.onclick = () => testAlert(a);
            const del = el("button", { type: "button", className: "danger" }, "Excluir");
            del.onclick = () => deleteAlert(a);
            return el("li", {},
              el("span", {}, `Linha ${a.line_label} · ${a.time} · ${a.lead_min} min antes`,
                el("br"), el("span", { className: "muted" }, `${a.operator} · ${a.stop_name}`)),
              el("span", { className: "actions" }, test, del));
          })
        : [el("li", { className: "muted" }, "Nenhum alerta neste aparelho.")])
    );
  } catch (err) {
    showNotice(err.message, "error");
  }
}

async function testAlert(alert) {
  try {
    await api(`/api/subscriptions/${alert.id}/test?endpoint=${encodeURIComponent(alert.endpoint)}`, { method: "POST" });
    showNotice("Notificação de teste enviada.", "ok");
  } catch (err) {
    showNotice(err.message, "error");
    loadAlerts();
  }
}

async function deleteAlert(alert) {
  try {
    await api(`/api/subscriptions/${alert.id}?endpoint=${encodeURIComponent(alert.endpoint)}`, { method: "DELETE" });
    loadAlerts();
  } catch (err) {
    showNotice(err.message, "error");
  }
}

$("stop-query").addEventListener("input", (e) => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(() => searchStops(e.target.value), 350);
});
$("alert-form").addEventListener("submit", activateAlert);

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js");
checkEnvironment();
loadOperators();
loadAlerts();
