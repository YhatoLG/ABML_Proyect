// Controllers/PreguntasController.cs — Endpoint que conecta Python con SignalR
//
// Flujo cuando Python presiona "Siguiente Pregunta":
//   1. Python  →  POST /api/preguntas/siguiente  (HTTP)
//   2. Este controlador recibe la pregunta en el body
//   3. La almacena en IEstadoPreguntaActual (singleton) para reconexiones
//   4. Llama a _hub.Clients.All.SendAsync("PreguntaCambiada", pregunta)
//      → SignalR entrega el mensaje por WebSocket a TODOS los React conectados
//   5. Retorna 200 OK con la pregunta para que Python confirme y actualice su UI
//
// Por qué IHubContext y no el Hub directamente:
//   El Hub solo existe mientras un cliente tiene una conexión activa.
//   IHubContext es una abstracción del contenedor DI que permite enviar
//   mensajes a clientes desde cualquier lugar del servidor (controladores,
//   servicios de background, etc.) sin necesitar una conexión entrante.
//
// Por qué se hace SendAsync Y return Ok():
//   SendAsync notifica a los clientes WebSocket (React) en tiempo real.
//   return Ok() responde a la petición HTTP original (Python) con confirmación.
//   Son canales independientes: uno es push WebSocket, el otro es pull HTTP.

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using ApiGenericaCsharp.Hubs;
using ApiGenericaCsharp.Modelos;
using ApiGenericaCsharp.Servicios;

namespace ApiGenericaCsharp.Controllers;

[ApiController]
[Route("api/preguntas")]
[AllowAnonymous]
public class PreguntasController : ControllerBase
{
    private readonly IHubContext<PreguntaHub> _hub;
    private readonly IEstadoPreguntaActual _estado;

    public PreguntasController(IHubContext<PreguntaHub> hub, IEstadoPreguntaActual estado)
    {
        _hub    = hub;
        _estado = estado;
    }

    // GET /api/preguntas/actual
    // React lo llama al montar el componente o al reconectarse para no
    // quedarse en blanco si ya hay una sesión activa. Retorna 204 si
    // todavía no se ha enviado ninguna pregunta.
    [HttpGet("actual")]
    public IActionResult ObtenerActual()
    {
        var actual = _estado.ObtenerActual();
        if (actual is null)
            return NoContent();   // 204: sesión aún no iniciada

        return Ok(actual);
    }

    // POST /api/preguntas/siguiente
    // Python lo llama cada vez que el usuario presiona "Siguiente Pregunta".
    // El body es un JSON con los campos de PreguntaDto.
    [HttpPost("siguiente")]
    public async Task<IActionResult> NotificarSiguiente([FromBody] PreguntaDto pregunta)
    {
        if (pregunta is null)
            return BadRequest("El body no puede estar vacío.");

        // Guardar en memoria para que clientes que se reconecten puedan
        // recuperar el estado actual con GET /api/preguntas/actual.
        _estado.Establecer(pregunta);

        // Emitir el evento a TODOS los clientes SignalR conectados.
        // Si no hay ninguno, la llamada es un no-op (no lanza excepción).
        await _hub.Clients.All.SendAsync("PreguntaCambiada", pregunta);

        // Responder a Python con la pregunta para confirmar que se procesó.
        return Ok(pregunta);
    }
}
