# แผนเวิร์กช็อป — Buzzle Hybrid

อัปเดต 2026-09-14 · ใช้สกิล create-plan จัดแผนตามข้อกำหนดโปรเจกต์

เป้าหมายคือ portfolio เว็บถอดเสียงไทย/อังกฤษพร้อมสรุปสองเทมเพลต รองรับไฟล์ 30–60 นาที และอธิบายผลวัดบน RTX 3050 6 GB ได้ ใช้โค้ดเดิมเป็นฐานและ Local เป็นค่าเริ่มต้นตามแผน

## Scope

- In: Python/Docker, FastAPI/RQ/PostgreSQL/Next.js เดิม, batch jobs, timestamps, Local/Cloud adapters, optional speakers, benchmark และ demo
- Out: streaming, fine-tuning, Kubernetes, billing platform และ public deployment ในรอบเอกสาร
- Current: local summary/diarization และหน้าเว็บยังไม่ครบ; ยังไม่ได้ยืนยัน build/end-to-end ดู [README](../README.md)

## Action items

- [ ] M0 — ตรวจ GPU passthrough, RAM/VRAM ว่าง, disk, Python/CUDA/cuDNN compatibility และ URL 8100; เตรียม Git baseline ก่อนแก้ implementation โดยไม่รวม secrets/media
- [ ] M1 — แก้ atomic job claim พร้อม lease/recovery, durable dispatch, per-job routing, รักษา words ตอน join และ cancel/delete ขณะทำงาน
- [ ] M2 — ประกอบ Next.js: upload, history, progress, playback, transcript editing และ template views; เพิ่ม web Docker service และ integration tests
- [ ] M3 — ทำ Local ASR: Turbo INT8 ไม่ใช้ large batch, fallback small/medium, normalize รักษา offset และหนึ่ง GPU owner ทั้งระบบ
- [ ] M4 — เพิ่ม summary adapters: Ollama/Qwen 4B candidate, ใช้ OpenRouter/Claude adapters ที่มีแล้ว, provider-aware structured output และ token-bounded map-reduce
- [ ] M5 — ทำ evidence/revisions: validate source segment IDs, derive timestamps, invalidate เมื่อแก้ transcript, cache ตาม provider/model/template/revision และ export TXT/Markdown/JSON
- [ ] M6 — เพิ่ม Community-1 แบบ Default Off หลัง core ผ่าน: รันแยก stage, วัด CPU/GPU memory, labels ภายในไฟล์ และ failure ไม่ทำ transcript หาย
- [ ] M7 — เพิ่ม Cloud opt-in แยก ASR/summary ต่อ job, ตรวจ model ID, preview ข้อมูลที่จะส่ง, cost limit และ retention; ไม่มี automatic Cloud fallback
- [ ] M8 — วัดเสียง 5/30/60 นาที: CER/WER, ผู้พูด, summary rubric, latency/usage/memory, recovery และจัด demo สำหรับสัมภาษณ์

ความคืบหน้าล่าสุด: เพิ่ม OpenRouter free adapter, config, safe errors, usage/model tracking และ offline Docker tests แล้ว ยังขาดคีย์จริงและ Local summary ดู [OpenRouter](openrouter.md)

## เงื่อนไขผ่าน

| Milestone | ผลลัพธ์ก่อนขยับ |
|---|---|
| M0–M1: core correctness | กดซ้ำไม่รับงานพร้อมกัน, rerun ไม่ทำ words หาย, restart แล้วกู้ขั้นงานได้ |
| M2: core UI | upload → progress → ฟัง/แก้ transcript → สองเทมเพลต ผ่าน integration test |
| M3–M5: Local baseline | คลิปสั้นจบโดยไม่มี Cloud key; 30/60 นาทีมีรายงานทรัพยากร; invalid evidence ถูกปฏิเสธ |
| M6: optional speakers | ประเมินหลายผู้พูดจริง; ไม่ผ่านให้คง experimental/off |
| M7: Cloud | stub tests ก่อน; live call เมื่อเลือก provider และยอมรับค่าใช้จ่าย/ข้อมูลที่จะส่ง |
| M8: portfolio | ทำ benchmark ซ้ำได้, credits ครบ และ demo ไม่ต้องรอไฟล์หนึ่งชั่วโมงสด |

M2 ใช้ fixtures ที่ติดป้ายว่าเป็นข้อมูลทดสอบระหว่างรอ provider ได้ ไม่แสดง fixture เป็นผล inference จริง

## Workshop 2 วัน

เสนอวันละประมาณ 6 ชั่วโมงสำหรับ walkthrough บน baseline ที่เตรียมและทดสอบแล้ว ไม่รับประกันว่าพัฒนางานค้างทั้งหมดจาก checkout ปัจจุบันจะเสร็จใน 12 ชั่วโมง

| วัน | Lab | เวลาเรียนโดยประมาณ |
|---|---|---|
| 1 | M0 Docker/GPU และ architecture | 1 ชั่วโมง |
| 1 | M1 jobs/upload/timestamps | 1.5 ชั่วโมง |
| 1 | M3 Local ASR และคลิปสั้น | 1.5 ชั่วโมง |
| 1 | M2 หน้าเว็บ | 2 ชั่วโมง |
| 2 | M4–M5 summary/templates/evidence | 2 ชั่วโมง |
| 2 | M6 optional speakers | 1 ชั่วโมง |
| 2 | M7 Cloud และการจัดการข้อมูล | 1 ชั่วโมง |
| 2 | M8 benchmark/demo/tradeoffs | 2 ชั่วโมง |

ไม่รวม download/build, พัก และประมวลผลชุดเสียงยาว เตรียม model cache และผลไฟล์ยาวก่อนวันเรียน

## Validation และกรณีขอบ

- ตรวจไฟล์ผิดชนิด/เสีย/ไม่มี audio track/เกิน 60 นาที ก่อนเรียก provider ที่เสียเงิน
- Stream upload ลง disk พร้อมจำกัด bytes; RAM ไม่เพิ่มตามขนาดไฟล์ทั้งก้อน
- เสียงเงียบคืนสถานะไม่มีคำพูดและไม่สร้างสรุปแต่งขึ้น
- ทดสอบไทยปนอังกฤษ ชื่อเฉพาะ ก้อง และพูดทับ; speaker label ไม่ใช่ชื่อคนจริง
- ทดสอบ timestamp ต้น/กลาง/ท้าย และ merge overlap โดยไม่ทำคำซ้ำ
- ทดสอบ concurrent start/retry และ crash ระหว่าง commit/dispatch
- Remote timeout ที่ไม่รู้ผลต้อง reconcile ก่อน retry ไม่รับประกัน exactly-once จาก unique DB row
- OOM ให้จำกัด retry และลด config หรือแจ้งผู้ใช้ ไม่ส่ง Cloud เอง
- Diarization/summary ล้มเหลวต้องยังอ่านและ export transcript ที่สำเร็จได้
- Delete ขณะรันต้องหยุดการเขียนและลบ work files ไม่ให้เกิดคืน

## เตรียมก่อนเรียน

Docker Desktop/WSL2 Linux containers, เสียงที่ได้รับอนุญาต, gold transcript และพื้นที่สำหรับ images/models/audio ตรวจ RAM/VRAM ตาม [hardware](hardware.md)

Local ไม่ต้องมี Cloud key หลังเตรียม artifacts; pyannote ต้องมีสิทธิ์ดาวน์โหลด Cloud lab ต้องกำหนด budget/credentials ก่อนรันจริง ดู [models](model-selection.md)

## Open questions

- Cloud summary model สุดท้ายเลือกจาก quality/cost และเงื่อนไขข้อมูลของบัญชีจริง
- ASR/context default และสถานะ diarization ล็อกหลัง benchmark
- Hosting ยังไม่เลือก ทดสอบในเครื่องก่อนขยาย online demo
