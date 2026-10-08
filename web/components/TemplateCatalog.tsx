"use client";

import { TemplatePicker } from "./TemplatePicker";
export function TemplateCatalog({selected,onChange,disabled=false}:{selected:string;onChange:(id:string)=>void;disabled?:boolean}) {
  return <section className="template-catalog" id="templates" aria-labelledby="template-heading">
    <div className="section-head"><div><p className="eyebrow">ขั้นตอนที่ 1</p><h2 id="template-heading">เลือกเทมเพลตสำหรับไฟล์นี้</h2><p className="small">เลือกแนวทางสรุปและดูตัวอย่างก่อนอัปโหลด ระบบจะใช้แบบนี้เมื่อถอดเสียงเสร็จ</p></div></div>
    <fieldset disabled={disabled}><TemplatePicker value={selected} onChange={onChange}/></fieldset>
    {!selected&&<p className="small selection-hint">ยังไม่ได้เลือกเทมเพลต · เลือกหนึ่งแบบเพื่ออัปโหลด</p>}
  </section>;
}
