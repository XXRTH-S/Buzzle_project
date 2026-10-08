# การเลือกโมเดล — Buzzle

อัปเดต 2026-09-14 นี่คือ shortlist สำหรับ RTX 3050 6 GB ไม่ใช่ผล benchmark ยังไม่มีตัวเลขยืนยันว่าโมเดลใดแม่นหรือเร็วที่สุดบนเสียงชุดนี้

## Candidates

| งาน | Candidate | เงื่อนไข |
|---|---|---|
| Local ASR | Whisper large-v3-turbo ผ่าน faster-whisper, int8_float16 | เริ่ม batch 1/ไม่ใช้ large batch; วัดไทยและ peak memory |
| ASR fallback | Whisper small หรือ medium multilingual quantized | เทียบจริง; ไม่สมมติว่า medium ประหยัดกว่า Turbo ทุกกรณี |
| Local summary | qwen3.5:4b Q4_K_M ผ่าน Ollama | context จำกัดและ map-reduce |
| Summary alternative | qwen3:4b Q4_K_M หรือโมเดลเล็กลง | ทดสอบเมื่อ baseline memory/quality ไม่ผ่าน |
| Local speakers | pyannote/speaker-diarization-community-1 | optional Default Off หลัง core ผ่าน |
| Cloud ASR | ElevenLabs Scribe v2 | diarization ใน API; วัดไฟล์เดียวกับ Local |
| Cloud summary — default ปัจจุบัน | OpenRouter openrouter/free | ใช้เฉพาะโมเดลฟรีและ JSON schema; ยังไม่วัดคุณภาพไทยจริง |
| Cloud summary — optional | Claude ผ่าน adapter เดิม | เลือก model ID ที่บัญชีรองรับและผ่าน rubric/งบ |

โค้ดปัจจุบันส่ง scribe_v1, summary_provider เป็น openrouter, summary_model เป็น openrouter/free และ Local ASR ตั้ง biodatlab/whisper-th-medium-combined ตัวสรุป OpenRouter ผ่าน offline mock tests แต่ยังไม่ได้ทดสอบคีย์จริงหรือ benchmark ดู [คู่มือตั้งค่า](openrouter.md)

## โมเดลกับ engine

Whisper คือโมเดล; faster-whisper ใช้ CTranslate2 รัน เลือก checkpoint ที่เป็น CTranslate2-compatible หรือ conversion ที่ทดสอบแล้ว ไม่ป้อน Hugging Face checkpoint ทุกชนิดเข้า WhisperModel โดยสมมติว่าใช้ได้

Qwen คือโมเดล; Ollama คือ runtime/API; pyannote.audio โหลด Community-1 pipeline ต้อง pin engine versions, model revision/digest และ dependencies หลังทดสอบ

Turbo กับ large-v3 เต็มเป็นคนละ candidate ไม่ใช้ VRAM ของรุ่นหนึ่งตัดสินอีกตัว รายงาน int8/int8_float16 แยกกัน

## Resource policy

- หนึ่ง GPU stage ทั้งระบบ: Whisper → unload → optional pyannote → unload → Ollama
- จำกัด Ollama ทั้ง model count และ request parallelism และใช้ coordinator ร่วมกับ Whisper
- เริ่ม summary context ประมาณ 4096 tokens เป็นค่าทดลอง ต้องเผื่อ system/schema/output ไม่ใส่ input จนเต็ม
- แบ่งข้อความตาม tokens และ segment boundaries เก็บ source IDs ผ่าน map/reduce ทุกชั้น
- Artifact Qwen3.5 4B ประมาณ 3.4 GB; Qwen3 4B ประมาณ 2.5 GB ตามหน้ารุ่นที่อ้างอิง ไม่ใช่ peak VRAM
- ไฟล์ยาวเพิ่ม RAM จาก decode/features/diarization ต้องวัด host/container/GPU และ swap
- ลดโมเดล/context เมื่อ OOM ตาม policy ไม่สลับ Cloud อัตโนมัติ

ดู [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Qwen3.5 4B](https://ollama.com/library/qwen3.5:4b) และ [Qwen3 4B](https://ollama.com/library/qwen3:4b)

## เลือกตามเป้าหมาย

| เป้าหมาย | ทางที่ทดลอง | Tradeoff |
|---|---|---|
| Local ไม่มี API key | Whisper + Qwen | จัด memory/context และรอ inference |
| สรุปซับซ้อน ถอดเสียงในเครื่อง | Whisper + Cloud LLM | ส่งข้อความและมีค่า API |
| Online demo ไม่ผูก GPU เครื่องพัฒนา | Scribe + Cloud LLM | network/credits และการจัดการข้อมูล |
| ผู้พูดในเครื่อง | Whisper + Community-1 sequential | เวลาเพิ่มและ speaker consistency |
| Fine-tune ไทยภายหลัง | Thonburian/checkpoint ไทยที่ตรวจ format/license | ยังไม่เพิ่ม dependency ก่อน baseline ผ่าน |

Community-1 รองรับ CPU/GPU และ offline หลังเตรียมโมเดล แต่ไม่ได้รับประกัน peak memory บนเครื่องนี้ ดู [model card](https://huggingface.co/pyannote/speaker-diarization-community-1)

## Benchmark protocol

1. เตรียมเสียงที่ได้รับอนุญาต: ไทย/ปนอังกฤษ ชัด ก้อง ชื่อเฉพาะ เงียบ และพูดทับ แยกคลิปปรับค่ากับ held-out clips
2. ใช้ไฟล์/preprocessing เดียวกันเทียบ ASR แยกเวลา ASR จาก diarization/summary
3. รายงาน cold run (โหลดโมเดล) และ warm run แยกกัน ทำซ้ำคลิปสั้นอย่างน้อย 3 ครั้ง
4. ทดสอบ 30/60 นาทีสำหรับ memory/recovery ไม่สรุปความพร้อมจากคลิปสั้น
5. เทียบ LLM ด้วย gold transcript เดียวกันก่อน แล้วเทียบ end-to-end ด้วย ASR output
6. บันทึก model revision, engine versions, compute, batch/beam, context, prompt/template และ resource state

| Metric | วิธีรายงาน |
|---|---|
| ASR | CER พร้อม normalization คงที่; WER ระบุ Thai tokenizer/version |
| Speakers | DER ระบุ overlap/collar protocol และตรวจ speaker turns ด้วยคน |
| Timestamp | ต้น/กลาง/ท้าย, out-of-range และ mapping กลับเสียง |
| Summary | coverage, unsupported claims, decisions, owner/deadline และหลักฐาน |
| Schema | pass rate/retries; JSON ผ่านไม่เท่ากับเนื้อหาถูก |
| Latency | upload, queue wait, load, ASR, speakers, summary และ end-to-end |
| RTF | processing seconds / audio seconds ระบุ stages ที่รวม |
| Resources | peak VRAM, host/container RAM, swap, disk และ failures |
| Cost | billed audio, tokens/cache, retries และ plan fees แยกกัน |

## ผลที่ต้องเติมหลังรัน

| Configuration | 5 นาที | 30 นาที | 60 นาที | Quality / memory / cost |
|---|---|---|---|---|
| Local ASR + Local summary | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด |
| Local + speakers + Local summary | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด |
| Local ASR + Cloud summary | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด |
| Cloud ASR + Cloud summary | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด | ยังไม่วัด |

เลือก default ที่ทำงานจบใน memory budget และผ่าน quality rubric แล้วเทียบความเร็ว/ต้นทุน เป้าเดิม 8 นาทีต่อเสียงหนึ่งชั่วโมงยังไม่มีหลักฐานและไม่ใช้เป็น promise

## ต้นทุน

ไม่ตรึงยอดต่อชั่วโมงจากราคาเก่า ค่า Cloud ขึ้นกับ plan, feature, usage และ retry:

- ASR = billed duration × rate ของ plan + add-ons
- LLM = input/cache-write/cache-read/output usage × rate ที่ตรงชนิด + retry
- Infrastructure = hosting/storage/network + plan fees ที่จัดสรร
- Local = ค่าไฟ/เครื่อง/เวลา; ไม่มีค่า API เมื่อทั้ง storage/inference เป็น local

เก็บ rate source, วันที่และสกุลเงิน ไม่แปลง USD เป็นบาทด้วยอัตราคงที่ และไม่รับประกันว่า prompt cache ทำให้เทมเพลตที่สองเกือบฟรี ตรวจ [ElevenLabs pricing](https://elevenlabs.io/pricing/api) และ [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing) ก่อนใช้จริง

## License และ attribution

| Artifact | License ที่ระบุในแหล่งอ้างอิง | ก่อนเผยแพร่ |
|---|---|---|
| Whisper large-v3-turbo | MIT | เก็บ copyright/license notice และตรวจ revision |
| faster-whisper | MIT | เก็บ library/dependency notices ที่แจกจ่าย |
| Qwen3.5 4B / Qwen3 4B ที่เลือก | Apache 2.0 | แนบ license/notice และระบุการแก้ไขเมื่อมี |
| Community-1 | CC BY 4.0 | เครดิต ลิงก์ license การแก้ไข และรับเงื่อนไขดาวน์โหลด |
| Cloud APIs | Terms ของ provider | ตรวจบัญชี ค่าใช้จ่าย retention และการประมวลผลข้อมูล |

License ของโมเดลไม่ให้สิทธิ์เผยแพร่เสียงคนอื่น ใช้เสียงที่ได้รับอนุญาตและไม่ใส่ keys/audio ส่วนตัวใน repository

## แหล่งหลัก

- [OpenRouter Free router](https://openrouter.ai/docs/guides/routing/routers/free-router)
- [Whisper Turbo](https://huggingface.co/openai/whisper-large-v3-turbo)
- [faster-whisper GPU requirements](https://github.com/SYSTRAN/faster-whisper)
- [Qwen3.5 4B](https://ollama.com/library/qwen3.5:4b)
- [Qwen3 4B](https://ollama.com/library/qwen3:4b)
- [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)
- [Scribe capabilities](https://elevenlabs.io/docs/overview/capabilities/speech-to-text)
- [Transcription API](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)

ข้อมูลอ้างอิงมาจากการตรวจในบทสนทนา ไม่แทน compatibility test หรือ benchmark ของ Buzzle
