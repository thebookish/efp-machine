
import axios from "axios";
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" }
});

export async function askAI(message: string) {
  const { data } = await api.post("/api/ai/chat", { message });
  return data;
}

export async function getRun() {
  const { data } = await api.get("/api/efp/run");
  return data;
}
