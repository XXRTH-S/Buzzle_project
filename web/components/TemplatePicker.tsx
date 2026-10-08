"use client";
import { useEffect, useId, useState } from "react";
import { api, type Template } from "@/lib/api";
import { StructuredSummaryBody } from "./SummaryView";

export function TemplatePicker({value,onChange,catalog=false}:{value:string;onChange:(id:string)=>void;catalog?:boolean}) {
  const [templates,setTemplates]=useState<Template[]>([]);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  const uid=useId();
  const load=()=>{setLoading(true);setError("");api.templates().then(setTemplates).catch(()=>setError("โหลดเทมเพลตไม่สำเร็จ")).finally(()=>setLoading(false));};
  useEffect(()=>{load();},[]);
  const visible=catalog?templates.filter(t=>t.example):templates;
  const active=visible.find(t=>t.id===value);
  if(loading)return <p className="small" role="status">กำลังโหลดเทมเพลต…</p>;
  if(error)return <div className="notice" role="alert">{error} <button className="secondary" onClick={load}>ลองอีกครั้ง</button></div>;
  return <div className={catalog?"template-browser catalog-browser":"template-browser"}>
    <div className="template-options" role="tablist" aria-label="ประเภทการสรุป">
      {visible.map((t,i)=><button key={t.id} id={uid+t.id} role="tab" aria-selected={t.id===value} aria-controls={uid+"panel"} tabIndex={t.id===value||(!active&&i===0)?0:-1} onClick={()=>onChange(t.id)} onKeyDown={e=>{
        let next=i;
        if(e.key==="ArrowRight"||e.key==="ArrowDown")next=(i+1)%visible.length;
        else if(e.key==="ArrowLeft"||e.key==="ArrowUp")next=(i-1+visible.length)%visible.length;
        else if(e.key==="Home")next=0;else if(e.key==="End")next=visible.length-1;else return;
        e.preventDefault();onChange(visible[next].id);document.getElementById(uid+visible[next].id)?.focus();
      }}><strong>{t.label}</strong><span>{t.hint}</span></button>)}
    </div>
    {active&&<div id={uid+"panel"} role="tabpanel" aria-labelledby={uid+active.id} className="template-panel">
      {active.sections?.length ? <div className="template-focus"><span className="small">ส่วนที่เน้นในสรุป</span><div>{active.sections.map(s=><span key={s}>{s}</span>)}</div></div>:null}
      {active.example&&<details key={active.id} open={catalog} className="template-example"><summary>ดูตัวอย่าง · {active.label}</summary><div className="example-body"><p className="example-disclaimer">ตัวอย่างสมมติเพื่อแสดงรูปแบบ ไม่ใช่ผลสรุปจากไฟล์ของคุณ</p><StructuredSummaryBody data={active.example}/></div></details>}
    </div>}
  </div>;
}
