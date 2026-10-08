# OpenRouter Free — ตัวสรุปปัจจุบัน

เปลี่ยน default summary provider เป็น OpenRouter แล้ว ใช้ HTTPX ที่มีอยู่และตรวจผลด้วย Pydantic schemas เดิม ทั้ง key_points และ timeline ยังใช้ API ของ Buzzle รูปแบบเดิม

## ตั้งค่า

สร้าง API key ที่ [OpenRouter keys](https://openrouter.ai/settings/keys) แล้วใส่ใน .env ของ checkout ที่ต้องการรัน:

```dotenv
SUMMARY_PROVIDER=openrouter
SUMMARY_MODEL=openrouter/free
OPENROUTER_API_KEY=ใส่คีย์ของคุณที่นี่
SUMMARY_MAX_TOKENS=4096
SUMMARY_TIMEOUT_SECONDS=180
```

openrouter/free เลือกจากโมเดลฟรีที่มีและรองรับ parameters ที่ร้องขอ จึงอาจได้โมเดลต่างกันในแต่ละครั้ง หากต้องการเทียบผลซ้ำให้เลือก model ID ที่มีรุ่น :free จริงจาก [รายการโมเดลฟรี](https://openrouter.ai/collections/free-models)

Adapter รับเฉพาะ openrouter/free หรือชื่อที่ลงท้าย :free ไม่ fallback ไปโมเดลเสียเงินหรือ Anthropic อัตโนมัติ และไม่ retry network/429 เอง เพื่อไม่ใช้โควตาซ้ำโดยไม่ทราบผล

ยังต้องใช้ ELEVENLABS_API_KEY หาก ASR_BACKEND=scribe ค่าสรุปฟรีไม่ได้ทำให้การถอดเสียงผ่าน Scribe ฟรีด้วย ส่วน ANTHROPIC_API_KEY ไม่จำเป็นเมื่อ SUMMARY_PROVIDER=openrouter

## ข้อจำกัดของบริการฟรี

- มี rate limits และ availability เปลี่ยนได้ ไม่รับประกัน latency สำหรับ demo
- Model/router จะเลือก endpoint ที่รองรับ JSON schema ตาม require_parameters หากไม่มีจะรายงานข้อผิดพลาด ไม่ลดเงื่อนไข structured output แบบเงียบ ๆ
- ข้อความยาวอาจเกิน context ของโมเดลที่เลือก ส่วน chunking/map-reduce ยังเป็นงานในแผน จึงยังไม่รับประกันสรุปทุกไฟล์ 60 นาที
- ข้อความถอดเสียงถูกส่งไป OpenRouter และ inference provider ที่ได้รับเลือก ตรวจ data settings/เงื่อนไขของบริการก่อนใช้ข้อมูลจริง การเปลี่ยนนี้เป็น Cloud summary ไม่ใช่ Local inference
- เพิ่ม token limit ได้ภายในขอบเขต config แต่ไม่แก้ input ที่เกิน context และใช้โควตา/เวลามากขึ้น

แหล่งทางการ: [Free router](https://openrouter.ai/docs/guides/routing/routers/free-router), [FAQ และโควตา](https://openrouter.ai/docs/faq), [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)

## ผลลัพธ์และ cache

ส่ง JSON schema ของแต่ละ template แบบ strict แล้ว validate อีกครั้งในแอป ไม่บันทึกผลที่ขาด ถูกปฏิเสธ หรือหยุดเพราะ token limit ข้อผิดพลาดไม่แสดง raw response ที่อาจมีข้อความส่วนตัว

เก็บ prompt/completion/cache tokens ถ้ามี และบันทึก model เป็น openrouter:<requested model> -> <actual model> เพื่อเห็นว่า free router เลือกโมเดลใด เมื่อขอสรุปใหม่หลังเปลี่ยน provider/model จะไม่ใช้ cache ของ Claude/โมเดลเดิม อย่างไรก็ตาม transcript revision cache และ duplicate job lease ยังเป็นงานค้างตาม architecture

GET /health และ CLI health แสดง summary_provider, summary_model และสถานะ summary key โดยไม่เผยค่าคีย์ การมีคีย์ไม่เท่ากับยืนยันว่า API key ใช้งานได้

## ทดสอบและเปิดใช้งาน

Tests ใช้ unittest และ mock HTTP ไม่ต้องมีคีย์จริงและไม่เรียก API ภายนอก:

```powershell
docker compose exec -T api python -m unittest discover -s app/tests -v
```

คำสั่งนี้ใช้ได้เมื่อ container mount app/ ของ checkout นี้เท่านั้น พบระหว่างตรวจว่าบริการชื่อ buzzle_project-api-1 ที่เปิดอยู่ mount C:\Users\PC\Buzzle_project\app แต่ checkout ที่แก้คือโฟลเดอร์ OneDrive อย่า recreate บริการชื่อเดียวกันโดยไม่ตรวจ mount, media path และ DB volume ก่อน

หลังเลือก checkout และ Compose project ที่ต้องการรันแล้ว ให้สร้าง api/worker ใหม่เพื่อโหลด env ที่เปลี่ยน; docker restart อย่างเดียวไม่โหลด env_file ใหม่ เก็บ DB/media เดิมให้ถูกชุด ไม่ต้องเปลี่ยนบริการ RAG อื่น

รอบนี้ยืนยันด้วย container ทดสอบแยกที่ mount source แบบ read-only และปิด network เท่านั้น ยังไม่ทดสอบ live API เพราะ OPENROUTER_API_KEY ยังว่าง และยังไม่ได้สลับ running service จากอีก checkout
