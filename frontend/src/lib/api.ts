import type { SessionResponse, SessionDetailResponse, MessageResponse } from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function createSession(transcript: string): Promise<SessionResponse> {
  const res = await fetch(`${API_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript_text: transcript }),
  });
  if (!res.ok) throw new Error('Failed to analyze transcript');
  return res.json();
}
export async function createLiveSession(): Promise<SessionResponse> {
  const res = await fetch(`${API_URL}/sessions/live`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to create live session');
  return res.json();
}

export async function sendAudioChunk(sessionId: string, audioBlob: Blob): Promise<SessionResponse> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'chunk.webm');

  const res = await fetch(`${API_URL}/sessions/${sessionId}/audio-chunk`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to process audio chunk');
  return res.json();
}

export async function finalizeLiveSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/finalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to finalize live session');
  return res.json();
}
export async function sendFollowupMessage(sessionId: string, message: string): Promise<MessageResponse> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: message }),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionDetailResponse> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch session');
  return res.json();
}

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

export async function loginAdmin(email: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData.toString()
  });

  if (!res.ok) throw new Error('Login failed');
  return res.json();
}

export async function getAdminSessions() {
  const res = await fetch(`${API_URL}/admin/sessions`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch admin sessions');
  return res.json();
}

export async function getSessionDetail(sessionId: string) {
  const res = await fetch(`${API_URL}/admin/sessions/${sessionId}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch session detail');
  return res.json();
}

export async function sendSessionMessage(sessionId: string, message: string) {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ content: message }),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}

export async function getAdminGraph() {
  const res = await fetch(`${API_URL}/admin/graph`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch graph data');
  return res.json();
}

export async function updateSessionStatus(sessionId: string, status: string) {
  const res = await fetch(`${API_URL}/admin/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify({ status })
  });
  if (!res.ok) throw new Error('Failed to update status');
  return res.json();
}
