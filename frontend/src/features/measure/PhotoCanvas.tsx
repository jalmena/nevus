import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  type WheelEvent,
} from "react";
import { Lasso, Move, ZoomIn, ZoomOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Point } from "@/lib/measurements";
import styles from "./measure.module.css";

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** A view as fractions of the photo, so two photos of different sizes can share one zoom and pan. */
export type SharedView = ViewBox;
export const WHOLE: SharedView = { x: 0, y: 0, w: 1, h: 1 };

interface CanvasContext {
  toImage: (clientX: number, clientY: number) => Point;
  /** Size of one screen pixel in image pixels: handles stay the same size on screen whatever the zoom. */
  unit: number;
  /** The visible part of the photo, in its pixels. */
  view: ViewBox;
}

const Context = createContext<CanvasContext>({
  toImage: (x, y) => ({ x, y }),
  unit: 1,
  view: { x: 0, y: 0, w: 1, h: 1 },
});
export const useCanvas = () => useContext(Context);

const MAX_ZOOM = 12;
const PAN_KEYS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
};

/** The most points an outline may carry (the API's limit); a longer trace keeps every n-th point. */
const MAX_OUTLINE_POINTS = 400;

/**
 * The photo in its own pixel coordinates, with zoom and pan by wheel, pinch and drag; a tap reports a point.
 * With `tools`, buttons over the photo zoom in and out and, given `onDraw`, switch a drag between moving the
 * photo and tracing an outline by hand.
 */
export function PhotoCanvas({
  src,
  width,
  height,
  label,
  onTap,
  view,
  onViewChange,
  tools = false,
  drawing = false,
  onDrawingChange,
  onDraw,
  children,
}: {
  src: string;
  width: number;
  height: number;
  label: string;
  onTap?: (point: Point) => void;
  /** Controlled zoom and pan, shared with another canvas. */
  view?: SharedView;
  onViewChange?: (view: SharedView) => void;
  tools?: boolean;
  /** A drag traces an outline instead of moving the photo. */
  drawing?: boolean;
  onDrawingChange?: (drawing: boolean) => void;
  /** The finished trace, in image pixels. */
  onDraw?: (points: Point[]) => void;
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  const svg = useRef<SVGSVGElement>(null);
  const [ownVb, setOwnVb] = useState<ViewBox>({ x: 0, y: 0, w: width, h: height });
  const vb: ViewBox = view
    ? { x: view.x * width, y: view.y * height, w: view.w * width, h: view.h * height }
    : ownVb;
  const latest = useRef(vb);
  useEffect(() => {
    latest.current = vb;
  });
  const setVb = useCallback(
    (next: ViewBox | ((current: ViewBox) => ViewBox)) => {
      const value = typeof next === "function" ? next(latest.current) : next;
      latest.current = value;
      if (onViewChange) {
        onViewChange({ x: value.x / width, y: value.y / height, w: value.w / width, h: value.h / height });
      }
      if (!view) setOwnVb(value);
    },
    [onViewChange, view, width, height],
  );
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef<{ moved: boolean; startDist: number; startVb: ViewBox } | null>(null);
  const [screenWidth, setScreenWidth] = useState(1);
  const [trace, setTrace] = useState<Point[] | null>(null);
  const tracing = useRef<Point[] | null>(null);

  useEffect(() => setOwnVb({ x: 0, y: 0, w: width, h: height }), [width, height]);
  useEffect(() => {
    const element = svg.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => setScreenWidth(element.clientWidth || 1));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const clamp = useCallback(
    (next: ViewBox): ViewBox => {
      const w = Math.min(width, Math.max(width / MAX_ZOOM, next.w));
      const h = (w * height) / width;
      return {
        w,
        h,
        x: Math.min(Math.max(0, next.x), width - w),
        y: Math.min(Math.max(0, next.y), height - h),
      };
    },
    [width, height],
  );

  const toImage = useCallback((clientX: number, clientY: number): Point => {
    const element = svg.current;
    const ctm = element?.getScreenCTM?.();
    if (!element || !ctm) return { x: clientX, y: clientY };
    const inverse = ctm.inverse();
    return {
      x: inverse.a * clientX + inverse.c * clientY + inverse.e,
      y: inverse.b * clientX + inverse.d * clientY + inverse.f,
    };
  }, []);

  function zoomAt(point: Point, factor: number) {
    setVb((current) => {
      const w = current.w / factor;
      const h = current.h / factor;
      return clamp({
        x: point.x - (point.x - current.x) / factor,
        y: point.y - (point.y - current.y) / factor,
        w,
        h,
      });
    });
  }

  function onWheel(event: WheelEvent<SVGSVGElement>) {
    event.preventDefault();
    zoomAt(toImage(event.clientX, event.clientY), event.deltaY < 0 ? 1.25 : 0.8);
  }

  function onPointerDown(event: PointerEvent<SVGSVGElement>) {
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const [a, b] = [...pointers.current.values()];
    gesture.current = {
      moved: pointers.current.size > 1,
      startDist: a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0,
      startVb: vb,
    };
    // Drawing: one finger traces; a second one turns the gesture back into a pinch.
    tracing.current = drawing && pointers.current.size === 1 ? [toImage(event.clientX, event.clientY)] : null;
    setTrace(tracing.current);
  }

  function onPointerMove(event: PointerEvent<SVGSVGElement>) {
    const previous = pointers.current.get(event.pointerId);
    if (!previous || !gesture.current) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const scale = vb.w / Math.max(event.currentTarget.clientWidth || width, 1);
    if (tracing.current && pointers.current.size === 1) {
      const point = toImage(event.clientX, event.clientY);
      const last = tracing.current[tracing.current.length - 1];
      if (last && Math.hypot(point.x - last.x, point.y - last.y) / scale < 2) return; // every 2 screen pixels
      tracing.current = [...tracing.current, point];
      if (tracing.current.length > 3) gesture.current.moved = true;
      setTrace(tracing.current);
      return;
    }
    if (pointers.current.size === 1) {
      const dx = event.clientX - previous.x;
      const dy = event.clientY - previous.y;
      if (Math.abs(dx) + Math.abs(dy) > 0 && (gesture.current.moved || Math.hypot(dx, dy) > 4)) {
        gesture.current.moved = true;
        setVb((current) => clamp({ ...current, x: current.x - dx * scale, y: current.y - dy * scale }));
      }
    } else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      if (!a || !b || gesture.current.startDist === 0) return;
      const factor = Math.hypot(a.x - b.x, a.y - b.y) / gesture.current.startDist;
      const mid = toImage((a.x + b.x) / 2, (a.y + b.y) / 2);
      const start = gesture.current.startVb;
      const w = start.w / factor;
      setVb(
        clamp({
          x: mid.x - (mid.x - start.x) / factor,
          y: mid.y - (mid.y - start.y) / factor,
          w,
          h: start.h / factor,
        }),
      );
    }
  }

  function onPointerUp(event: PointerEvent<SVGSVGElement>) {
    const wasTap = pointers.current.size === 1 && gesture.current && !gesture.current.moved;
    const traced = tracing.current;
    tracing.current = null;
    setTrace(null);
    if (traced && traced.length >= 8 && onDraw) {
      const every = Math.ceil(traced.length / MAX_OUTLINE_POINTS);
      onDraw(traced.filter((_, index) => index % every === 0));
    }
    pointers.current.delete(event.pointerId);
    if (wasTap && onTap) onTap(toImage(event.clientX, event.clientY));
    if (pointers.current.size === 0) gesture.current = null;
  }

  function onKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    const centre = { x: vb.x + vb.w / 2, y: vb.y + vb.h / 2 };
    const pan = PAN_KEYS[event.key];
    if (event.key === "+" || event.key === "=") zoomAt(centre, 1.25);
    else if (event.key === "-") zoomAt(centre, 0.8);
    else if (event.key === "Enter" && onTap) onTap(centre);
    else if (pan) {
      // A tenth of the view per press; handles keep their own arrow keys.
      setVb((current) =>
        clamp({
          ...current,
          x: current.x + pan[0] * current.w * 0.1,
          y: current.y + pan[1] * current.h * 0.1,
        }),
      );
    } else return;
    event.preventDefault();
  }

  const unit = vb.w / Math.max(screenWidth, 1);
  const centre = { x: vb.x + vb.w / 2, y: vb.y + vb.h / 2 };
  const canvas = (
    <Context.Provider value={{ toImage, unit, view: vb }}>
      <svg
        ref={svg}
        className={[styles.canvas, onDrawingChange && !drawing ? styles.canvasPan : ""].join(" ")}
        viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
        role="application"
        aria-label={label}
        tabIndex={0}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onKeyDown={onKeyDown}
      >
        <image href={src} x={0} y={0} width={width} height={height} preserveAspectRatio="none" />
        {children}
        {trace && trace.length > 1 && (
          <polyline
            className={styles.trace}
            points={trace.map((p) => `${p.x},${p.y}`).join(" ")}
            strokeWidth={2 * unit}
            aria-hidden="true"
          />
        )}
      </svg>
    </Context.Provider>
  );
  if (!tools) return canvas;
  return (
    <div className={styles.canvasWrap}>
      {canvas}
      <div className={styles.tools}>
        <button
          type="button"
          onClick={() => zoomAt(centre, 1.5)}
          disabled={vb.w <= width / MAX_ZOOM + 0.5}
          aria-label={t("bodymap.zoomIn")}
          title={t("bodymap.zoomIn")}
        >
          <ZoomIn aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => zoomAt(centre, 1 / 1.5)}
          disabled={vb.w >= width - 0.5}
          aria-label={t("bodymap.zoomOut")}
          title={t("bodymap.zoomOut")}
        >
          <ZoomOut aria-hidden="true" />
        </button>
        {onDrawingChange && (
          // The button shows what a press does: start drawing (a lasso) or go back to moving (the arrows).
          <button
            type="button"
            className={drawing ? styles.toolActive : ""}
            onClick={() => onDrawingChange(!drawing)}
            aria-label={drawing ? t("measure.pan") : t("measure.draw")}
            title={drawing ? t("measure.pan") : t("measure.draw")}
          >
            {drawing ? <Move aria-hidden="true" /> : <Lasso aria-hidden="true" />}
          </button>
        )}
      </div>
    </div>
  );
}

/** A draggable point: pointer drag, or arrow keys (Shift for bigger steps). */
export function Handle({
  x,
  y,
  label,
  onMove,
  step = 2,
}: {
  x: number;
  y: number;
  label: string;
  onMove: (point: Point) => void;
  step?: number;
}) {
  const { toImage, unit } = useCanvas();
  const dragging = useRef(false);

  function onPointerDown(event: PointerEvent<SVGCircleElement>) {
    event.stopPropagation();
    dragging.current = true;
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }
  function onPointerMove(event: PointerEvent<SVGCircleElement>) {
    if (!dragging.current) return;
    event.stopPropagation();
    onMove(toImage(event.clientX, event.clientY));
  }
  function onPointerUp(event: PointerEvent<SVGCircleElement>) {
    event.stopPropagation();
    dragging.current = false;
  }
  function onKeyDown(event: KeyboardEvent<SVGCircleElement>) {
    const d = (event.shiftKey ? 10 : 1) * step;
    const moves: Record<string, Point> = {
      ArrowLeft: { x: x - d, y },
      ArrowRight: { x: x + d, y },
      ArrowUp: { x, y: y - d },
      ArrowDown: { x, y: y + d },
    };
    const next = moves[event.key];
    if (next) {
      event.preventDefault();
      event.stopPropagation();
      onMove(next);
    }
  }
  return (
    <circle
      className={styles.handle}
      cx={x}
      cy={y}
      r={11 * unit}
      strokeWidth={2 * unit}
      role="slider"
      aria-label={label}
      aria-valuetext={`${Math.round(x)}, ${Math.round(y)}`}
      tabIndex={0}
      data-handle
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onKeyDown={onKeyDown}
    />
  );
}
