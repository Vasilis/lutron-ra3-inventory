import { useMemo } from "react";
import { ChevronRight, Home } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAppStore } from "@/stores/app-store";
import { cn } from "@/lib/utils";
import type { Area, Device } from "@/lib/types";

interface AreaTreeProps {
  areas: Area[];
  areasByHref: Map<string, Area>;
  devicesByArea: Map<string | null, Device[]>;
}

interface AreaNode {
  area: Area;
  depth: number;
  deviceCount: number;
}

/** Build a depth-first flat list of areas ordered as a tree. */
function flattenTree(
  areas: Area[],
  devicesByArea: Map<string | null, Device[]>,
): AreaNode[] {
  const byParent = new Map<string | null, Area[]>();
  for (const a of areas) {
    const p = a.Parent?.href ?? null;
    const bucket = byParent.get(p) ?? [];
    bucket.push(a);
    byParent.set(p, bucket);
  }
  // Sort each level by Name.
  for (const list of byParent.values()) {
    list.sort((a, b) => (a.Name ?? "").localeCompare(b.Name ?? ""));
  }

  const out: AreaNode[] = [];
  const walk = (parent: string | null, depth: number) => {
    const kids = byParent.get(parent);
    if (!kids) return;
    for (const a of kids) {
      const own = devicesByArea.get(a.href)?.length ?? 0;
      out.push({ area: a, depth, deviceCount: own });
      walk(a.href, depth + 1);
    }
  };
  walk(null, 0);
  return out;
}

export function AreaTree({ areas, devicesByArea }: AreaTreeProps) {
  const selected = useAppStore((s) => s.selectedAreaHref);
  const setSelected = useAppStore((s) => s.setSelectedAreaHref);

  const nodes = useMemo(
    () => flattenTree(areas, devicesByArea),
    [areas, devicesByArea],
  );

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-0.5 p-3">
        <button
          type="button"
          onClick={() => setSelected(null)}
          className={cn(
            "flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors",
            selected === null
              ? "bg-accent text-accent-foreground"
              : "hover:bg-accent/50",
          )}
        >
          <Home className="size-4 shrink-0 text-muted-foreground" />
          <span className="flex-1 font-medium">All areas</span>
        </button>
        {nodes.map(({ area, depth, deviceCount }) => {
          const active = selected === area.href;
          return (
            <button
              key={area.href}
              type="button"
              onClick={() => setSelected(area.href)}
              className={cn(
                "group flex items-center gap-1 rounded-md px-2 py-2 text-left text-sm transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50",
              )}
              style={{ paddingLeft: `${0.5 + depth * 1.1}rem` }}
            >
              <ChevronRight
                className={cn(
                  "size-3.5 shrink-0",
                  active ? "text-foreground" : "text-muted-foreground/60",
                )}
              />
              <span className="flex-1 truncate">
                {area.Name ?? "(unnamed)"}
              </span>
              {deviceCount > 0 && (
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px] tabular-nums",
                    active
                      ? "bg-background/40"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {deviceCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}
