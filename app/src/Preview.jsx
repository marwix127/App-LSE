import React, { useEffect, useRef, useState } from "react";

/**
 * Muestra el vídeo de la cámara virtual (lo que ven en Teams/Zoom).
 * Lee el dispositivo cuyo nombre coincide con `virtualCamera` mediante getUserMedia.
 * No accede a la webcam real (de eso se encarga el sidecar de Python).
 */
export default function Preview({ virtualCamera, activo }) {
  const videoRef = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stream = null;
    let cancelado = false;

    async function conectar() {
      setError("");
      if (!activo || !virtualCamera) return;
      try {
        // NO abrimos la cámara por defecto (podría ser la webcam real, que está
        // ocupada por el sidecar). Buscamos directamente la cámara virtual por nombre.
        const dispositivos = await navigator.mediaDevices.enumerateDevices();
        const cam = dispositivos.find(
          (d) => d.kind === "videoinput" && d.label.includes(virtualCamera)
        );
        if (!cam) {
          setError(`No encuentro "${virtualCamera}" entre las cámaras.`);
          return;
        }

        stream = await navigator.mediaDevices.getUserMedia({
          video: { deviceId: { exact: cam.deviceId } },
        });
        if (cancelado) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (e) {
        setError(e.message);
      }
    }

    // La cámara virtual tarda un instante en estar disponible tras "ready".
    const t = setTimeout(conectar, 600);

    return () => {
      cancelado = true;
      clearTimeout(t);
      if (stream) stream.getTracks().forEach((tr) => tr.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [virtualCamera, activo]);

  if (!activo) {
    return <div className="preview-vacio">Inicia la cámara para ver el preview</div>;
  }

  return (
    <div className="preview">
      <video ref={videoRef} autoPlay playsInline muted />
      {error && <div className="preview-error">{error}</div>}
    </div>
  );
}
