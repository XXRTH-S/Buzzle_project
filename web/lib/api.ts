const BASE = process.env.NEXT_PUBLIC_API ?? "http://localhost:8100";

export type StructuredSummary = { headline: string; summary: string; sections: Record<string, string[]> };
export type Template = { id: string; label: string; hint: string; sections?: string[]; example?: StructuredSummary | null };
export type Media = { id: string; filename: string; status: string; duration_ms: number | null; created_at: string; error?: string | null; summary_template?: string };
export function statusLabel(status: string): string {
  return ({uploaded:"รอเริ่มงาน",queued:"รอคิว",normalizing:"กำลังเตรียมเสียง",transcribing:"กำลังถอดเสียง",joining:"กำลังจัดข้อความ",summarizing:"กำลังสรุป",done:"เสร็จแล้ว",failed:"ต้องตรวจสอบ",running:"กำลังประมวลผล"} as Record<string,string>)[status] ?? status;
}

export type Segment = {
  id: number;
  idx: number;
  start_ms: number;
  end_ms: number;
  speaker: string | null;
  text: string;
  text_model: string;
  text_edited: string | null;
};

export type ActionItem = {
  task: string;
  owner: string;
  due: string | null;
  cite_ms: number;
};

export type KeyPoints = {
  headline: string;
  summary: string;
  decisions: string[];
  action_items: ActionItem[];
  open_questions: string[];
};

export type TimelineEntry = {
  at_ms: number;
  kind: "topic" | "decision" | "assignment" | "blocker" | "schedule";
  title: string;
  detail: string;
  speaker: string | null;
};

export type Timeline = { headline: string; entries: TimelineEntry[] };

export type Summary = {
  template_id: string;
  model: string;
  payload: KeyPoints | Timeline | StructuredSummary;
  usage: {
    input_tokens: number | null;
    output_tokens: number | null;
    // ถ้าค่านี้เป็น 0 ตลอด แปลว่า cache ไม่ติด
    cache_read_tokens: number | null;
  };
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(()=>({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `คำขอไม่สำเร็จ (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,
  health: () => json<{summary_key?:string;asr_key?:string}>("/health"),
  listMedia: () => json<Media[]>("/api/media"),
  summaries: (id:string) => json<Summary[]>(`/api/media/${id}/summaries`),

  templates: () => json<Template[]>("/api/templates"),

  createMedia: (filename: string, language = "auto", summary_template = "key_points") =>
    json<{ media_id: string; upload: { method: string; url: string } }>(
      "/api/media",
      { method: "POST", body: JSON.stringify({ filename, language, summary_template }) },
    ),

  async upload(target: { method: string; url: string }, file: File) {
    const res = await fetch(target.url, { method: target.method, body: file });
    if (!res.ok) throw new Error(`อัปโหลดล้มเหลว: ${res.status}`);
  },

  start: (mediaId: string) =>
    json<{ status: string }>(`/api/media/${mediaId}/start`, { method: "POST" }),

  media: (mediaId: string) => json<Media>(`/api/media/${mediaId}`),

  segments: (mediaId: string) =>
    json<Segment[]>(`/api/media/${mediaId}/segments`),

  editSegment: (segmentId: number, text: string) =>
    json<Segment>(`/api/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ text }),
    }),

  summary: (mediaId: string, template: string) =>
    json<Summary>(`/api/media/${mediaId}/summary?template=${template}`),

  requestSummary: (mediaId: string, template: string, force = false) =>
    json<{ status: "ready" | "queued"; cached: boolean }>(
      `/api/media/${mediaId}/summarize`,
      { method: "POST", body: JSON.stringify({ template, force }) },
    ),
};

export function stamp(ms: number): string {
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = String(Math.floor(total / 60) % 60).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  return h > 0 ? `${h}:${m}:${s}` : `${m}:${s}`;
}
