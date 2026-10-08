# จุดเสี่ยงที่ต้องทดสอบ — Buzzle

เอกสารนี้อิงโค้ดปัจจุบันและเป้าหมาย Hybrid วันที่ 2026-09-14 ไม่ใช่รายการที่แก้เสร็จแล้ว

## คำพูดหลอนและ VAD

VAD ช่วยลดช่วงไม่มีเสียงพูดแต่ไม่รับประกันว่า Whisper จะไม่แต่งข้อความ ทดสอบเงียบ เพลง ก้อง และเสียงเบา การตั้ง condition_on_previous_text=False เป็นค่าที่ต้องเทียบคุณภาพ ไม่ใช่คำตอบทุกไฟล์

audio/vad.py ปัจจุบันใช้ FFmpeg silencedetect; Local Whisper เปิด vad_filter อยู่แล้ว ไม่ควรเขียนเอกสารว่าทั้งระบบใช้ standalone Silero ถ้ายังไม่ได้ implement

ถ้าตัดเงียบแล้วต่อเสียงใหม่ ต้องมี mapping กลับเวลาต้นฉบับ มิฉะนั้น Timeline จะคลาด

## ภาษาไทยและการวัดผล

WER ต้องมี tokenizer/version ที่ระบุชัด ไม่ใช้ split ช่องว่างเป็นตัวแทนการตัดคำไทย รายงาน CER พร้อม normalization คงที่ และแยกคลิปปรับค่าออกจากชุดตัดสิน

ไม่จัดอันดับโมเดลจาก benchmark คนละภาษา/ชุดข้อมูลหรือใช้ความเร็ว real-time API เป็นเวลา batch หนึ่งชั่วโมง

## Timestamp และ words หาย

pipeline.join_step ปัจจุบันลบ segments แล้วสร้างใหม่ ขณะที่ words มี ON DELETE CASCADE ทำให้คำและเวลาหาย ต้องรักษา raw words และ reassign/alignment อย่างถูกต้อง

เวลาเฉลี่ยจากสัดส่วนตัวอักษรไม่ใช่ forced alignment ทดสอบ seek ต้น กลาง ท้าย และ speech overlap ใช้ timestamp จากต้นทางเมื่อมี

## งานซ้ำและ recovery

_claim() ปัจจุบันข้ามเฉพาะ done แต่ไม่กันคนรับงาน running เดียวกัน ต้องเพิ่ม atomic owner/lease และ durable dispatch

Unique row ไม่รับประกันไม่เสียค่า API ซ้ำเมื่อ remote สำเร็จแต่ client timeout ใช้ request tracking/reconciliation และ retry limit

เส้นทาง retry ต้องยังเข้าคิวที่ถูก ไม่เรียก GPU stage ตรงจาก CPU worker และใช้ provider snapshot ของ job

## Upload และไฟล์หนึ่งชั่วโมง

local_upload ใช้ request.body() และ storage มี read_bytes() จึงยังโหลดไฟล์ทั้งก้อนเข้า RAM เป้าหมายต้อง stream/copy แบบ bounded พร้อม byte/duration limit และ cleanup ไฟล์อัปโหลดไม่ครบ

การใช้ local API upload ทำได้เมื่อ bounded ไม่จำเป็นต้องบังคับ S3 ตั้งแต่ workshop รุ่นแรก

## GPU และ RAM

ไม่กำหนด VRAM จากขนาด weights และไม่ตัดสินว่า Local ทำไม่ได้เพราะรันทุกโมเดลพร้อมกันไม่ได้ ใช้ sequential stages และวัดก่อนเลือก default

หนึ่ง RQ worker ไม่กัน Ollama ที่ถูกเรียกนอกคิว ต้องมี shared GPU ownership และยืนยัน unload ของ engine; torch.cuda.empty_cache() ไม่จัดการ memory ของทุก engine

Diarization แยก chunk อาจสลับ speaker labels ต้อง reconcile ข้าม chunk CPU fallback ก็ใช้ RAM/เวลา จึงต้องทดสอบก่อนถือว่าเป็นทางกู้คืน

## สรุปและ cache

Schema ผ่านไม่เท่ากับสรุปถูก; source ID มีจริงก็ยังอาจถูกอ้างผิดเรื่อง ตรวจด้วย human rubric

Cache เดิมตาม media/template อาจคืนผลเก่าหลังแก้ transcript หรือเปลี่ยน model เพิ่ม revision/provider/config key และ stale indicator

Provider cache read เป็น 0 ไม่ได้หมายถึง cache bug เสมอ ไม่ใช้ราคาคงที่ต่อชั่วโมงโดยไม่มี usage/plan จริง

## การลบและข้อมูล

DELETE ปัจจุบันลบ raw storage/DB แต่ยังต้องตรวจ work directory และ worker ที่กำลังรัน เพิ่ม cancellation/tombstone และ retention job ที่ลบจริงทุก artifact

Local inference แต่ใช้ S3/OneDrive sync ก็ยังมีข้อมูลออกจากเครื่อง ตรวจ storage/telemetry/network ก่อนอ้าง offline

Cloud opt-in ต้องผูกกับ job/provider/purpose โดยแจ้งข้อมูลที่จะส่ง; UI checkbox อย่างเดียวไม่ใช่การยืนยันว่าครบข้อกำหนดด้านข้อมูล ใช้เสียงตัวอย่างที่ได้รับอนุญาตสำหรับ portfolio

## Runtime และ demo

ตรวจ GPU Dockerfile Python source และ CUDA/cuDNN compatibility ก่อนรัน Local; health ปัจจุบันไม่ได้ยืนยัน provider/GPU readiness

Next.js ยังไม่ครบ อย่ารัน scaffolder ทับ web/ ที่มี components แล้วโดยไม่ตรวจพฤติกรรม ประกอบในที่เดิมอย่างระมัดระวัง

ดู [Docker](docker.md), [model protocol](model-selection.md) และ [workshop](workshop-plan.md) สำหรับเกณฑ์ทดสอบ ไม่ใช้การล้าง Docker ทั้งเครื่องแก้ปัญหา disk แบบอัตโนมัติ
