"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Check, ChevronDown, ChevronUp, GripVertical, Lock, Plus, X } from "lucide-react";
import { MAX_PAGES, MAX_TOTAL_SECTIONS, PAGE_CATALOG, PageTemplate, SitePlan } from "@/types/generation";
import {
  EditablePage,
  EditableSection,
  addSection,
  createCustomPage,
  createPageFromCatalog,
  moveSection,
  planFromEditablePages,
  reorderSection,
  removeSection,
  seedEditablePages,
  suggestedSectionsFor,
} from "@/lib/page-plan-utils";

interface PageSectionManagerProps {
  plan: SitePlan;
  busy?: boolean;
  onSubmit: (plan: SitePlan) => void;
}

export function PageSectionManager({ plan, busy, onSubmit }: PageSectionManagerProps) {
  const [pages, setPages] = useState<EditablePage[]>(() => seedEditablePages(plan));
  const [seededPlan, setSeededPlan] = useState(plan);

  // Re-seed whenever a genuinely new plan arrives from the parent (initial
  // load, or after "Revise with AI") — not on every unrelated re-render,
  // since `plan` only gets a new reference from those two places. Adjusted
  // during render rather than in an effect (React's documented pattern for
  // resetting state on a prop change).
  if (plan !== seededPlan) {
    setSeededPlan(plan);
    setPages(seedEditablePages(plan));
  }

  const selectedPages = pages.filter((p) => p.selected);
  const selectedCount = selectedPages.length;
  const totalSections = selectedPages.reduce((sum, p) => sum + p.sections.length, 0);
  const remainingSections = Math.max(0, MAX_TOTAL_SECTIONS - totalSections);
  const atPageCap = selectedCount >= MAX_PAGES;

  function updatePage(id: string, updater: (p: EditablePage) => EditablePage) {
    setPages((prev) => prev.map((p) => (p.id === id ? updater(p) : p)));
  }

  /** Null means "fine to select". Checked before every path that can turn a
   * page on — the checkbox toggle, the catalog quick-add, and the custom
   * page form — so a page that was customized while unselected (which is
   * free to do, since its rows don't count until it's selected) can never
   * blow the section budget the instant it's switched on. */
  function blockedReason(page: EditablePage): string | null {
    if (page.selected) return null;
    if (atPageCap) return `You can pick up to ${MAX_PAGES} pages — remove one first`;
    if (page.sections.length > remainingSections) {
      return `This page has ${page.sections.length} sections but only ${remainingSections} are left in your ${MAX_TOTAL_SECTIONS}-section budget`;
    }
    return null;
  }

  function toggleSelected(page: EditablePage) {
    if (page.isHome || busy) return;
    if (page.selected) {
      updatePage(page.id, (p) => ({ ...p, selected: false }));
      return;
    }
    if (blockedReason(page)) return;
    updatePage(page.id, (p) => ({ ...p, selected: true }));
  }

  function handleAddSection(pageId: string, name: string) {
    if (remainingSections <= 0 || busy) return;
    updatePage(pageId, (p) => addSection(p, name));
  }

  function handleAddCatalogPage(template: PageTemplate) {
    if (busy || atPageCap) return;
    const sectionCount = template.defaultSections.length + 2; // + locked nav/footer
    if (sectionCount > remainingSections) return;
    setPages((prev) => [...prev, createPageFromCatalog(template, false, true)]);
  }

  function handleAddCustomPage(name: string) {
    if (busy || atPageCap || !name.trim()) return;
    if (remainingSections < 3) return; // a fresh custom page is nav + 1 starter + footer
    setPages((prev) => [...prev, createCustomPage(name.trim())]);
  }

  const existingNames = new Set(pages.map((p) => p.name.trim().toLowerCase()));
  const catalogPagesNotListed = PAGE_CATALOG.filter((t) => !existingNames.has(t.name.toLowerCase()));

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">Pick your pages</h2>
        <p className="text-sm text-muted-foreground">
          Select pages and drag sections to reorder them.{" "}
          <span className="font-medium text-foreground">
            {selectedCount} of {MAX_PAGES} pages selected
          </span>
        </p>
      </div>

      <div className="-mx-1 flex gap-4 overflow-x-auto px-1 pb-3">
        {pages.map((page) => (
          <PageCard
            key={page.id}
            page={page}
            busy={busy}
            blockedReason={blockedReason(page)}
            remainingSections={remainingSections}
            onToggleSelected={() => toggleSelected(page)}
            onAddSection={(name) => handleAddSection(page.id, name)}
            onRemoveSection={(sectionId) => updatePage(page.id, (p) => removeSection(p, sectionId))}
            onMoveSection={(sectionId, dir) => updatePage(page.id, (p) => moveSection(p, sectionId, dir))}
            onReorderSection={(fromId, toId) => updatePage(page.id, (p) => reorderSection(p, fromId, toId))}
          />
        ))}

        <AddPageCard
          disabled={atPageCap || busy}
          remainingSections={remainingSections}

          suggestions={catalogPagesNotListed}
          onAddCatalog={handleAddCatalogPage}
          onAddCustom={handleAddCustomPage}
        />
      </div>

      <Card className="flex flex-wrap items-center justify-between gap-4 bg-muted/30 p-4">
        <div>
          <p className="font-semibold">
            {selectedCount} page{selectedCount === 1 ? "" : "s"} · {totalSections} section
            {totalSections === 1 ? "" : "s"}
          </p>
          <p className="text-sm text-muted-foreground">
            {selectedPages.length > 0 ? selectedPages.map((p) => p.name).join(", ") : "No pages selected yet"}
          </p>
        </div>
        <Button
          size="lg"
          disabled={busy || selectedCount === 0}
          onClick={() => onSubmit(planFromEditablePages(pages))}
        >
          {busy ? "Building…" : "Review & Generate"}
        </Button>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------

function PageCard({
  page,
  busy,
  blockedReason,
  remainingSections,
  onToggleSelected,
  onAddSection,
  onRemoveSection,
  onMoveSection,
  onReorderSection,
}: {
  page: EditablePage;
  busy?: boolean;
  blockedReason: string | null;
  remainingSections: number;
  onToggleSelected: () => void;
  onAddSection: (name: string) => void;
  onRemoveSection: (sectionId: string) => void;
  onMoveSection: (sectionId: string, dir: "up" | "down") => void;
  onReorderSection: (fromId: string, toId: string) => void;
}) {
  const [draggingId, setDraggingId] = useState<string | null>(null);

  return (
    <Card
      className={cn(
        "flex w-[280px] shrink-0 flex-col overflow-hidden transition-colors",
        page.selected ? "border-primary/50" : "opacity-80"
      )}
    >
      <div className="flex items-center justify-between gap-2 px-4 pb-3 pt-4">
        <h3 className="truncate text-base font-semibold">{page.name}</h3>
        {page.isHome ? (
          <span
            title="Your homepage — always included"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
          >
            <Lock className="h-3.5 w-3.5" />
          </span>
        ) : (
          <button
            type="button"
            title={page.selected ? "Remove this page" : blockedReason ?? "Include this page"}
            disabled={(!page.selected && blockedReason !== null) || busy}
            onClick={onToggleSelected}
            className={cn(
              "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-40",
              page.selected
                ? "border-primary bg-primary text-primary-foreground"
                : "border-muted-foreground/40 text-transparent hover:border-muted-foreground"
            )}
          >
            <Check className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="border-t border-border" />

      <div className="flex flex-1 flex-col gap-2 p-3">
        {page.sections.map((section, index) => (
          <SectionRow
            key={section.id}
            section={section}
            isFirstEditable={index === 1}
            isLastEditable={index === page.sections.length - 2}
            dragging={draggingId === section.id}
            onDragStart={() => setDraggingId(section.id)}
            onDragEnd={() => setDraggingId(null)}
            onDropOn={() => {
              if (draggingId && draggingId !== section.id) onReorderSection(draggingId, section.id);
              setDraggingId(null);
            }}
            onRemove={() => onRemoveSection(section.id)}
            onMove={(dir) => onMoveSection(section.id, dir)}
          />
        ))}
      </div>

      <div className="p-3 pt-0">
        <AddSectionButton
          disabled={busy || remainingSections <= 0}
          remainingSections={remainingSections}
          suggestions={suggestedSectionsFor(page)}
          onAdd={onAddSection}
        />
      </div>
    </Card>
  );
}

function SectionRow({
  section,
  isFirstEditable,
  isLastEditable,
  dragging,
  onDragStart,
  onDragEnd,
  onDropOn,
  onRemove,
  onMove,
}: {
  section: EditableSection;
  isFirstEditable: boolean;
  isLastEditable: boolean;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDropOn: () => void;
  onRemove: () => void;
  onMove: (dir: "up" | "down") => void;
}) {
  if (section.locked) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-dashed border-border px-3 py-2.5 text-muted-foreground">
        <span className="flex items-center gap-2 text-sm">
          <Lock className="h-3.5 w-3.5" />
          {section.name}
        </span>
        <span className="text-[10px] font-semibold tracking-wide text-muted-foreground/70">LOCKED</span>
      </div>
    );
  }

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        onDropOn();
      }}
      className={cn(
        "flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-3 py-2.5 transition-opacity",
        dragging ? "opacity-40" : "opacity-100"
      )}
    >
      <span className="flex min-w-0 items-center gap-2 text-sm font-medium">
        <GripVertical className="h-4 w-4 shrink-0 cursor-grab text-muted-foreground active:cursor-grabbing" />
        <span className="truncate">{section.name}</span>
      </span>
      <span className="flex shrink-0 items-center gap-0.5">
        <button
          type="button"
          title="Move up"
          disabled={isFirstEditable}
          onClick={() => onMove("up")}
          className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronUp className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          title="Move down"
          disabled={isLastEditable}
          onClick={() => onMove("down")}
          className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          title="Remove section"
          onClick={onRemove}
          className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </span>
    </div>
  );
}

function AddSectionButton({
  disabled,
  remainingSections,
  suggestions,
  onAdd,
}: {
  disabled?: boolean;
  remainingSections: number;
  suggestions: string[];
  onAdd: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [customName, setCustomName] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, []);

  function submitCustom() {
    if (!customName.trim()) return;
    onAdd(customName.trim());
    setCustomName("");
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-2.5 text-sm text-muted-foreground transition-colors hover:border-muted-foreground hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Plus className="h-3.5 w-3.5" />
        Add section
      </button>

      {open ? (
        <div className="absolute bottom-full left-0 z-10 mb-1 w-64 rounded-lg border border-border bg-popover p-2 shadow-md">
          <p className="mb-1.5 px-1 text-[11px] text-muted-foreground">
            {remainingSections} section{remainingSections === 1 ? "" : "s"} left across your site
          </p>
          {suggestions.length > 0 ? (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {suggestions.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => {
                    onAdd(name);
                    setOpen(false);
                  }}
                  className="rounded-full border border-border px-2.5 py-1 text-xs hover:bg-accent"
                >
                  {name}
                </button>
              ))}
            </div>
          ) : null}
          <div className="flex gap-1.5">
            <input
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitCustom();
              }}
              placeholder="Custom section name…"
              className="h-8 flex-1 rounded-md border border-input bg-card px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button type="button" size="sm" className="h-8 px-2.5" disabled={!customName.trim()} onClick={submitCustom}>
              Add
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AddPageCard({
  disabled,
  remainingSections,
  suggestions,
  onAddCatalog,
  onAddCustom,
}: {
  disabled?: boolean;
  remainingSections: number;
  suggestions: PageTemplate[];
  onAddCatalog: (template: PageTemplate) => void;
  onAddCustom: (name: string) => void;
}) {
  const [customOpen, setCustomOpen] = useState(false);
  const [name, setName] = useState("");

  function submit() {
    if (!name.trim()) return;
    onAddCustom(name.trim());
    setName("");
    setCustomOpen(false);
  }

  return (
    <Card className="flex w-[280px] shrink-0 flex-col items-center justify-center gap-3 border-dashed p-5 text-center">
      <p className="text-sm font-medium">Add another page</p>
      <p className="text-xs text-muted-foreground">Up to {MAX_PAGES} pages total.</p>
      {!customOpen ? (
        <>
          {suggestions.length > 0 ? (
            <div className="flex flex-wrap justify-center gap-1.5">
              {suggestions.map((t) => {
                const rows = t.defaultSections.length + 2;
                const overBudget = rows > remainingSections;
                return (
                  <button
                    key={t.id}
                    type="button"
                    disabled={disabled || overBudget}
                    title={overBudget ? `Needs ${rows} sections, only ${remainingSections} left` : undefined}
                    onClick={() => onAddCatalog(t)}
                    className="rounded-full border border-border px-2.5 py-1 text-xs hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    + {t.name}
                  </button>
                );
              })}
            </div>
          ) : null}
          <Button type="button" variant="outline" size="sm" disabled={disabled || remainingSections < 3} onClick={() => setCustomOpen(true)}>
            Custom page…
          </Button>
        </>
      ) : (
        <div className="w-full space-y-2">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
            placeholder="Page name…"
            className="h-9 w-full rounded-md border border-input bg-card px-2.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <div className="flex justify-center gap-2">
            <Button type="button" size="sm" disabled={!name.trim()} onClick={submit}>
              Add
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setCustomOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
