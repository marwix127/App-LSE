import React, { useEffect, useState } from "react";

const TAMANOS = [
  { label: "Pequeño", value: 0.5 },
  { label: "Normal", value: 1.0 },
  { label: "Grande", value: 1.5 },
];

/**
 * Panel de ajustes. Los valores se aplican cuando se (re)inicia la cámara,
 * porque el sidecar los lee como argumentos al arrancar.
 */
export default function Settings({ config, setConfig, bloqueado }) {
  const [camaras, setCamaras] = useState([]);

  async function refrescarCamaras() {
    const lista = await window.signcam.listCameras();
    setCamaras(lista);
  }

  useEffect(() => {
    refrescarCamaras();
  }, []);

  function set(clave, valor) {
    setConfig((c) => ({ ...c, [clave]: valor }));
  }

  return (
    <div className={`ajustes ${bloqueado ? "bloqueado" : ""}`}>
      <h2>Ajustes</h2>

      <label>
        Cámara de entrada
        <div className="fila-camara">
          <select
            value={config.camera}
            disabled={bloqueado}
            onChange={(e) => set("camera", Number(e.target.value))}
          >
            {camaras.length === 0
              ? [0, 1, 2, 3, 4].map((i) => (
                  <option key={i} value={i}>Cámara {i}</option>
                ))
              : camaras.map((c) => (
                  <option key={c.index} value={c.index}>{c.name}</option>
                ))}
          </select>
          <button
            type="button"
            className="refrescar"
            disabled={bloqueado}
            onClick={refrescarCamaras}
            title="Volver a detectar cámaras"
          >
            ⟳
          </button>
        </div>
      </label>

      <label>
        Tamaño del subtítulo
        <select
          value={config.subtitleScale}
          disabled={bloqueado}
          onChange={(e) => set("subtitleScale", Number(e.target.value))}
        >
          {TAMANOS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </label>

      <label>
        Posición del subtítulo
        <div className="toggle">
          <button
            className={config.subtitlePosition === "top" ? "sel" : ""}
            disabled={bloqueado}
            onClick={() => set("subtitlePosition", "top")}
          >
            Arriba
          </button>
          <button
            className={config.subtitlePosition === "bottom" ? "sel" : ""}
            disabled={bloqueado}
            onClick={() => set("subtitlePosition", "bottom")}
          >
            Abajo
          </button>
        </div>
      </label>

      {bloqueado && <p className="nota">Detén la cámara para cambiar los ajustes.</p>}
    </div>
  );
}
