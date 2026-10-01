import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Notice } from "@/design-system/components/Notice";
import { imageUrl } from "@/lib/images";
import styles from "./capture.module.css";

/** Live capture needs a secure context; the native camera through a file input always works. */
export function liveCameraAvailable(): boolean {
  return typeof window !== "undefined" && window.isSecureContext && !!navigator.mediaDevices?.getUserMedia;
}

interface TorchCapabilities extends MediaTrackCapabilities {
  torch?: boolean;
}

/**
 * The camera with guides: the previous close-up as a translucent ghost to match framing and
 * distance, and a circle where the reference card's window should sit. Nothing is analysed here.
 */
export function LiveCamera({
  previousImageId,
  onCapture,
  onClose,
}: {
  previousImageId?: string | null;
  onCapture: (file: File) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ghost, setGhost] = useState(0.35);
  const [torch, setTorch] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 4096 }, height: { ideal: 3072 } },
        audio: false,
      })
      .then((media) => {
        if (cancelled) {
          media.getTracks().forEach((track) => track.stop());
          return;
        }
        stream.current = media;
        if (video.current) {
          video.current.srcObject = media;
          void video.current.play();
        }
        const track = media.getVideoTracks()[0];
        const capabilities = track?.getCapabilities?.() as TorchCapabilities | undefined;
        if (capabilities?.torch) setTorch(false);
      })
      .catch((failure: Error) => setError(failure.message));
    return () => {
      cancelled = true;
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function toggleTorch() {
    const track = stream.current?.getVideoTracks()[0];
    if (!track || torch === null) return;
    await track.applyConstraints({ advanced: [{ torch: !torch } as MediaTrackConstraintSet] });
    setTorch(!torch);
  }

  async function capture() {
    const track = stream.current?.getVideoTracks()[0];
    let blob: Blob | null = null;
    const Capture = (
      window as unknown as { ImageCapture?: new (t: MediaStreamTrack) => { takePhoto(): Promise<Blob> } }
    ).ImageCapture;
    if (track && Capture) {
      try {
        blob = await new Capture(track).takePhoto(); // full sensor resolution where supported
      } catch {
        blob = null;
      }
    }
    if (!blob && video.current) {
      const canvas = document.createElement("canvas");
      canvas.width = video.current.videoWidth;
      canvas.height = video.current.videoHeight;
      canvas.getContext("2d")?.drawImage(video.current, 0, 0);
      blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.95));
    }
    if (blob) {
      onCapture(new File([blob], `live-${Date.now()}.jpg`, { type: blob.type || "image/jpeg" }));
      onClose();
    }
  }

  return (
    <div className={styles.live} role="dialog" aria-modal="true" aria-label={t("capture.title")}>
      <div className={styles.viewport}>
        <video ref={video} className={styles.video} playsInline muted aria-label={t("capture.preview")} />
        {previousImageId && (
          <img
            className={styles.ghost}
            src={imageUrl(previousImageId, "preview")}
            alt=""
            style={{ opacity: ghost }}
          />
        )}
        <svg
          className={styles.guide}
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        >
          <circle cx="50" cy="50" r="18" />
        </svg>
      </div>
      <div className={styles.controls}>
        {error && <Notice kind="error">{t("capture.error", { message: error })}</Notice>}
        {previousImageId && (
          <label className={styles.slider}>
            <span>{t("capture.ghost")}</span>
            <input
              type="range"
              min={0}
              max={0.8}
              step={0.05}
              value={ghost}
              onChange={(e) => setGhost(Number(e.target.value))}
            />
          </label>
        )}
        {torch !== null && (
          <Button variant="secondary" onClick={() => void toggleTorch()} aria-pressed={torch}>
            {t("capture.torch")}
          </Button>
        )}
        <button
          type="button"
          className={styles.shutter}
          onClick={() => void capture()}
          aria-label={t("capture.shutter")}
        />
        <Button variant="quiet" onClick={onClose}>
          {t("common.close")}
        </Button>
      </div>
    </div>
  );
}
