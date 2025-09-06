# Explicación

Este es el repositorio donde he levantado mi sistema RAG para la detección de realciones entra criminale spor medio de noticias.

Mejoras:
Usar volúmenes para que me cambie codigo dentro del contenedor es buena idea?
A la salida del NER puedo aplicar LLM de manera que integre la respuesta con la del RAG o que la haga aparte, diciendole que tiene que responder con datos importantes, fijándose especialmente en si es criminal o pep o lo que sea.
Arreglar lo de que salga primero un personaje que no es el nuestro.
Arreglar que no salgan todas las entidades (¿posible cambio de modelo NER?)
Cambiar Dense por Sparse puede ser una buena idea.
Añadir código para obtener nombres y entidades limpios de OpenSanctions.