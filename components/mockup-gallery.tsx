"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { MockupDesign } from "@/types/generation";

const FRAME_W = 1200;
const FRAME_H = 700;

/** Renders a fixed 1200x700 mockup iframe scaled down to fit whatever width
 * its container actually ends up at (grid columns are responsive, so a
 * static CSS scale would only be correct at one viewport width). */
function ScaledThumb({ html, title }: { html: string; title: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.25);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setScale(el.clientWidth / FRAME_W);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={containerRef} className="relative w-full overflow-hidden bg-white" style={{ aspectRatio: `${FRAME_W} / ${FRAME_H}` }}>
      <div
        className="absolute left-0 top-0 origin-top-left"
        style={{ width: FRAME_W, height: FRAME_H, transform: `scale(${scale})` }}
      >
        <iframe srcDoc={html} className="pointer-events-none h-full w-full border-0" title={title} scrolling="no" />
      </div>
    </div>
  );
}

interface MockupGalleryProps {
  mockups: MockupDesign[];
  onChoose: (mockup: MockupDesign) => void;
  busy?: boolean;
}

export function MockupGallery({ mockups, onChoose, busy }: MockupGalleryProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <div>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {mockups.map((m) => {
          const selected = selectedId === m.id;
          return (
            <Card
              key={m.id}
              className={cn(
                "overflow-hidden border transition-colors",
                selected ? "border-primary ring-1 ring-primary" : "border-border"
              )}
            >
              <div className="flex items-center justify-between border-b bg-muted/40 px-3 py-2">
                <span className="text-sm font-medium">{m.label}</span>
                <button
                  type="button"
                  className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
                  onClick={() => setOpenId(openId === m.id ? null : m.id)}
                >
                  {openId === m.id ? "shrink" : "view full size"}
                </button>
              </div>
              {openId === m.id ? (
                <div className="h-[640px] w-full">
                  <iframe srcDoc={m.html} className="h-full w-full border-0" title={m.label} />
                </div>
              ) : (
                <ScaledThumb html={m.html} title={m.label} />
              )}
              <div className="flex items-center justify-between p-3">
                <p className="pr-3 text-xs text-muted-foreground">{m.direction}</p>
                <Button
                  size="sm"
                  variant={selected ? "default" : "outline"}
                  disabled={busy}
                  onClick={() => {
                    setSelectedId(m.id);
                    onChoose(m);
                  }}
                >
                  Use this design
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
