// src/components/PreguntaActual.jsx — Visualizador de la pregunta activa en tiempo real

import { HubConnectionState } from '@microsoft/signalr';
import { useSignalR } from '../hooks/useSignalR';
import './PreguntaActual.css';

const LETRAS = 'ABCDEFGHIJKLMNOP';

const ESTADO_CONFIG = {
  [HubConnectionState.Connecting]:   { texto: 'Conectando…',   color: '#f59e0b', dot: 'dot--amarillo' },
  [HubConnectionState.Connected]:    { texto: 'En vivo',        color: '#10b981', dot: 'dot--verde'    },
  [HubConnectionState.Reconnecting]: { texto: 'Reconectando…', color: '#f59e0b', dot: 'dot--amarillo' },
  [HubConnectionState.Disconnected]: { texto: 'Desconectado',   color: '#ef4444', dot: 'dot--rojo'     },
};

export function PreguntaActual() {
  const { preguntaActual, estadoConexion } = useSignalR();
  const cfg = ESTADO_CONFIG[estadoConexion] ?? ESTADO_CONFIG[HubConnectionState.Disconnected];

  return (
    <section className="pregunta-card">

      {/* Badge de estado de conexión */}
      <div className="conexion-badge">
        <span className={`dot ${cfg.dot}`} />
        <span style={{ color: cfg.color }}>{cfg.texto}</span>
      </div>

      {preguntaActual?.id === -1 ? (
        <div className="analisis-finalizado">
          <span className="finalizado-icon">✓</span>
          <p className="finalizado-titulo">Análisis finalizado</p>
          <p className="finalizado-hint">La sesión ha concluido correctamente.</p>
        </div>
      ) : preguntaActual ? (
        <div className="pregunta-contenido">
          {preguntaActual.grupoNombre && (
            <p className="pregunta-grupo">
              Grupo: <strong>{preguntaActual.grupoNombre}</strong>
              {' · '}
              Pregunta #{preguntaActual.id + 1}
            </p>
          )}

          <p className="pregunta-texto">{preguntaActual.texto}</p>

          {preguntaActual.opciones?.length > 0 && (
            <ul className="opciones-lista">
              {preguntaActual.opciones.map((opcion, idx) => (
                <li key={idx} className="opcion-item">
                  <span className="opcion-letra">{LETRAS[idx] ?? idx + 1}.</span>
                  <span className="opcion-texto">{opcion}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="sin-pregunta">
          <span className="sin-pregunta-icon">⏳</span>
          <p>Esperando la primera pregunta…</p>
          <p className="sin-pregunta-hint">
            Presiona <strong>Iniciar Análisis</strong> en la app de escritorio.
          </p>
        </div>
      )}
    </section>
  );
}
