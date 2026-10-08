# Buzzle

เว็บถอดเสียงและสรุปการประชุมสำหรับ portfolio และ workshop: อัปโหลดเสียง → อ่าน transcript พร้อมเวลา → เลือกสรุปสาระสำคัญหรือ Timeline → คลิกกลับไปฟังต้นทาง

## สถานะและแนวทาง

อัปเดต 2026-09-14: เป้าหมายคือ **Hybrid โดยใช้ Local เป็นค่าเริ่มต้น** และเลือก Cloud แยกสำหรับการถอดเสียงและการสรุป รองรับไฟล์ 30–60 นาที ทำงานแบบ batch ทีละงาน GPU

อัปเดตโค้ด 2026-09-15: Next.js production build ผ่านแล้ว และ backend tests ใน Docker ผ่าน 24 ข้อ รวม integration กับ PostgreSQL, Redis/RQ และ FFmpeg โดยจำลอง ASR/LLM ยังไม่ได้ benchmark โมเดลหรือไฟล์จริง 30–60 นาที ดู [สถานะการส่งมอบ](docs/implementation-status.md) ก่อนเริ่มรัน

| ส่วน | มีในโค้ดปัจจุบัน | งานที่ยังต้องทำ |
|---|---|---|
| Backend | FastAPI, RQ, Redis, PostgreSQL, CLI, SSE และ per-media advisory lock | ทดสอบ lifecycle จริง, durable outbox และ crash recovery |
| ASR | Scribe และ faster-whisper adapters; default เป็น Scribe | Local default, เลือกต่อ job, บันทึก model/revision |
| Cloud ASR | โค้ดส่ง scribe_v1 | ตรวจและเปลี่ยนเป็น scribe_v2 ก่อน benchmark |
| สรุป | OpenRouter free + optional Claude, schemas และ template registry | Ollama adapter, chunking และหลักฐานระดับ segment |
| ผู้พูด | ได้จาก Scribe; Local คืน speaker ว่าง | pyannote Community-1 แบบเลือกเปิดหลัง core ผ่าน |
| หน้าเว็บ | Next.js pages, upload/history, transcript editor และสองเทมเพลต; Docker preview 3210 เชื่อม API จริงผ่าน | ทดสอบโมเดลจริงและไฟล์ 30–60 นาที |
| ไฟล์ | bounded local upload 500 MiB, playback, cleanup, ตรวจระยะเวลา 60 นาที | ทดสอบไฟล์จริง, S3 upload limit และ signed playback |
| ทดสอบ | CLI compare และ offline OpenRouter unit tests ใน Docker | gold set, automated tests และรายงาน benchmark |

## OpenRouter Free ที่เพิ่มแล้ว

Summary default ปัจจุบันคือ SUMMARY_PROVIDER=openrouter และ SUMMARY_MODEL=openrouter/free ใส่ OPENROUTER_API_KEY ใน .env โดยดู [คู่มือตั้งค่า OpenRouter](docs/openrouter.md) ใช้ได้ทั้งสองเทมเพลต แต่ยังต้องมี Scribe key หากใช้ Cloud ASR

ทดสอบ adapter ด้วย mock ใน Docker แบบปิด network แล้ว ยังไม่ได้ทดสอบ live API หรือ Local inference บริการ Buzzle ที่เปิดอยู่พบว่า mount โค้ดจาก C:\\Users\\PC\\Buzzle_project ซึ่งเป็นคนละ checkout กับไฟล์ใน OneDrive ที่แก้รอบนี้

## โหมดเป้าหมาย

| โหมด | ถอดเสียง / ผู้พูด | สรุป | เหมาะกับ |
|---|---|---|---|
| Local — default ตามแผน | Whisper; pyannote เป็นตัวเลือก | Qwen ผ่าน Ollama | เรียนรู้ GPU/Docker และใช้ข้อมูลในเครื่อง |
| Hybrid | Whisper; pyannote เป็นตัวเลือก | Cloud LLM | ส่งเฉพาะข้อความที่จำเป็นเพื่อสรุป |
| Cloud | Scribe พร้อม diarization | Cloud LLM | เดโมออนไลน์และเปรียบเทียบผล |

ASR และ LLM เลือกแยกต่อ job ได้ในเป้าหมาย ระบบต้องไม่ส่งไป Cloud อัตโนมัติเมื่อ Local ล้มเหลว การมี API key ไม่เท่ากับเลือกส่งข้อมูล

## Stack ที่รักษาไว้

| ชั้น | เทคโนโลยี | เหตุผล |
|---|---|---|
| Web | Next.js, TypeScript, Tailwind, native HTML audio | audio seek โดยไม่ decode waveform ทั้งชั่วโมงใน browser |
| API | FastAPI, Pydantic | ใช้ API และ schemas เดิม |
| Queue | RQ + Redis | เพียงพอสำหรับ batch workshop; ยังไม่ต้องย้าย Celery |
| Data | PostgreSQL + psycopg | เก็บ transcript, jobs, summaries และ revisions |
| Audio | FFmpeg; VAD ตาม backend | normalize โดยรักษาเวลาต้นฉบับ |
| Local ASR | faster-whisper / CTranslate2 | ทดลอง Turbo INT8 และ fallback ขนาดเล็ก |
| Local summary | Ollama + Qwen 4B — ต้องเพิ่ม | แบ่งข้อความตาม token budget |
| Local speakers | Community-1 — ต้องเพิ่ม | เป็นขั้นเสริมหลังปล่อย ASR |
| Runtime | Docker Compose | Python/FFmpeg ใน container; เพิ่ม web/Ollama ตามแผน |
| Storage | local volume ก่อน; S3/R2 เป็นตัวเลือก | เริ่มในเครื่องก่อนขยาย online |

## โครงสร้างปัจจุบัน

```text
app/
  main.py, config.py, cli.py
  db.py, schema.sql, storage.py, queue.py, events.py
  audio/                 FFmpeg normalize และตรวจช่วงเสียง
  asr/                   interface, registry, Scribe, local Whisper
  summaries/             schemas, templates, OpenRouter/Claude runners
  tasks/pipeline.py      normalize → asr → join → summarize
  routers/               media, segments, summaries, SSE
web/
  components/            Uploader, TemplatePicker, SummaryView, Player
  lib/                   API types และ progress hook
docker/
  Dockerfile.py
  Dockerfile.gpu
docs/
docker-compose.yml
requirements.txt
```

Diarization module, summary provider registry, migrations และ benchmark harness เป็นงานที่จะเพิ่ม

## เครื่องเป้าหมาย

ตรวจใน session วันที่ 2026-09-14: Ryzen 5 PRO 4650G (6C/12T), RAM 15.87 GiB, RTX 3050 6144 MiB และ Docker Linux VM เห็น RAM ประมาณ 7.69 GiB ขณะตรวจ host RAM ว่าง 1.66 GiB และ VRAM ว่าง 4300 MiB ตัวเลขว่างเปลี่ยนได้ตลอด

ใช้ GPU ทีละโมเดล: ASR → ปล่อยทรัพยากร → diarization ถ้าเลือก → ปล่อยทรัพยากร → Local summary ขนาดไฟล์โมเดลไม่เท่ากับ peak VRAM และยังไม่รับประกันว่าเสียงหนึ่งชั่วโมงจะเสร็จใน 8 นาที ดู [hardware](docs/hardware.md)

## เริ่มตรวจ backend ปัจจุบัน

คำสั่งนี้อ้าง services ที่มีจริง ใช้จาก root ของโปรเจกต์ ยังไม่ใช่การเปิด Hybrid ครบระบบ และยังไม่ได้รันในรอบเอกสารนี้

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build db redis api worker
docker compose exec api python -m app.cli health
```

ตรวจ .env ด้วยตนเอง: ASR default ต้องใช้ ElevenLabs key และ summary default ต้องใช้ OPENROUTER_API_KEY (ไม่ต้องมี Anthropic key); model ID/SDK ต้องทดสอบกับบัญชีจริงก่อนเรียกงานที่มีค่าใช้จ่าย ตั้ง PUBLIC_API_URL=http://localhost:8100 สำหรับ browser บนเครื่องนี้ เพราะ config default เดิมใช้ 8000 แต่ Compose publish 8100

- API: [localhost:8100](http://localhost:8100)
- Swagger: [localhost:8100/docs](http://localhost:8100/docs)
- Web เป้าหมาย: port 3100; ต้องประกอบตาม [web README](web/README.md)
- Health ปัจจุบันยังไม่ยืนยันว่า GPU/provider/pipeline ผ่านครบ

CLI ที่มีอยู่ (อาจเรียก API ตาม config):

```powershell
docker compose exec api python -m app.cli ingest /srv/media/in/meeting.m4a --language th
docker compose logs -f worker
docker compose exec api python -m app.cli compare /srv/media/in/clip.wav --backends scribe --language th
```

วางไฟล์ที่ได้รับอนุญาตใน media/in/ ก่อนใช้ CLI ส่วน GPU image ต้องแก้/ตรวจ Python, CUDA, cuDNN และ CTranslate2 ก่อนถือว่าใช้ได้ ดู [Docker](docs/docker.md)

## เทมเพลตสรุป

| ID | ผลลัพธ์ | หลักฐานเป้าหมาย |
|---|---|---|
| key_points | ภาพรวม, การตัดสินใจ, งานที่ต้องทำ, ประเด็นค้าง | segment จริง; ไม่เดา owner/deadline |
| timeline | เหตุการณ์เรียงตามเวลา | timestamp จาก segment จริง |

เปลี่ยนเทมเพลตใช้ transcript เดิม แก้ transcript แล้วต้องทำเครื่องหมายสรุปเก่าว่าล้าสมัย Cache เป้าหมายต้องรวม revision, template version, provider/model ดู [templates](docs/summary-templates.md)

## เกณฑ์ผ่านก่อนเดโม

- Local path ใช้ได้โดยไม่ต้องมี Cloud key หลังเตรียมโมเดล/dependencies
- ไฟล์ 30/60 นาทีจบ หรือแจ้งข้อจำกัดโดยไม่ทำ transcript ที่สำเร็จแล้วหาย
- Timestamp อยู่ภายในไฟล์และคลิกต้น/กลาง/ท้ายได้
- สองเทมเพลตผ่าน schema และตรวจความตรงกับหลักฐานด้วยคน
- กดซ้ำ/retry ไม่รันขั้นเดียวกันซ้อน; restart แล้วกู้สถานะได้
- รายงานเวลา CER/WER, ผู้พูดเมื่อเปิด, peak RAM/VRAM และ usage จริง
- Demo สดใช้คลิป 2–5 นาที พร้อมผล 30/60 นาทีที่ระบุว่าเตรียมล่วงหน้า

## เอกสารและลำดับพัฒนา

| เอกสาร | เนื้อหา |
|---|---|
| [Workshop plan](docs/workshop-plan.md) | milestones, labs และ acceptance |
| [Architecture](docs/architecture.md) | pipeline, GPU ownership, data model และ API |
| [OpenRouter setup](docs/openrouter.md) | คีย์ โมเดลฟรี และข้อจำกัด |
| [Model selection](docs/model-selection.md) | candidates, licenses, benchmark และต้นทุน |
| [Hardware](docs/hardware.md) | baseline และวิธีตรวจทรัพยากร |
| [Docker](docs/docker.md) | commands ปัจจุบันและ services เป้าหมาย |
| [Templates](docs/summary-templates.md) | schema, citations, revisions และ cache |
| [Pitfalls](docs/pitfalls.md) | ข้อผิดพลาดที่ต้องทดสอบ |

เริ่มแก้ pipeline → ประกอบเว็บ → Local ASR/LLM → templates/evidence → optional diarization → Cloud opt-in → benchmark และ demo โดยรักษาโค้ดที่ใช้ต่อได้

## ข้อมูลส่วนตัวและเครดิต

ใช้เสียงของตนเองหรือได้รับอนุญาต เก็บ keys ใน .env และไม่เผยแพร่ media/ การลบต้องครอบคลุมต้นฉบับ ไฟล์ชั่วคราว DB และงานที่ยังรันอยู่ Retention/Cloud consent ยังต้องพัฒนา

เพิ่ม Models & Attribution และ license notices ตาม [model selection](docs/model-selection.md) Local mode ต้องใช้ทั้ง storage และ inference ในเครื่องด้วย ตรวจการ sync ของ OneDrive ก่อนใช้ข้อมูลจริง
