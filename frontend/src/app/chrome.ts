import { useEffect, useSyncExternalStore, type ReactNode } from "react";
import type { MenuItem } from "@/design-system/components/Menu";

/** An icon action in the app bar: a button, or a link when it navigates. */
export interface ChromeAction {
  key: string;
  label: string;
  icon: ReactNode;
  onClick?: () => void;
  to?: string;
  showLabel?: boolean | "desktop";
  disabled?: boolean;
}

export interface ChromePrimary {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  pending?: boolean;
}

export interface RailItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
}

/**
 * What a page asks the shell to show around it: the way back, the title that appears once the
 * page's own heading scrolls away, at most two icon actions, the "more" menu, the one primary
 * action (the bottom bar on a phone, the app bar on a desktop), a help sheet, and the context
 * block of the desktop rail.
 */
export interface Chrome {
  back?: { to: string; label: string };
  title?: string;
  actions?: ChromeAction[];
  menu?: MenuItem[];
  primary?: ChromePrimary;
  secondary?: { label: string; onClick: () => void };
  /** Replaces the primary in the bar while the page waits for a tap (placing a mark). */
  instruction?: string;
  help?: { title: string; content: ReactNode };
  rail?: { heading: string; items: RailItem[] };
}

let chrome: Chrome = {};
let titleInView = true;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function setChrome(next: Chrome) {
  chrome = next;
  emit();
}

export function setTitleInView(value: boolean) {
  if (titleInView === value) return;
  titleInView = value;
  emit();
}

export function useChrome(): Chrome {
  return useSyncExternalStore(
    subscribe,
    () => chrome,
    () => chrome,
  );
}

export function useTitleInView(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => titleInView,
    () => titleInView,
  );
}

/** A page declares its chrome on every render and clears it when it leaves. */
export function usePageChrome(next: Chrome) {
  useEffect(() => {
    setChrome(next);
  });
  useEffect(() => {
    return () => {
      setChrome({});
      setTitleInView(true);
    };
  }, []);
}

/** Whether a media query matches now; false where the browser cannot say (tests). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (listener) => {
      const media = typeof window !== "undefined" && window.matchMedia ? window.matchMedia(query) : null;
      if (!media) return () => undefined;
      media.addEventListener("change", listener);
      return () => media.removeEventListener("change", listener);
    },
    () => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia(query).matches : false),
    () => false,
  );
}
