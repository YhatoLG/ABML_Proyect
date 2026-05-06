// Modelos/PreguntaDto.cs — Objeto de transferencia de datos para SignalR y el endpoint REST
//
// Es un record (inmutable por diseño) que viaja tanto en el body HTTP
// como en el mensaje SignalR "PreguntaCambiada".
// ASP.NET Core serializa las propiedades a camelCase por defecto,
// por eso en React se accede como pregunta.texto, pregunta.opciones, etc.

namespace ApiGenericaCsharp.Modelos;

public record PreguntaDto(
    // Índice local (posición en la sesión Python, ya que la BD no expone un id global de orden)
    int Id,

    // Texto de la pregunta tal como está en la columna "texto" de la tabla preguntas
    string Texto,

    // Opciones de respuesta: en la BD se guardan como JSON (ej. ["Opción A","Opción B"])
    // Ya desserializadas a List<string> antes de enviar
    List<string> Opciones,

    // Índice base-0 de la opción correcta (columna "respuesta_correcta")
    int RespuestaCorrecta,

    // Nombre del banco de preguntas (columna "nombre" en grupos_preguntas)
    // Nullable porque puede no estar disponible en todos los contextos
    string? GrupoNombre
);
