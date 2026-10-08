"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type CSSProperties } from "react";
import { Bee } from "@/components/Bee";
import { Uploader } from "@/components/Uploader";
import { TemplateCatalog } from "@/components/TemplateCatalog";
import { api, stamp, statusLabel, type Media, type Template } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [files, setFiles] = useState<Media[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [template,setTemplate]=useState("");
  const [uploading,setUploading]=useState(false);
  const [templates,setTemplates]=useState<Template[]>([]);
  useEffect(()=>{api.templates().then(setTemplates).catch(()=>{});},[]);
  const selected=templates.find(t=>t.id===template);
  const [search,setSearch] = useState("");
  const [health, setHealth] = useState<{summary_key?: string; asr_key?: string} | null>(null);
  useEffect(() => { let alive=true; Promise.all([api.listMedia(), api.health()]).then(([rows, ready]) => {if(alive){setFiles(rows);setHealth(ready);}}).catch(e=>{if(alive)setError(e.message);}).finally(()=>{if(alive)setLoading(false);}); return()=>{alive=false;}; }, []);
  const shown = files.filter(f=>f.filename.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  return <>
    <div className="hero">
      <div>
        <p className="eyebrow">เปลี่ยนเสียงเป็นสรุป ในแบบที่คุณเลือก</p>
        <h1>ทุกบทสนทนา<br/>มีเรื่อง<span className="highlight">ให้จดจำ</span></h1>
        <p className="intro">เปลี่ยนไฟล์เสียงเป็นข้อความและสรุปที่อ่านง่าย<br/>เลือกสาระสำคัญหรือ Timeline แล้วกลับไปฟัง<br className="hidden md:block"/>ช่วงที่ต้องการได้ในคลิกเดียว</p>
        <div className="workflow" aria-label="ขั้นตอนการใช้งาน"><span><b>1</b>เลือกเทมเพลต</span><span><b>2</b>อัปโหลดเสียง</span><span><b>3</b>รับสรุป</span></div>
        <div className="hero-art" aria-hidden="true"><Bee className="hero-bee"/><div className="sound-bars">{[10,18,30,22,14,28,36,22,12,20,29,17,9].map((h,i)=><i key={i} style={{"--height":h+"px","--delay":i*.12+"s"} as CSSProperties}/>)}</div></div>
      </div>
      <div className="setup-note"><span className="eyebrow">สรุปในแบบที่คุณต้องการ</span><h2>เลือกแบบก่อน<br/>แล้วให้เราช่วยจด</h2><p>ประชุมบอร์ด อบรม หรือประชุมทีม<br/>แต่ละแบบเน้นเนื้อหาต่างกัน</p><a className="primary" href="#templates">เลือกเทมเพลต</a></div>
    </div>
    <div className="upload-workflow">
      <TemplateCatalog selected={template} onChange={setTemplate} disabled={uploading}/>
      <section className="upload-panel" id="upload" aria-labelledby="upload-heading"><p className="eyebrow">ขั้นตอนที่ 2</p><h2 id="upload-heading">อัปโหลดไฟล์เพื่อเริ่มสรุป</h2><p className="panel-subtitle">สูงสุด 60 นาที · 500 MiB</p>
        <div className="selected-template" role="status">{template?<>สรุปตามแบบ <strong>{selected?.label??template}</strong></>:"เลือกเทมเพลตในขั้นตอนที่ 1 ก่อน"}</div>
        <Uploader template={template} onBusyChange={setUploading} onStarted={id=>router.push(`/media/${id}`)}/>
        <p className="small upload-explainer">ถอดเสียงเสร็จแล้ว ระบบจะสร้างสรุปตามเทมเพลตที่เลือกโดยอัตโนมัติ</p>
        {health && (health.summary_key!=="set" || health.asr_key!=="set") && <p className="notice">ยังไม่ได้ตั้งคีย์บริการครบ อัปโหลดไฟล์ได้ แต่การถอดเสียงหรือสรุปจะยังไม่สำเร็จ</p>}
      </section>
    </div>
    <section id="files" className="files-section"><div className="section-head"><h2>ไฟล์ของคุณ <span className="count">{loading?"…":files.length}</span></h2><input className="search" type="search" aria-label="ค้นหาไฟล์" placeholder="ค้นหาชื่อไฟล์…" value={search} onChange={e=>setSearch(e.target.value)}/></div>
      {loading?<p className="empty" role="status">กำลังโหลดรายการ…</p>:error?<p role="alert" className="notice">เชื่อมต่อระบบไม่ได้: {error}</p>:shown.length===0?<div className="empty"><svg className="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M5 3h9l5 5v13H5zM14 3v6h5M8 13h8M8 17h5"/></svg><strong>{search?"ไม่พบไฟล์ที่ค้นหา":"บทสนทนาแรกของคุณ เริ่มได้ที่นี่"}</strong><p>{search?"ลองค้นหาด้วยชื่ออื่น":"อัปโหลดไฟล์เสียง แล้วข้อความและสรุปจะรวมอยู่ในที่เดียว"}</p></div>:shown.map(file=><Link className="file-row" key={file.id} href={`/media/${file.id}`}><div><strong>{file.filename}</strong><time>{new Date(file.created_at).toLocaleString("th-TH")}</time></div><span className="status">{statusLabel(file.status)}</span><span className="small">{file.duration_ms?stamp(file.duration_ms):"ยังไม่ทราบความยาว"}</span></Link>)}
    </section>
  </>;
}
