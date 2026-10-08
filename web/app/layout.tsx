import type { Metadata } from "next";
import Link from "next/link";
import { Bee } from "@/components/Bee";
import { MainNav } from "@/components/MainNav";
import "./globals.css";

export const metadata: Metadata = { title: "Buzzle — ถอดเสียงและสรุป", description: "เปลี่ยนบทสนทนาเป็นข้อความและสรุปที่กลับไปฟังต้นทางได้" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="th"><body><header className="masthead"><Link href="/" className="brand" aria-label="Buzzle หน้าหลัก"><Bee className="brand-bee"/>Buzzle<span>.</span></Link><span>ถอดเสียง · สรุป · กลับไปฟัง</span><MainNav/></header><main>{children}</main><footer>เก็บเสียงไว้ ทบทวนประเด็นได้ทุกเมื่อ <span>Buzzle / Portfolio workshop</span></footer></body></html>;
}
