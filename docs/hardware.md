# Hardware baseline — Buzzle

อัปเดตเอกสาร 2026-09-14 ข้อมูลต่อไปนี้ได้จากการตรวจเครื่องใน session วันเดียวกัน ไม่ได้ตรวจทรัพยากรสดซ้ำในรอบแก้เอกสาร

## ผลตรวจ

| รายการ | ค่าที่อ่านได้ |
|---|---|
| CPU | AMD Ryzen 5 PRO 4650G, 6 cores / 12 logical processors |
| RAM รวม | 15.87 GiB |
| RAM ว่างขณะตรวจ | 1.66 GiB — เปลี่ยนตามโปรแกรมที่เปิด |
| GPU | NVIDIA GeForce RTX 3050, compute capability 8.6 |
| VRAM รวม / ว่าง | 6144 / 4300 MiB ขณะตรวจ |
| NVIDIA driver | 560.94 |
| OS | Windows 11 Home 64-bit |
| Docker | Desktop 4.73.1, Engine 29.4.3, Linux/WSL2 |
| Docker VM resources | 12 CPUs, RAM 8,257,634,304 bytes (ประมาณ 7.69 GiB) |
| Runtime | Docker info แสดง nvidia runtime; ยังไม่ใช่ inference smoke test |

VRAM รวมประมาณ 6 GiB ไม่เท่ากับ VRAM ที่จัดสรรได้ทั้งหมด ใช้ nvidia-smi เป็นหลัก; WMI AdapterRAM อาจรายงานผิดสำหรับการ์ดขนาดใหญ่ ไม่สรุปว่าตัดที่ 4 GB ทุกกรณี

ข้อมูล disk/Node/Python บน host จากเอกสารเก่ายังไม่ได้ยืนยันใน session นี้ จึงไม่ใช้เป็นเงื่อนไขว่าเครื่องพร้อมทั้งหมด Python/FFmpeg ของระบบให้รันใน Docker

## การจัดทรัพยากรตามแผน

- ให้ ASR, diarization และ Local LLM รันทีละ stage ภายใต้ coordinator เดียว
- เริ่มคลิปสั้นแบบ quantized แล้ววัด peak RAM/VRAM ก่อนเพิ่มเป็น 30/60 นาที
- ปิดแอปหรือ workload อื่นตามที่ผู้ใช้เลือกเพื่อเพิ่มพื้นที่ว่าง โดยตรวจใหม่ก่อนโหลดโมเดล
- Memory limit ของ Docker ไม่ใช่ RAM ว่างที่รับประกันให้ container; host และ VM ต้องติดตามทั้งคู่
- CPU fallback อาจลด VRAM แต่เพิ่ม host RAM/เวลา ไม่เปิดโดยถือว่าปลอดภัยเสมอ
- ขนาด weights ไม่รวม context/KV cache/features/activation/runtime; ไม่มีตารางรับประกัน VRAM ต่อโมเดลก่อน benchmark
- เครื่องนี้ใช้ Local ได้เป็นเป้าหมายทดลอง ไม่จำเป็นต้องตัดสินใช้ Cloud เพียงเพราะรันทุกโมเดลพร้อมกันไม่ได้

Default candidate: Turbo INT8 และ Qwen 4B context จำกัด; pyannote Default Off หลัง core ผ่าน รายละเอียด [models](model-selection.md)

## ตรวจซ้ำแบบ read-only

รันจาก PowerShell บน host:

```powershell
Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv
docker info --format 'CPUs={{.NCPU}} MemoryBytes={{.MemTotal}} OSType={{.OSType}}'
docker stats --no-stream
Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,Size,SizeRemaining
```

Memory จาก Win32_OperatingSystem มีหน่วย KiB; จาก nvidia-smi เป็น MiB ตาม output ส่วน Docker MemoryBytes เป็น bytes

ถ้าสิทธิ์ WMI/Docker ถูกจำกัด ให้ขอสิทธิ์อ่านที่จำเป็น ไม่ตีความ Access denied ว่า Docker หรือ GPU ใช้ไม่ได้

## ก่อน model smoke test

ต้องทดสอบ GPU จาก container ของแอปด้วย inference จริงหลังแก้ image dependencies การเห็น nvidia runtime อย่างเดียวไม่พิสูจน์ว่า cuDNN/CTranslate2 เข้ากัน

เก็บ before/load/inference/after-unload memory และ cold/warm latency ไม่ตั้งเกณฑ์ “60 นาทีเสร็จใน 8 นาที” จนมีหลักฐาน

โปรเจกต์อยู่ใน OneDrive ตรวจการ sync ของไฟล์เสียง/model cache ถ้า Local mode ต้องการให้ข้อมูลอยู่ในเครื่อง Named volumes สำหรับ DB/model cache เป็นเป้าหมาย Docker โดยยังต้องมีแผนสำรองข้อมูล
