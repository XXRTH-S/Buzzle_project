"use client";

import {
  stamp,
  type KeyPoints,
  type Summary,
  type Timeline,
  type StructuredSummary,
} from "@/lib/api";

const KIND_LABEL: Record<string, string> = {
  topic: "หัวข้อ",
  decision: "ตัดสินใจ",
  assignment: "มอบหมาย",
  blocker: "ติดปัญหา",
  schedule: "นัดหมาย",
};

/** เรนเดอร์ได้ทั้งสองเทมเพลต — ทุกจุดที่มีเวลา คลิกแล้ว seek ไปที่ ms นั้น */
export function SummaryView({
  summary,
  onSeek,
}: {
  summary: Summary;
  onSeek: (ms: number) => void;
}) {
  const body =
    summary.template_id === "timeline" ? (
      <TimelineBody data={summary.payload as Timeline} onSeek={onSeek} />
    ) : "sections" in summary.payload ? (
      <StructuredSummaryBody data={summary.payload as StructuredSummary}/>
    ) : (
      <KeyPointsBody data={summary.payload as KeyPoints} onSeek={onSeek} />
    );

  return (
    <section className="summary-document" aria-label="ผลสรุป">
      {body}
      <details className="summary-metadata"><summary>รายละเอียดการสร้างสรุป</summary>
        <p>โมเดล: {summary.model}</p>
        <p>โทเคนเข้า {summary.usage.input_tokens ?? "—"} · โทเคนออก {summary.usage.output_tokens ?? "—"} · แคช {summary.usage.cache_read_tokens ?? "—"}</p>
      </details>
    </section>
  );
}

export function StructuredSummaryBody({data}: {data: StructuredSummary}) {
  return <div className="structured-summary summary-content"><h3 className="summary-headline">{data.headline}</h3><p className="summary-intro">{data.summary}</p>
    {Object.entries(data.sections).map(([title,items])=><section className="summary-block" key={title}><h4>{title}</h4>{items.length?<ul>{items.map((item,i)=><li key={i}>{item}</li>)}</ul>:<p className="summary-empty">ไม่พบข้อมูลส่วนนี้ในข้อความถอดเสียง</p>}</section>)}
  </div>;
}

function KeyPointsBody({
  data,
  onSeek,
}: {
  data: KeyPoints;
  onSeek: (ms: number) => void;
}) {
  return (
    <div className="summary-content">
      <h3 className="summary-headline">{data.headline}</h3>
      <p className="summary-intro">{data.summary}</p>

      <Group title="การตัดสินใจ" empty="ไม่มีการตัดสินใจที่จบในไฟล์นี้">
        {data.decisions.map((d, i) => (
          <li key={i}>{d}</li>
        ))}
      </Group>

      <Group title="งานที่ต้องทำ" empty="ไม่มีงานที่มอบหมายชัดเจน">
        {data.action_items.map((a, i) => (
          <li key={i} className="summary-action">
            <button
              onClick={() => onSeek(a.cite_ms)}
              className="summary-time"
              aria-label={`ฟังต้นฉบับเวลา ${stamp(a.cite_ms)}`}
            >
              {stamp(a.cite_ms)}
            </button>
            <p>{a.task}</p>
            <div className="action-meta"><span>ผู้รับผิดชอบ: {a.owner}</span>
            {a.due && <span>กำหนดส่ง: {a.due}</span>}</div>
          </li>
        ))}
      </Group>

      <Group title="ยังไม่ได้ข้อสรุป" empty="ไม่มี">
        {data.open_questions.map((q, i) => (
          <li key={i}>{q}</li>
        ))}
      </Group>
    </div>
  );
}

function TimelineBody({
  data,
  onSeek,
}: {
  data: Timeline;
  onSeek: (ms: number) => void;
}) {
  return (
    <div className="summary-content">
      <h3 className="summary-headline">{data.headline}</h3>
      <ol className="summary-timeline">
        {data.entries.map((e, i) => (
          <li key={i}>
            <div className="timeline-heading">
              <button
                onClick={() => onSeek(e.at_ms)}
                className="summary-time"
                aria-label={`ฟังต้นฉบับเวลา ${stamp(e.at_ms)}`}
              >
                {stamp(e.at_ms)}
              </button>
              <span className="timeline-kind">
                {KIND_LABEL[e.kind] ?? e.kind}
              </span>
              <h4>{e.title}</h4>
            </div>
            <p>{e.detail}</p>
            {e.speaker && (
              <p className="mt-0.5 font-mono text-xs text-neutral-400">
                {e.speaker}
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Group({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string;
  children: React.ReactNode[];
}) {
  return (
    <section className="summary-block">
      <h4>
        {title}
      </h4>
      {children.length === 0 ? (
        <p className="summary-empty">{empty}</p>
      ) : (
        <ul>{children}</ul>
      )}
    </section>
  );
}
