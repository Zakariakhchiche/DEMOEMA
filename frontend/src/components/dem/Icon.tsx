"use client";

const PATHS: Record<string, string> = {
  plus: "M12 5v14M5 12h14",
  menu: "M3 6h18M3 12h18M3 18h18",
  search: "M11 19a8 8 0 1 1 0-16 8 8 0 0 1 0 16Zm10 2-4.35-4.35",
  sparkles: "M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1",
  bell: "M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M9 21h6",
  bookmark: "M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z",
  chart: "M3 3v18h18M7 14l4-4 4 4 5-7",
  table: "M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18",
  network: "M5 6a3 3 0 1 1 6 0 3 3 0 0 1-6 0Zm0 12a3 3 0 1 1 6 0 3 3 0 0 1-6 0Zm8-6a3 3 0 1 1 6 0 3 3 0 0 1-6 0M11 8l5 2M11 16l5-2",
  chat: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  send: "M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.4l2-1.6-2-3.4-2.4.9a7 7 0 0 0-2.4-1.4L14 2h-4l-.5 2.6a7 7 0 0 0-2.4 1.4l-2.4-.9-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.8l-2 1.6 2 3.4 2.4-.9a7 7 0 0 0 2.4 1.4L10 22h4l.5-2.6a7 7 0 0 0 2.4-1.4l2.4.9 2-3.4-2-1.6c.1-.5.1-.9.1-1.4Z",
  paperclip: "M21 12.5 13 20.5a5 5 0 0 1-7-7l8-8a3.5 3.5 0 0 1 5 5l-8 8a2 2 0 0 1-3-3l7-7",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  chevronDown: "m6 9 6 6 6-6",
  chevronRight: "m9 6 6 6-6 6",
  chevronLeft: "m15 6-6 6 6 6",
  close: "M18 6 6 18M6 6l12 12",
  user: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6",
  save: "M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2ZM17 21v-8H7v8M7 3v5h8",
  warning: "M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0ZM12 9v4M12 17h.01",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z",
  check: "M20 6 9 17l-5-5",
  filter: "M22 3H2l8 9.46V19l4 2v-8.54z",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  eye: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12ZM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  arrowRight: "M5 12h14M12 5l7 7-7 7",
  pin: "M12 17v5M9 10.76V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4.76l3 4.24H6z",
  history: "M3 12a9 9 0 1 0 9-9c-2.5 0-4.7 1-6.4 2.6L3 8M3 3v5h5",
  folder: "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
  layers: "M12 2 2 7l10 5 10-5-10-5ZM2 17l10 5 10-5M2 12l10 5 10-5",
  star: "M12 2l3 7 7 .8-5 5L18 22l-6-3-6 3 1-7-5-5L9 9z",
  refresh: "M21 12a9 9 0 0 1-15 6.7L3 16M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M3 21v-5h5",
  book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15zM4 19.5A2.5 2.5 0 0 0 6.5 22H20",
  trash: "M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2",
  arrowUp: "M12 19V5M5 12l7-7 7 7",
  coffee: "M17 8h1a4 4 0 1 1 0 8h-1M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4zM6 1v3M10 1v3M14 1v3",
  kanban: "M3 3h6v18H3zM10 3h4v12h-4zM15 3h6v8h-6z",
  "chevron-right": "M9 18l6-6-6-6",
  "chevron-down": "M6 9l6 6 6-6",
  more: "M12 12h.01M19 12h.01M5 12h.01",
  moon: "M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z",
  sun: "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41M12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10z",
  play: "M5 3l14 9-14 9V3z",
  cpu: "M9 3h6v3h3v3h3v6h-3v3h-3v3H9v-3H6v-3H3V9h3V6h3z M9 9h6v6H9z",
  info: "M12 8h.01M11 12h1v4h1M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  link: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
};

interface Props {
  name: string;
  size?: number;
  color?: string;
  strokeWidth?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function Icon({ name, size = 14, color = "currentColor", strokeWidth = 1.75, className, style }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ display: "block", flexShrink: 0, ...style }}
      aria-hidden
    >
      <path d={PATHS[name] || ""} />
    </svg>
  );
}
