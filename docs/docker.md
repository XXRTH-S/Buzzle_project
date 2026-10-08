# Docker workflow — Buzzle

Python และ FFmpeg รันผ่าน Docker ใช้ Compose เดิมเป็นฐาน เพิ่ม web และ Ollama ในขั้นพัฒนาถัดไป เอกสารนี้ไม่เปลี่ยน Dockerfiles/Compose และยังไม่ได้ build/run ในรอบจัดทำเอกสาร

## Services ปัจจุบัน

| Service | การใช้งาน | Port ที่ publish บน host |
|---|---|---|
| db | PostgreSQL | 55432 → 5432 |
| redis | Redis / RQ | 56379 → 6379 |
| api | FastAPI | 8100 → 8000 |
| worker | คิว cpu | ไม่มี |
| worker-gpu | คิว gpu, profile gpu | ไม่มี |
| web / ollama | ยังไม่มี Compose services | วางแผน web 3100; Ollama ใช้ internal network |

ภายใน Docker ใช้ db:5432 และ redis:6379 ตาม service DNS; browser บน host ใช้ localhost:8100 ไม่ใช่ api:8000

## เริ่ม backend เดิม

รันจาก root โปรเจกต์ และตรวจ .env ก่อนว่า provider/model/keys ตรงงานที่จะเรียก:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build db redis api worker
docker compose exec api python -m app.cli health
docker compose logs --tail 100 worker
```

ตั้ง PUBLIC_API_URL=http://localhost:8100 สำหรับ local browser upload ส่วน ASR/summary ยังเป็น Cloud default ตาม config เดิม Health ยังไม่ทดสอบ provider, Redis/GPU และ pipeline ครบ

คำสั่ง ingest/compare/summarize ใน [README](../README.md) อาจมีค่า API; การเปิด backend อย่างเดียวไม่เท่ากับทดสอบ inference

## GPU image: ต้องแก้และทดสอบก่อน

Compose มี worker-gpu และ GPU reservation แล้ว แต่ Dockerfile.gpu ใช้ Ubuntu 22.04 แล้วขอติดตั้ง python3.12 ผ่าน apt โดยไม่ได้เพิ่มแหล่งแพ็กเกจ Python ดังกล่าว ต้องตรวจหรือเปลี่ยนฐาน/วิธีติดตั้งให้รองรับจริง

ตรวจและ pin CUDA/cuDNN/CTranslate2/faster-whisper ให้เข้ากันตาม [faster-whisper requirements](https://github.com/SYSTRAN/faster-whisper) ไม่อ้างว่าเห็น nvidia-smi แล้ว inference จะผ่าน

หลังแก้ dependencies และตั้ง Local ASR config จึงใช้:

```powershell
docker compose --profile gpu up -d --build worker-gpu
docker compose logs --tail 100 worker-gpu
```

เปิด profile อย่างเดียวไม่เปลี่ยน ASR_BACKEND และยังไม่เพิ่ม Local LLM/diarization ให้ระบบ

## Compose เป้าหมาย

- ใช้ Python version เดียวที่ตรวจ compatibility ผ่านทั้ง CPU/GPU images ก่อน lock
- เพิ่ม web service จาก Next.js app ที่ประกอบแล้ว และ Ollama service พร้อม cache volume
- ใช้ named volumes สำหรับ DB/model caches; จำกัด mount ของ media/work ให้ชัด
- ทั้ง Whisper/pyannote/Ollama รับคำสั่งผ่าน GPU coordinator เดียว แม้อยู่คนละ process/container
- เพิ่ม readiness และตรวจโหลด/ปล่อยโมเดลจริง ตั้ง context และ concurrency ที่ผ่าน benchmark
- เก็บ keys ฝั่ง server; ไม่ใช้ NEXT_PUBLIC_* สำหรับ secrets และไม่ bake .env ลง image
- ลดการ publish db/redis/Ollama ที่ไม่จำเป็น; หาก demo online ต้องจัด auth/HTTPS ก่อน
- สร้าง versioned migrations; init schema.sql ทำงานเฉพาะ volume ใหม่ ห้ามใช้ลบ volume แทน migration

## Windows และพื้นที่เก็บข้อมูล

Host Windows/OneDrive bind mounts อาจมีต้นทุน I/O และ file watching ให้ทดสอบจริงก่อนตัดสินย้าย repo ใช้ Docker volume สำหรับข้อมูลเขียนหนักได้โดยไม่ต้องย้าย source ตอนนี้

การแก้ .wslconfig หรือ shutdown WSL กระทบ workload อื่นบนเครื่อง ให้ทำเมื่อมีเหตุจาก memory measurement และวางแผนร่วมกับผู้ใช้ ไม่เพิ่ม RAM limit จน host ไม่มีพื้นที่ทำงาน

ตรวจพื้นที่แบบ read-only ด้วย docker system df และ Get-Volume ก่อน download ไม่แนะนำล้าง Docker images/volumes ทั้งเครื่องเป็นขั้นตอนปกติของ workshop

## เป้าหมายการเริ่มระบบครั้งเดียว

หลังเพิ่ม services/config/migrations และทดสอบครบ ให้จัดคำสั่ง documented startup สำหรับ Local และ Cloud profiles ต่างหาก ปัจจุบันยังไม่มีคำสั่งเดียวที่เปิด Hybrid ครบทุกส่วน ดู [workshop plan](workshop-plan.md)
