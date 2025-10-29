const API_BASE = 'https://your-backend.example.com/api'; // change to your backend

export async function postEvent(token, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  const text = await res.text();
  try {
    const json = text ? JSON.parse(text) : null;
    if (!res.ok) throw { status: res.status, body: json || text };
    return json;
  } catch (e) {
    if (!res.ok) throw { status: res.status, body: text };
    throw e;
  }
}

export async function postMultipart(token, path, formData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  const text = await res.text();
  try {
    const json = text ? JSON.parse(text) : null;
    if (!res.ok) throw { status: res.status, body: json || text };
    return json;
  } catch (e) {
    if (!res.ok) throw { status: res.status, body: text };
    throw e;
  }
}
