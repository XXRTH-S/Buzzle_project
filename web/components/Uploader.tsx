"use client";
import { useRef, useState } from "react";
import { api } from "@/lib/api";

export function Uploader({ onStarted, template, onBusyChange }: { onStarted: (id: string) => void; template: string; onBusyChange?: (busy:boolean)=>void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [dragging,setDragging] = useState(false);

  async function handle(file: File) {
    if(busy) return;
    if(!template) { setError("เลือกเทมเพลตก่อนอัปโหลดไฟล์"); return; }
    if (!consent) { setError("กรุณายืนยันสิทธิ์ใช้ไฟล์และการส่งข้อมูลก่อนอัปโหลด"); return; }
    if (!file.size) { setError("ไฟล์นี้ว่าง กรุณาเลือกไฟล์เสียงอื่น"); return; }
    if (file.size > 500 * 1024 * 1024) { setError("ไฟล์ต้องไม่เกิน 500 MiB"); return; }
    setBusy(true); onBusyChange?.(true); setError(null);
    try {
      const { media_id, upload } = await api.createMedia(file.name, "auto", template);
      await api.upload(upload, file);
      await api.start(media_id);
      onStarted(media_id);
    } catch (e) { setError(e instanceof Error ? e.message : "อัปโหลดไม่สำเร็จ ลองอีกครั้ง"); }
    finally { setBusy(false); onBusyChange?.(false); if(input.current)input.current.value=""; }
  }
  return <div>
    <div className={`upload-area ${dragging?"dragging":""}`} onDragOver={e=>{e.preventDefault();if(!busy)setDragging(true);}} onDragLeave={e=>{if(!e.currentTarget.contains(e.relatedTarget as Node))setDragging(false);}} onDrop={e=>{e.preventDefault();setDragging(false);const file=e.dataTransfer.files[0];if(file)void handle(file);}}>
      <div className="upload-symbol"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></svg></div>
      <strong>{busy?"กำลังอัปโหลดไฟล์…":"ลากไฟล์เสียงมาวางที่นี่"}</strong>
      <p>MP3, M4A, WAV, MP4 · ไม่เกิน 500 MiB</p>
      <button className="primary" disabled={busy||!consent||!template} onClick={()=>input.current?.click()}>{busy?"กำลังอัปโหลด…" :"เลือกไฟล์เสียงและเริ่มสรุป"}</button>
      <input ref={input} type="file" id="audio-file" aria-label="ไฟล์เสียง" accept="audio/*,video/mp4,video/quicktime" hidden disabled={busy||!consent||!template} onChange={e=>{const file=e.target.files?.[0];if(file)void handle(file);}}/>
    </div>
    <label className="consent"><input type="checkbox" disabled={busy} checked={consent} onChange={e=>setConsent(e.target.checked)}/><span>ฉันมีสิทธิ์ใช้ไฟล์นี้ และยอมรับการส่งเสียงไปบริการถอดเสียง รวมถึงข้อความไป OpenRouter เพื่อสรุป</span></label>
    {error&&<p role="alert" className="notice">{error}</p>}
  </div>;
}
