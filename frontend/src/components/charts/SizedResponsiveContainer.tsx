import React, { useState, useEffect, useRef } from 'react';

type ResponsiveDimension = number | `${number}%`;

// All Recharts chart roots (PieChart, AreaChart, LineChart, etc.) accept
// explicit width/height as props — this type reflects that contract.
interface SizedResponsiveContainerProps {
  width?: ResponsiveDimension;
  height?: ResponsiveDimension;
  children: React.ReactElement<{ width?: number; height?: number }>;
}

/**
 * Drop-in replacement for Recharts ResponsiveContainer that eliminates the
 * width(-1)/height(-1) warning.
 *
 * Strategy: ResponsiveContainer always fires that warning on its own first
 * internal measurement pass because it starts with -1 before its ResizeObserver
 * fires. This component bypasses ResponsiveContainer entirely — it measures the
 * wrapper div with its own ResizeObserver after the browser's first layout pass,
 * then passes explicit pixel dimensions directly to the chart via cloneElement.
 * Recharts receives real numbers immediately and never emits the warning.
 */
export const SizedResponsiveContainer: React.FC<SizedResponsiveContainerProps> = ({
  width = "100%",
  height = "100%",
  children,
}) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;

    const measure = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setDims(prev => {
          const w = Math.floor(rect.width);
          const h = Math.floor(rect.height);
          // Avoid unnecessary re-renders when nothing changed
          if (prev && prev.width === w && prev.height === h) return prev;
          return { width: w, height: h };
        });
      }
    };

    // Measure immediately (fires after useEffect, post-paint — real dimensions)
    measure();

    // Re-measure on every container resize (e.g. window resize, panel collapse)
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={wrapperRef} style={{ width, height }}>
      {dims
        ? React.cloneElement(children, { width: dims.width, height: dims.height })
        : null
      }
    </div>
  );
};
