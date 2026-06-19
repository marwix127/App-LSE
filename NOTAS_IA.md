# Notas sobre la IA de SignCam — cómo funciona y por qué

> Este documento es una explicación en lenguaje natural de **por qué** tomamos cada
> decisión sobre la parte de inteligencia artificial. No es documentación técnica
> seca (eso está en `PROGRESS.md`), sino la historia razonada de cómo llegamos
> hasta aquí y qué aprendimos por el camino.

---

## 1. La idea clave: no entrenamos con vídeo, entrenamos con "puntos"

Lo más importante de entender es que **el modelo nunca ve tu cámara ni tus fotos**.
Lo que ve son números.

El flujo real es así:

```
   Imagen real          MediaPipe            21 puntos (x,y,z)        Modelo
  (foto o webcam)  ───►  detecta la    ───►   = 63 números      ───►  predice
                          mano                  por mano               la letra
```

MediaPipe es una librería de Google que ya está entrenada para encontrar la mano
en una imagen y devolver **21 puntitos** (las articulaciones de los dedos), cada
uno con coordenadas `x`, `y`, `z`. Eso son 63 números.

Nuestro modelo solo trabaja con esos 63 números. Por eso:

- Da igual el color de fondo, la ropa, la luz... MediaPipe ya filtra todo eso.
- El modelo es pequeño y rápido: clasificar 63 números es trivial comparado con
  procesar una imagen entera píxel a píxel.
- En la videollamada real pasa exactamente lo mismo: webcam → MediaPipe → 63
  números → modelo → subtítulo.

**Decisión:** no usamos CNN (redes que miran píxeles) porque no hace falta.
MediaPipe ya hizo el trabajo duro de "mirar la imagen". Nosotros solo interpretamos
los puntos.

---

## 2. El primer tropiezo: un dataset que parecía bueno y no lo era

Descargamos un dataset de letras que venía con las imágenes ya "procesadas"...
pero al pasarlas por MediaPipe extraíamos **0 manos**.

El motivo: esas imágenes no eran fotos de manos reales, eran **dibujos de los
puntos ya pintados** sobre fondo negro. MediaPipe busca una mano de verdad, y un
dibujo de puntos no lo es.

```
  Lo que necesitábamos          Lo que tenía el dataset malo
  ┌──────────────┐              ┌──────────────┐
  │   🖐 (foto    │              │   • •        │  (puntos dibujados,
  │   real de     │              │  •     •     │   sin mano real)
  │   una mano)   │              │     •  •     │
  └──────────────┘              └──────────────┘
       ✅ MediaPipe la ve            ❌ MediaPipe no ve nada
```

**Lección:** para este pipeline necesitamos **fotos/vídeos reales**, porque el
primer paso siempre es que MediaPipe detecte una mano auténtica. Cambiamos al
dataset *ASL Alphabet* (fotos reales) y empezó a funcionar.

---

## 3. El modelo MLP: la primera versión que funcionó

Para las letras "quietas" (la mayoría del alfabeto) usamos un **MLP**
(Multi-Layer Perceptron), que es la red neuronal más sencilla que existe: coge los
63 números de entrada y los pasa por unas capas hasta decidir qué letra es.

```
  63 números ──► [capa 128] ──► [capa 64] ──► [A, B, C, ... Z]
   (entrada)                                    (probabilidades)
```

Con eso ya conseguimos **99% de acierto en test**. Pero "99% en test" engaña: en
test las imágenes se parecen mucho a las de entrenamiento. En la webcam real, en
tu cocina, con tu mano, costaba más. Ahí empezaron los ajustes de verdad.

---

## 4. El problema más importante: la normalización

Este fue el ajuste que más cambió las cosas, así que merece explicación.

Al principio le dábamos al modelo las coordenadas **tal cual** salían de MediaPipe.
Problema: esas coordenadas dependen de **dónde** está la mano en la pantalla.

```
  Mano arriba-izquierda        Misma letra, abajo-derecha
  ┌──────────────┐             ┌──────────────┐
  │ 🖐            │             │              │
  │               │            │              │
  │               │            │           🖐 │
  └──────────────┘             └──────────────┘
   x≈0.1, y≈0.1                  x≈0.8, y≈0.8
   → números muy distintos para EL MISMO signo
```

El modelo veía números totalmente diferentes y se confundía. La solución fue
**normalizar** los puntos antes de dárselos. Lo hicimos en tres pasos, cada uno
arreglando un problema concreto:

**Paso 1 — Quitar la posición.** Restamos la muñeca a todos los puntos. Así el
signo se describe "desde la muñeca", no importa dónde esté en la pantalla.

**Paso 2 — Quitar el tamaño.** Dividimos por el valor más grande. Da igual si tu
mano está cerca (grande) o lejos (pequeña): la *forma* es la misma.

**Paso 3 — Quitar el lado.** La A solo funcionaba con la mano izquierda porque el
dataset tenía sobre todo manos derechas. Espejamos la coordenada X de la mano
izquierda para que el modelo trate ambas manos igual.

```
  ANTES (coords crudas):   posición + tamaño + lado  → el modelo se lía
  DESPUÉS (normalizado):   solo la FORMA de la mano   → el modelo acierta
```

Después de esto, el reconocimiento dio un salto enorme. **La normalización fue
más importante que el propio modelo.**

> Nota: por eso `normalizar()` está ahora en `landmarks_utils.py` y es sagrada.
> Si se cambia, hay que reentrenar todo, porque el entrenamiento y la webcam
> tienen que hablar exactamente el mismo idioma.

---

## 5. Grabar tus propias muestras: la guinda

Aún con normalización, la C y la F se confundían con la D. Son letras parecidas y
el dataset genérico no tenía suficiente variedad de *tu* forma de hacerlas.

Solución pragmática: grabarte a ti mismo haciendo esas letras y mezclar esas
muestras con el dataset grande. El modelo aprende "así es como las hace este
usuario en esta cámara".

Un detalle que pulimos: al principio grababa 50 muestras de golpe en un segundo...
pero eran 50 fotos casi idénticas, no aportaban variedad. Lo cambiamos para grabar
**una muestra por pulsación**, soltando y rehaciendo el signo cada vez. Así cada
muestra tiene un ángulo ligeramente distinto = más robustez.

```
  ❌ 50 frames seguidos = casi la misma foto 50 veces
  ✅ 50 capturas separadas = 50 variaciones reales del signo
```

---

## 6. Data augmentation: inventar variedad "gratis"

Para reforzar aún más, añadimos **data augmentation**: cogemos los datos que ya
tenemos y creamos copias con un poco de ruido aleatorio en los puntos.

La idea: en la vida real tu mano nunca está exactamente igual dos veces, tiembla un
poco. Si entrenamos solo con datos "perfectos", el modelo es frágil. Si le metemos
versiones ligeramente movidas, aprende a tolerar esa variación.

```
  1 muestra real  ──►  + ruido pequeño  ──►  3 muestras
                                              (la original + 2 variadas)
```

Es como estudiar con más ejemplos sin tener que grabar más: multiplicamos el
dataset por 3 sin esfuerzo.

---

## 7. El salto a movimiento: las letras J y Z

Aquí cambió el tipo de problema. La J y la Z **no son una postura, son un
movimiento**. El MLP solo mira un instante (un frame), así que es incapaz de ver un
gesto que cambia en el tiempo. Es como intentar reconocer un saludo viendo una sola
foto: imposible.

Para esto se usa un **LSTM**, una red pensada para **secuencias**. En vez de un
frame, le damos 30 frames seguidos (≈1 segundo) y aprende el patrón del movimiento.

```
   MLP (foto fija)            LSTM (secuencia)
   ┌─────┐                    ┌──┬──┬──┬──┬──┐
   │ 🖐  │ → "es una A"        │f1│f2│f3│..│f30│ → "esto se mueve como una J"
   └─────┘                    └──┴──┴──┴──┴──┘
   1 frame                     30 frames en orden
```

Por qué LSTM y no algo más complejo: los datos ya son los 63 números limpios de
MediaPipe, así que no necesitamos nada que procese imágenes. El LSTM solo tiene que
entender cómo cambian esos números a lo largo del tiempo.

---

## 8. Los datos del LSTM: pocos al principio, muchos después

Primera versión: grabamos 20 secuencias de J y 20 de Z nosotros mismos. Dio 100%
en test... pero ese 100% era mentira: con solo 40 ejemplos el modelo "memoriza" en
vez de "aprender". En la webcam fallaba.

La solución fue traer un dataset de **vídeos** reales (SigNN Video Data): 316
vídeos de J y 396 de Z. Cada vídeo lo pasamos por MediaPipe frame a frame para
sacar su secuencia de puntos.

Un detalle bonito: los vídeos no tenían todos la misma duración, así que
**remuestreamos** cada uno a exactamente 30 frames (cogiendo puntos repartidos a lo
largo del vídeo). Así todas las secuencias tienen el mismo tamaño, que es lo que el
LSTM necesita.

Ahora el 100% sí significa algo, porque son ~750 secuencias variadas.

---

## 9. El ajuste más fino: ¿cuándo usar MLP y cuándo LSTM?

Teníamos dos modelos y un problema nuevo: ¿cómo decide el programa cuál usar en
cada momento? Si una letra está quieta es MLP; si hay movimiento es LSTM. Pero,
¿cómo sabemos si "hay movimiento"?

Aquí cometimos un error instructivo. Primero medíamos el movimiento con
`np.std(secuencia)` a secas. Pero eso mide **lo desperdigados** que están los 21
puntos entre sí (que siempre es mucho, una mano abierta ocupa espacio), **no**
cuánto se mueven en el tiempo. Resultado: el programa creía que SIEMPRE había
movimiento y disparaba el LSTM aunque tuvieras la mano quieta.

La corrección: medir la desviación **a lo largo del tiempo** (eje temporal). O sea:
¿cada punto se queda quieto entre frame y frame, o se desplaza?

```
  Mano QUIETA (letra estática)      Mano en MOVIMIENTO (J/Z)
  frame1: • • •                     frame1: •
  frame2: • • •  (igual)            frame2:   •   (se desplaza)
  frame3: • • •  (igual)            frame3:     •
  → variación temporal ≈ 0.002      → variación temporal ≈ 0.100
```

Medimos los dos casos reales en tu cámara: quieta daba ~0.002, moviendo daba
~0.100. Pusimos el umbral en **0.03**, justo en medio. Limpio y fiable.

Otro bug del mismo estilo: teníamos un código que "reseteaba" la memoria de frames
cuando detectaba un cambio brusco. Pero hacer una J **es** un cambio brusco, así
que se reseteaba justo cuando queríamos grabar el movimiento, y nunca llegaba a
juntar los 30 frames. Lo quitamos y usamos una **ventana deslizante**: siempre
guardamos los últimos 30 frames, sin resetear.

---

## 10. La filosofía final: mejor callar que mentir

Una reflexión que guió los últimos ajustes: en un **traductor**, decir una letra
equivocada es peor que no decir nada. Si alguien confía en el subtítulo, un error
le da información falsa.

Por eso subimos los **umbrales de confianza**: el modelo solo muestra una letra si
está muy seguro (>95%). Si duda, prefiere quedarse callado. También pusimos un
tiempo mínimo entre cambios para que el subtítulo no parpadee nervioso.

```
  Confianza 99% → muestra la letra
  Confianza 70% → mejor no digo nada (podría estar mal)
```

---

## Resumen en una frase

Construimos un sistema que convierte la mano en 63 números (MediaPipe), los
**normaliza** para que solo importe la forma, y los manda a **dos modelos**: un MLP
para letras quietas y un LSTM para letras con movimiento, eligiendo entre ellos
según cuánto se mueve la mano. Lo que más mejoró la precisión no fueron los modelos
en sí, sino **los datos y la normalización**.
