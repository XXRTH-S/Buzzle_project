# Buzzle — หน้าเว็บ

เพิ่ม Next.js app/pages/config แล้ว และ production build ผ่านเมื่อ 2026-09-15 ดูสถานะล่าสุดและข้อจำกัดที่ [implementation-status](../docs/implementation-status.md)

## สิ่งที่ใช้ต่อ

| ไฟล์ | งาน |
|---|---|
| lib/api.ts | API calls และ types |
| lib/useProgress.ts | SSE progress |
| components/Uploader.tsx | สร้างงาน อัปโหลด เริ่ม pipeline |
| components/TemplatePicker.tsx | ปุ่มจาก template registry |
| components/SummaryView.tsx | สาระสำคัญ/Timeline และ seek callback |
| components/Player.tsx | player/transcript component |

## แผนเดิมและงานต่อยอด

1. เพิ่ม package/config, root layout, global styles และ dependencies ที่เข้ากันใน web/ โดยรักษาไฟล์เดิม
2. ทำหน้า upload/history และ app/media/[id]/page.tsx สำหรับงานแต่ละไฟล์
3. เชื่อม status snapshot + SSE, playback endpoint, edit transcript และสอง templates
4. เพิ่ม ASR/summary selectors ตาม backend capabilities พร้อม Local default และ Cloud opt-in ที่ระบุข้อมูลจะส่ง
5. แสดง pending/failed/stale states และให้เปิด transcript ต่อได้เมื่อ summary/diarization ล้มเหลว
6. เพิ่ม web service ใน Docker Compose และทดสอบ flow จริงก่อนประกาศว่าคำสั่ง startup พร้อม

ไม่ใช้ create-next-app ทับโฟลเดอร์นี้โดยสมมติว่าตอบ No แล้วจะรวมไฟล์ให้ การสร้าง scaffold หากจำเป็นให้ทำในโฟลเดอร์ชั่วคราวและตรวจ diff ก่อนรวม

## URL และการรันตามเป้าหมาย

Web ใช้ host port 3100; browser API ใช้ http://localhost:8100 และ PUBLIC_API_URL ฝั่ง backend ต้องตรงกันเพื่อสร้าง local upload URL

NEXT_PUBLIC_API เป็น public URL ไม่ใช่ที่เก็บ API keys ถ้ามี server-side fetch ใน Docker ให้ใช้ service DNS ที่ต่างจาก browser URL และจัด config ให้ชัด

ตอนนี้ใช้ `npm ci`, `npm run build`, `npm run dev` ในโฟลเดอร์ web ได้แล้ว Docker web ใน compose.preview.yml build และเชื่อม API จริงผ่าน โดย preview ใช้ http://localhost:3210 หน้าเว็บใช้ polling ทุก 3 วินาที; SSE hook เก็บไว้สำหรับขั้นต่อไป

## UX สำหรับ portfolio

ใช้คลิป 2–5 นาที demo สด พร้อมผลไฟล์ 30/60 นาทีที่ติดป้ายว่าเตรียมล่วงหน้า คลิกเวลาไปเสียงต้นทาง และแสดงประโยชน์ของสองเทมเพลต

แสดง diagnostics ของ provider/model/tokens ในรายละเอียดเทคนิค ส่วนสรุปหลักเน้นเนื้อหาและหลักฐาน ไม่แสดง cache miss เป็น error แก่ผู้ใช้ทั่วไป

ดู [README](../README.md), [architecture](../docs/architecture.md) และ [workshop plan](../docs/workshop-plan.md)
