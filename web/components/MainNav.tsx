"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function MainNav() {
  const home = usePathname() === "/";
  return <nav className="main-nav" aria-label="เมนูหลัก">
    <Link href="/#files" className="nav-link">ไฟล์ของคุณ</Link>
    <Link href="/" className="nav-link home-link" aria-label="Home · หน้าแรก" title="กลับหน้าแรก" aria-current={home ? "page" : undefined}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/></svg>
    </Link>
  </nav>;
}
