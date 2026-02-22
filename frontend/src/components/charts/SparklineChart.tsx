/**
 * SparklineChart — Lightweight inline SVG sparkline.
 *
 * Pure SVG, not Recharts. Used inline in MetricCards and wherever
 * a minimal, performant trend indicator is needed.
 */
import React, { useMemo } from 'react';

export interface SparklineChartProps {
  /** Array of numeric values to plot. */
  data: number[];
  /** Override the auto-detected trend color. */
  color?: string;
  /** SVG height in pixels. Defaults to 40. */
  height?: number;
  /** Show area fill beneath the line. Defaults to true. */
  showArea?: boolean;
  /** Enable CSS path-draw animation on mount. Defaults to true. */
  animated?: boolean;
  /** Additional className for the outer <svg>. */
  className?: string;
}

// Semantic colors — never themed, per DESIGN_GUIDE §4.3
const COLOR_GAIN = '#2ECC71';
const COLOR_LOSS = '#E74C3C';

function normalize(values: number[]): number[] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;
  if (range === 0) return values.map(() => 0.5);
  return values.map((v) => (v - min) / range);
}

export const SparklineChart: React.FC<SparklineChartProps> = ({
  data,
  color,
  height = 40,
  showArea = true,
  animated = true,
  className,
}) => {
  // Handle empty / single-point data gracefully
  const points = data.length > 1 ? data : data.length === 1 ? [data[0], data[0]] : [];

  const { polylinePoints, polygonPoints, strokeColor, gradientId } = useMemo(() => {
    if (points.length === 0) {
      return { polylinePoints: '', polygonPoints: '', strokeColor: COLOR_GAIN, gradientId: 'sg-empty' };
    }

    const normalised = normalize(points);
    const width = 100; // Use viewBox units — responsive by default
    const padding = 2;
    const plotHeight = height - padding * 2;

    const coords = normalised.map((y, i) => {
      const x = (i / (normalised.length - 1)) * width;
      // Flip y: SVG 0 is top, so high value → small y
      const svgY = padding + plotHeight * (1 - y);
      return `${x.toFixed(2)},${svgY.toFixed(2)}`;
    });

    const polyline = coords.join(' ');

    // Polygon for area fill: close at bottom-right → bottom-left
    const firstX = '0';
    const lastX = width.toFixed(2);
    const bottom = (height - padding).toFixed(2);
    const polygon = `${firstX},${bottom} ${polyline} ${lastX},${bottom}`;

    // Use first-to-last trend for color
    const trend = points[points.length - 1] >= points[0];
    const stroke = color ?? (trend ? COLOR_GAIN : COLOR_LOSS);
    const id = `sg-${stroke.replace('#', '')}-${points.length}`;

    return { polylinePoints: polyline, polygonPoints: polygon, strokeColor: stroke, gradientId: id };
  }, [points, height, color]);

  if (points.length === 0) {
    return (
      <svg
        className={className}
        width="100%"
        height={height}
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        aria-hidden="true"
      />
    );
  }

  return (
    <svg
      className={className}
      width="100%"
      height={height}
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        {/* Gradient fill fades to transparent at bottom for area fill */}
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity={0.25} />
          <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
        </linearGradient>

        {/* Mask to fade horizontally at edges for a soft blend into card background */}
        <linearGradient id={`${gradientId}-fade`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="white" stopOpacity={0} />
          <stop offset="8%" stopColor="white" stopOpacity={1} />
          <stop offset="92%" stopColor="white" stopOpacity={1} />
          <stop offset="100%" stopColor="white" stopOpacity={0} />
        </linearGradient>
        <mask id={`${gradientId}-mask`}>
          <rect width="100%" height="100%" fill={`url(#${gradientId}-fade)`} />
        </mask>
      </defs>

      <g mask={`url(#${gradientId}-mask)`}>
        {/* Area fill */}
        {showArea && (
          <polygon
            points={polygonPoints}
            fill={`url(#${gradientId})`}
          />
        )}

        {/* Line */}
        <polyline
          points={polylinePoints}
          fill="none"
          stroke={strokeColor}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={animated ? 'sparkline-draw' : undefined}
        />
      </g>
    </svg>
  );
};
