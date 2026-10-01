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
import type { Point } from "@/lib/measurements";
import styles from "./measure.module.css";

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface CanvasContext {
  toImage: (clientX: number, clientY: number) => Point;
  /** Size of one screen pixel in image pixels: handles stay the same size on screen whatever the zoom. */
  unit: number;
}

const Context = createContext<CanvasContext>({ toImage: (x, y) => ({ x, y }), unit: 1 });
export const useCanvas = () => useContext(Context);

const MAX_ZOOM = 12;

/** The photo in its own pixel coordinates, with zoom and pan by wheel, pinch and drag; a tap reports a point. */
export function PhotoCanvas({
  src,
  width,
  height,
  label,
  onTap,
  children,
}: {
  src: string;
  width: number;
  height: number;
  label: string;
  onTap?: (point: Point) => void;
  children?: ReactNode;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const [vb, setVb] = useState<ViewBox>({ x: 0, y: 0, w: width, h: height });
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef<{ moved: boolean; startDist: number; startVb: ViewBox } | null>(null);
  const [screenWidth, setScreenWidth] = useState(1);

  useEffect(() => setVb({ x: 0, y: 0, w: width, h: height }), [width, height]);
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
  }

  function onPointerMove(event: PointerEvent<SVGSVGElement>) {
    const previous = pointers.current.get(event.pointerId);
    if (!previous || !gesture.current) return;
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const scale = vb.w / Math.max(event.currentTarget.clientWidth || width, 1);
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
    pointers.current.delete(event.pointerId);
    if (wasTap && onTap) onTap(toImage(event.clientX, event.clientY));
    if (pointers.current.size === 0) gesture.current = null;
  }

  function onKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    const centre = { x: vb.x + vb.w / 2, y: vb.y + vb.h / 2 };
    if (event.key === "+" || event.key === "=") zoomAt(centre, 1.25);
    else if (event.key === "-") zoomAt(centre, 0.8);
    else if (event.key === "Enter" && onTap) onTap(centre);
    else return;
    event.preventDefault();
  }

  const unit = vb.w / Math.max(screenWidth, 1);
  return (
    <Context.Provider value={{ toImage, unit }}>
      <svg
        ref={svg}
        className={styles.canvas}
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
      </svg>
    </Context.Provider>
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
