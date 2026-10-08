"use client";
import { useEffect, useState } from "react";
import { api, type Template } from "@/lib/api";

export function SummaryActions({ id, template, hasSummary, disabled, running, failed, generate, onError }: {
  id: string; template: string; hasSummary: boolean; disabled: boolean; running: boolean; failed: boolean;
  generate: () => void; onError: (message: string) => void;
}) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [downloading, setDownloading] = useState(false);
  useEffect(() => { api.templates().then(setTemplates).catch(() => {}); }, []);
  const label = templates.find(t => t.id === template)?.label ?? template;
  async function download() {
    setDownloading(true); onError("");
    try {
      const response = await fetch(`${api.base}/api/media/${id}/summary.pdf?template=${encodeURIComponent(template)}`);
      if (!response.ok) throw new Error("ดาวน์โหลด PDF ไม่สำเร็จ กรุณาลองอีกครั้ง");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url; link.download = `buzzle-${id}-${template}.pdf`;
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { onError(e instanceof Error ? e.message : "ดาวน์โหลดไม่สำเร็จ"); }
    finally { setDownloading(false); }
  }
  return <>
    <h2>สรุปแบบ · {label}</h2>
    <p className="small">เลือกเทมเพลตแล้วกดสร้างสรุป ระบบใช้ข้อความเดิม ไม่ถอดเสียงซ้ำ</p>
    <div className="toolbar">
      <button className="primary" disabled={disabled} onClick={generate}>{hasSummary ? "สร้างสรุปใหม่" : failed ? "ลองสรุปใหม่ตามแบบที่เลือก" : "สร้างสรุปตามแบบที่เลือก"}</button>
      <button className="secondary" disabled={!hasSummary || disabled || downloading} onClick={download}>{downloading ? "กำลังสร้าง PDF…" : "ดาวน์โหลด PDF"}</button>
    </div>
    {running && <p className="notice" role="status">กำลังรอผลสรุปจากโมเดล{hasSummary ? " — ด้านล่างเป็นผลที่บันทึกไว้ก่อนหน้า" : ""}</p>}
    <p className="small">PDF ใช้สรุปที่บันทึกไว้ของเทมเพลตนี้ ไม่เรียก AI เพิ่ม โปรดตรวจสอบก่อนนำไปใช้</p>
  </>;
}
