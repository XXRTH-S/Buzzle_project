"use client";
import { useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";
import { api, stamp, type Segment } from "@/lib/api";

export type PlayerHandle = { seek: (ms: number) => void };

// Native audio streams/ranges long recordings without decoding the whole file for a waveform.
export const Player = forwardRef<PlayerHandle, {
  audioUrl: string;
  segments: Segment[];
  onEdited?: () => Promise<void>;
}>(function Player({ audioUrl, segments, onEdited }, ref) {
  const audio = useRef<HTMLAudioElement>(null);
  const [active, setActive] = useState<number | null>(null);
  const [rows, setRows] = useState(segments);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => setRows(segments), [segments]);
  function seek(ms: number) {
    const element=audio.current;
    if (!element) return;
    element.currentTime=Math.max(0,ms/1000);
    void element.play().catch(()=>setError("กดเล่นเสียงเพื่อเริ่มฟัง"));
  }
  useImperativeHandle(ref,()=>({seek}));
  async function save(segment: Segment) {
    setSaving(true);setError("");
    try {
      const updated=await api.editSegment(segment.id,draft);
      setRows(prev=>prev.map(r=>r.id===segment.id?{...r,...updated}:r));
      setEditing(null);
      await onEdited?.();
    } catch(e) {setError(e instanceof Error?e.message:"บันทึกไม่สำเร็จ");}
    finally {setSaving(false);}
  }
  return <div><div className="player"><audio ref={audio} controls preload="metadata" src={audioUrl} onTimeUpdate={()=>{const ms=(audio.current?.currentTime??0)*1000;setActive(rows.find(s=>ms>=s.start_ms&&ms<s.end_ms)?.id??null);}} /></div>{error&&<p role="alert" className="notice">{error}</p>}<ol className="transcript">{rows.map(s=><li key={s.id} className={active===s.id?"active":""}><div><button className="timecode" onClick={()=>seek(s.start_ms)} aria-label={`ฟังที่ ${stamp(s.start_ms)}`}>{stamp(s.start_ms)}</button><span className="small">{s.speaker??"ไม่ระบุผู้พูด"}</span></div>{editing===s.id?<><textarea aria-label="แก้ไขข้อความ" value={draft} onChange={e=>setDraft(e.target.value)}/><div className="toolbar"><button className="primary" disabled={saving} onClick={()=>save(s)}>บันทึก</button><button className="secondary" disabled={saving} onClick={()=>setEditing(null)}>ยกเลิก</button></div></>:<><p>{s.text||"ข้อความถูกลบแล้ว"}</p><button className="small" onClick={()=>{setEditing(s.id);setDraft(s.text);}}>แก้ไขข้อความ</button></>}</li>)}</ol></div>;
});
