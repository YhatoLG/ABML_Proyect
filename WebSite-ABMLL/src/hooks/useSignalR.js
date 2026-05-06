// src/hooks/useSignalR.js — Hook que gestiona la conexión SignalR y la pregunta activa
//
// Responsabilidades:
//   1. Crear y mantener UNA sola conexión WebSocket durante el ciclo de vida del componente
//   2. Suscribirse al evento "PreguntaCambiada" emitido por el servidor .NET
//   3. Al montar: recuperar la pregunta actual vía HTTP (por si ya había sesión activa)
//   4. Al desmontar: limpiar suscripciones y cerrar la conexión para evitar leaks
//
// Por qué el cleanup es crítico:
//   React en modo StrictMode (desarrollo) monta y desmonta los componentes dos veces.
//   Sin cleanup, cada ciclo dejaría una conexión WebSocket abierta y un listener
//   "PreguntaCambiada" activo → la misma pregunta llegaría duplicada N veces.

import { useEffect, useRef, useState } from 'react';
import {
  HubConnectionBuilder,
  HubConnectionState,
  LogLevel,
} from '@microsoft/signalr';

// Usar variable de entorno de Vite; si no existe, apuntar al servidor en Railway.
// En desarrollo local, crear un archivo .env con: VITE_API_URL=http://localhost:5034
const API_URL =
  import.meta.env.VITE_API_URL ?? 'https://api-proyect-production.up.railway.app';

export function useSignalR() {
  const [preguntaActual, setPreguntaActual] = useState(null);
  const [estadoConexion, setEstadoConexion] = useState(
    HubConnectionState.Disconnected,
  );

  // useRef guarda la conexión entre renders sin causar re-renders al cambiar.
  const connectionRef = useRef(null);

  useEffect(() => {
    // ── Recuperar pregunta activa al montar ─────────────────────────────────
    // Si hay una sesión en curso cuando React carga la página, este fetch
    // evita que el componente quede en blanco hasta que llegue el próximo evento.
    fetch(`${API_URL}/api/preguntas/actual`)
      .then((res) => (res.status === 200 ? res.json() : null))
      .then((data) => {
        if (data) setPreguntaActual(data);
      })
      .catch(() => {}); // errores de red en la carga inicial no son fatales

    // ── Crear la conexión ───────────────────────────────────────────────────
    const connection = new HubConnectionBuilder()
      .withUrl(`${API_URL}/preguntaHub`)
      // withAutomaticReconnect: si la conexión cae, SignalR reintenta en los
      // intervalos especificados (ms) antes de declararse desconectado.
      .withAutomaticReconnect([0, 2_000, 10_000, 30_000])
      // configureLogging: en desarrollo es útil para ver el handshake y los mensajes.
      // En producción cambia a LogLevel.None para no saturar la consola.
      .configureLogging(
        import.meta.env.DEV ? LogLevel.Information : LogLevel.None,
      )
      .build();

    // ── Suscribirse al evento del servidor ──────────────────────────────────
    // El primer argumento debe coincidir EXACTAMENTE con el string que usa
    // SendAsync("PreguntaCambiada", ...) en PreguntasController.cs
    connection.on('PreguntaCambiada', (pregunta) => {
      setPreguntaActual(pregunta);
    });

    // ── Eventos del ciclo de vida de la reconexión ──────────────────────────
    connection.onreconnecting(() =>
      setEstadoConexion(HubConnectionState.Reconnecting),
    );
    connection.onreconnected(() =>
      setEstadoConexion(HubConnectionState.Connected),
    );
    connection.onclose(() =>
      setEstadoConexion(HubConnectionState.Disconnected),
    );

    connectionRef.current = connection;

    // ── Iniciar la conexión ─────────────────────────────────────────────────
    async function iniciar() {
      setEstadoConexion(HubConnectionState.Connecting);
      try {
        await connection.start();
        setEstadoConexion(HubConnectionState.Connected);
      } catch (err) {
        console.error('[SignalR] Error al conectar:', err);
        setEstadoConexion(HubConnectionState.Disconnected);
      }
    }

    iniciar();

    // ── Cleanup al desmontar el componente ──────────────────────────────────
    return () => {
      connection.off('PreguntaCambiada');
      connection.stop();
    };
  }, []); // [] → el efecto se ejecuta solo al montar y al desmontar

  return { preguntaActual, estadoConexion };
}
