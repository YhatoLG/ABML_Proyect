// Servicios/EstadoPreguntaActual.cs — Almacén en memoria de la pregunta activa
//
// Por qué un singleton y no una variable estática:
//   Las variables estáticas en controladores no participan del sistema de DI,
//   no son testeables, y no pueden ser reemplazadas con mocks.
//   Un singleton registrado en DI tiene exactamente el mismo ciclo de vida
//   (vive mientras viva la app) pero respeta la arquitectura del proyecto.
//
// Por qué no usar IDistributedMemoryCache (ya registrada en Program.cs):
//   IMemoryCache es adecuada para datos efímeros con TTL. Aquí queremos
//   que el estado sea explícito y sin expiración — el singleton es más claro.
//   En un escenario multi-servidor usaríamos Redis; en este proyecto con
//   un único servidor Railway, el singleton es la elección correcta.
//
// Seguridad de hilos (concurrencia):
//   Múltiples requests HTTP pueden llegar simultáneamente (ej. dos instancias
//   del desktop presionando "Siguiente" a la vez). El lock garantiza que
//   solo uno a la vez pueda leer o escribir _actual.

using ApiGenericaCsharp.Modelos;

namespace ApiGenericaCsharp.Servicios;

public interface IEstadoPreguntaActual
{
    PreguntaDto? ObtenerActual();
    void Establecer(PreguntaDto pregunta);
    void Limpiar();
}

public class EstadoPreguntaActual : IEstadoPreguntaActual
{
    private readonly object _lock = new();
    private PreguntaDto? _actual;

    public PreguntaDto? ObtenerActual()
    {
        lock (_lock)
            return _actual;
    }

    public void Establecer(PreguntaDto pregunta)
    {
        lock (_lock)
            _actual = pregunta;
    }

    public void Limpiar()
    {
        lock (_lock)
            _actual = null;
    }
}
