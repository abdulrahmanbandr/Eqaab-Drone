const API_BASE = `http://${window.location.hostname}:8000`;

export async function sendCommand(command, params = {}) {
  const res = await fetch(`${API_BASE}/api/commands/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command, params }),
  });
  return res.json();
}

export async function getDroneState() {
  const res = await fetch(`${API_BASE}/api/commands/state`);
  return res.json();
}

export async function getMissionConfig() {
  const res = await fetch(`${API_BASE}/api/mission/config`);
  return res.json();
}
