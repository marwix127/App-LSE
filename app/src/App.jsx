import React, { useEffect, useState, useRef } from "react";
import Preview from "./Preview.jsx";
import Settings from "./Settings.jsx";

const CONFIG_DEFECTO = { camera: 0, subtitleScale: 1.0, subtitlePosition: "bottom" };

function cargarConfig() {
  try {
    return { ...CONFIG_DEFECTO, ...JSON.parse(localStorage.getItem("signcam-config")) };
  } catch {
    return CONFIG_DEFECTO;
  }
}

const ESTADOS = {
  idle: "Detenido",
  loading_models: "Cargando modelos…",
  opening_camera: "Abriendo cámara…",
  camera_opened: "Cámara abierta…",
  loading_landmarker: "Cargando detector de manos…",
  opening_virtualcam: "Abriendo cámara virtual…",
  ready: "En marcha",
};

export default function App() {
  const [estado, setEstado] = useState("idle");
  const [letra, setLetra] = useState("");
  const [esMovimiento, setEsMovimiento] = useState(false);
  const [fps, setFps] = useState(0);
  const [camaraVirtual, setCamaraVirtual] = useState("");
  const [log, setLog] = useState([]);
  const [config, setConfig] = useState(cargarConfig);
  const logRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("signcam-config", JSON.stringify(config));
  }, [config]);

  useEffect(() => {
    const off = window.signcam.onEvent((ev) => {
      switch (ev.type) {
        case "init":
          setEstado(ev.stage);
          break;
        case "ready":
          setEstado("ready");
          setCamaraVirtual(ev.virtual_camera);
          break;
        case "status":
          setLetra(ev.letter || "");
          setEsMovimiento(!!ev.is_movement);
          if (typeof ev.fps === "number") setFps(ev.fps);
          break;
        case "stopped":
        case "exit":
          setEstado("idle");
          setLetra("");
          break;
        case "error":
          setEstado("idle");
          añadirLog("ERROR: " + ev.message);
          break;
        case "log":
          añadirLog(ev.message);
          break;
        default:
          break;
      }
    });
    return off;
  }, []);

  function añadirLog(msg) {
    setLog((prev) => [...prev.slice(-80), msg]);
  }

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const corriendo = estado !== "idle";

  async function toggle() {
    if (corriendo) {
      await window.signcam.stop();
    } else {
      setLog([]);
      await window.signcam.start(config);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>SignCam</h1>
        <span className={`badge ${corriendo ? "on" : "off"}`}>{ESTADOS[estado] || estado}</span>
      </header>

      <main>
        <section className="panel-preview">
          <Preview virtualCamera={camaraVirtual} activo={estado === "ready"} />
          {fps ? <div className="fps">{fps} fps</div> : null}
        </section>

        <section className="panel-control">
          <button className={corriendo ? "stop" : "start"} onClick={toggle}>
            {corriendo ? "Detener" : "Iniciar cámara"}
          </button>
          {camaraVirtual && (
            <p className="hint">
              Selecciona <b>{camaraVirtual}</b> en Teams / Zoom / Meet.
            </p>
          )}

          <Settings config={config} setConfig={setConfig} bloqueado={corriendo} />
        </section>
      </main>

      <section className="log">
        <h2>Registro</h2>
        <pre ref={logRef}>{log.join("\n")}</pre>
      </section>
    </div>
  );
}
