# Control de Congestion

Pregunta 1:
Sirve de base ya que se puede ver que stop and wait es un caso particular de go back n, donde el tamaño de la ventana es de tamaño uno, de modo habria que generalizarla
Pregunta 2: Esta de base, deberia de ser practicamente igual, con una condicion extra, al mandar varios paquetes a la vez, puede llegar el caso en el que la secuencia sea mayor que la secuencia guardada, pero no sea el mensaje correspondiente, de modo que el receptor debe descartar los mensajes en caso de que la secuencia sea mas grande de lo necesario