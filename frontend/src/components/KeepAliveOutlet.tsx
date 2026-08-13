import { useLocation, useOutlet } from "react-router-dom";
import { useRef, type ReactNode } from "react";

/** Keep the last N route outlets mounted so switching only toggles visibility. */
export function KeepAliveOutlet({ max = 6 }: { max?: number }) {
  const outlet = useOutlet();
  const { pathname } = useLocation();
  const cacheRef = useRef<Map<string, ReactNode>>(new Map());

  if (outlet) {
    const next = new Map(cacheRef.current);
    next.delete(pathname);
    next.set(pathname, outlet);
    while (next.size > max) {
      const oldest = next.keys().next().value as string | undefined;
      if (!oldest) break;
      next.delete(oldest);
    }
    cacheRef.current = next;
  }

  return (
    <>
      {[...cacheRef.current.entries()].map(([path, node]) => {
        const active = path === pathname;
        return (
          <div
            key={path}
            hidden={!active}
            aria-hidden={!active}
            className={active ? "qa-page-enter" : undefined}
          >
            {node}
          </div>
        );
      })}
    </>
  );
}
