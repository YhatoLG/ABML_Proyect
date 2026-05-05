// Hubs/PreguntaHub.cs — Canal central de comunicación en tiempo real
//
// Un Hub en SignalR es el punto de encuentro entre clientes y servidor.
// Los clientes se conectan por WebSocket a la URL del hub y quedan
// suscritos a eventos que el servidor puede emitir en cualquier momento.
//
// Diferencia entre Clients.All / Clients.Caller / Clients.Others:
//   Clients.All    → todos los clientes conectados (React, otros desktops, etc.)
//   Clients.Caller → solo el cliente que invocó el método del hub (no aplica desde IHubContext)
//   Clients.Others → todos los conectados EXCEPTO quien disparó la acción
//
// En este proyecto usamos Clients.All porque queremos que TODOS los visualizadores
// React vean la pregunta activa, independientemente de quién la disparó.

using Microsoft.AspNetCore.SignalR;

namespace ApiGenericaCsharp.Hubs;

public class PreguntaHub : Hub
{
    // El hub está intencionalmente vacío de métodos públicos.
    // La notificación la dispara el controlador PreguntasController
    // usando IHubContext<PreguntaHub>, que es el patrón correcto cuando
    // el evento se origina fuera del hub (desde un endpoint HTTP).
    //
    // Si el hub expusiera métodos aquí, solo los clientes SignalR podrían
    // invocarlos. Necesitamos que Python (HTTP) sea quien dispara el evento,
    // por eso el controlador usa IHubContext en lugar de llamar al hub directamente.
}
