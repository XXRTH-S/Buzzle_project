"use client";

import { useEffect, useState } from "react";
import { api } from "./api";

export type Progress = {
  step: string;
  state: "running" | "done" | "failed" | string;
  progress: number | null;
  error?: string;
};

/** อ่าน SSE ความคืบหน้าต่อขั้น — ผู้ใช้เปิดหน้าหลังงานเริ่มไปแล้วก็ยังเห็นสถานะ */
export function useProgress(mediaId: string | null) {
  const [events, setEvents] = useState<Progress[]>([]);
  const [latest, setLatest] = useState<Progress | null>(null);

  useEffect(() => {
    if (!mediaId) return;
    const source = new EventSource(`${api.base}/api/media/${mediaId}/events`);

    source.onmessage = (raw) => {
      const payload: Progress = JSON.parse(raw.data);
      setLatest(payload);
      setEvents((prev) => [...prev, payload]);
      if (payload.state === "failed") source.close();
      if (payload.step.startsWith("summarize") && payload.state === "done") {
        source.close();
      }
    };
    source.onerror = () => source.close();

    return () => source.close();
  }, [mediaId]);

  return { events, latest };
}
