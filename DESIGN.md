---
name: Consultorio Dental JM
description: Sistema de gestión del consultorio, con estilo de app y paleta Lavanda (tema claro y oscuro).
colors:
  marino-jm: "#012880"
  marino-hover: "#0a3aa8"
  verde-encia: "#85b559"
  verde-encia-hondo: "#6e9c45"
  lavanda: "#a393be"
  cielo-lavanda: "#c0cde6"
  tinta: "#0d1838"
  gris-salvia: "#55625c"
  hoja: "#ffffff"
  hoja-elevada: "#f5f6fa"
  linea: "#e1e5ef"
  rojo-alerta: "#b4232f"
  noche-marco: "#161a2e"
  noche-hoja: "#1d2239"
  noche-tinta: "#e8ebf7"
typography:
  headline:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "26px"
    fontWeight: 600
    lineHeight: "32px"
    letterSpacing: "-0.01em"
  title:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: "21px"
  body:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "20px"
  label:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: "18px"
  figure:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "32px"
    fontWeight: 600
    lineHeight: "38px"
    fontFeature: "tnum"
rounded:
  control: "11px"
  card: "18px"
  tile: "22px"
  hero: "24px"
  sheet: "26px"
  pill: "99px"
spacing:
  gap: "16px"
  pad: "28px"
  pad-mobile: "16px"
components:
  button-primary:
    backgroundColor: "{colors.marino-jm}"
    textColor: "{colors.hoja}"
    rounded: "{rounded.control}"
    height: "36px"
    padding: "0 14px"
  button-primary-hover:
    backgroundColor: "{colors.marino-hover}"
  button-whatsapp:
    backgroundColor: "{colors.verde-encia}"
    textColor: "#15270a"
    rounded: "{rounded.control}"
    height: "36px"
  button-secondary:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.control}"
    height: "36px"
  card:
    backgroundColor: "{colors.hoja}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.card}"
  quick-tile-navy:
    backgroundColor: "{colors.marino-jm}"
    textColor: "{colors.hoja}"
    rounded: "{rounded.tile}"
    padding: "16px 18px 18px"
  day-chip-today:
    backgroundColor: "{colors.marino-jm}"
    textColor: "{colors.hoja}"
    rounded: "16px"
---

# Design System: Consultorio Dental JM

## Overview

**Creative North Star: "La bata y la sonrisa"**

Una herramienta clínica que se siente como una app: precisa y confiable en su base (marino profundo, hojas blancas, números en tipografía tabular) y cálida en los momentos que mueven al doctor a actuar (el verde de la encía en los botones de WhatsApp, tarjetas de color en los accesos rápidos, círculos de pacientes). La estructura es la de un tablero de trabajo; la superficie es la de una app móvil, con esquinas generosas, sombras suaves y botones tipo píldora donde la acción importa.

La densidad es cómoda, no apretada: los dos doctores la usan entre pacientes, en la computadora y en el celular. Lo que evita una falta (próxima cita, confirmaciones, recordatorios) va arriba y a un toque. El marco (dock lateral y encabezado) es lavanda claro y la hoja de trabajo es blanca; en el tema noche, el marco y la hoja bajan a azul tinta conservando los mismos acentos.

**Key Characteristics:**
- Marco lavanda (#c0cde6) que envuelve una hoja blanca de esquinas amplias (26px).
- Marino JM (#012880) como color de autoridad: acción principal, día de hoy, héroe del inicio.
- Verde encía (#85b559) para lo que se manda al paciente (WhatsApp) y como subrayado de los botones primarios.
- Tarjetas con sombra suave tintada de marino, sin borde duro, en el tablero.
- 3D (molar y tipodonto) como pieza de identidad, no como adorno.
- Temas claro (Lavanda) y oscuro (Noche) a partir de las mismas variables.

## Colors

Paleta del logo del consultorio: un marino de autoridad, un verde de encía cálido y dos lavandas que suavizan todo lo demás.

### Primary
- **Marino JM** (#012880): botón primario, día de hoy en la semana, héroe del inicio, mosaico "Recordatorios", texto de datos. En tema noche el primario pasa a lavanda claro (#b8b0dc) con texto tinta.

### Secondary
- **Verde encía** (#85b559): botones de WhatsApp (enviar, confirmar), subrayado de 3px de los botones primarios, primer pendiente del día, anillo de los pacientes de hoy. Su versión honda (#6e9c45) sirve para bordes y hovers.

### Tertiary
- **Lavanda** (#a393be): segunda serie de datos (egresos), mosaico "Nuevo paciente", contorno del borde de los dientes 3D.
- **Cielo lavanda** (#c0cde6): marco de la app (dock y encabezado), mosaico "Cobrar saldos", lóbulo claro del logo.

### Neutral
- **Tinta** (#0d1838): texto principal.
- **Gris salvia** (#55625c): texto secundario y metadatos.
- **Hoja** (#ffffff) y **hoja elevada** (#f5f6fa): superficie de trabajo y rellenos de chips.
- **Línea** (#e1e5ef): bordes y divisores.
- **Rojo alerta** (#b4232f): saldos negativos, vencidos, piezas por extraer.

### Named Rules
**The Encía Rule.** El verde se reserva para lo que sale hacia el paciente (WhatsApp, confirmaciones) y para el subrayado del botón primario. No es un color decorativo.

**The One Navy Moment Rule.** Por pantalla hay un solo bloque grande en marino sólido (el héroe o el mosaico destacado); el resto del marino vive en botones y texto.

## Typography

**Display/Body Font:** IBM Plex Sans (con system-ui)
**Mono:** IBM Plex Mono, solo para datos técnicos.

**Character:** una sola familia, humanista y técnica a la vez; la jerarquía sale del peso (400/500/600) y del tamaño, nunca de cambiar de familia.

### Hierarchy
- **Headline** (600, 26px, 32px): saludo del inicio y títulos de página.
- **Title** (600, 16–17px): títulos de mosaicos y secciones.
- **Body** (400, 14px, 20px): texto de listas y formularios.
- **Label** (500, 13px): etiquetas de KPI, chips, metadatos.
- **Figure** (600, 32px, tabular): cifra principal (ingresos del mes). Las demás cifras van a 24px/500 con `tnum`.

### Named Rules
**The Tabular Money Rule.** Toda cifra, hora o fecha numérica usa `font-variant-numeric: tabular-nums`.

## Layout

Shell de dos columnas: dock lateral de 92px y hoja de trabajo (contenido máximo de 1480px, relleno de 28px). El tablero usa un bento de 12 columnas con separación de 16px: héroe (8) y próxima cita (4), accesos rápidos (4 mosaicos), semana, números del mes, jornada, gráfica (7) y avisos (5), tratamientos (8) y lateral (4). Por debajo de 1240px todo baja a ancho completo y los mosaicos pasan a 2 columnas. Por debajo de 900px el dock se vuelve barra inferior con un botón + central flotante (agendar cita), el relleno baja a 16px y la hoja se redondea solo arriba.

## Elevation & Depth

Híbrido: el marco y la hoja son planos y se distinguen por tono; dentro del tablero, las tarjetas flotan con una sombra suave tintada de marino en lugar de borde. En tema noche se añade un borde fino porque la sombra casi no se lee.

### Shadow Vocabulary
- **Lift** (`0 1px 2px rgb(1 40 128 / .06), 0 8px 24px -10px rgb(1 40 128 / .22)`): tarjetas del tablero, día de hoy, hover de mosaicos.
- **FAB** (`0 0 0 5px var(--frame), 0 10px 22px -6px rgb(1 40 128 / .55)`): botón + central de la barra móvil.

### Named Rules
**The Lift-Not-Line Rule.** En el tablero, una tarjeta se separa del fondo con sombra suave, no con borde de 1px (salvo en tema noche).

## Shapes

Esquinas generosas y escalonadas por tamaño: controles 11px, tarjetas 18px, mosaicos 22px, héroe 24px, hoja 26px. Píldora (99px) para los botones del héroe y de la próxima cita, chips de pendientes y círculos de pacientes. Los avatares de personas en el tablero son círculos; en listas y el dock, cuadrados redondeados.

## Components

### Buttons
- **Shape:** esquinas suaves (11px); píldora en el héroe y en la próxima cita.
- **Primary:** marino con texto blanco y subrayado verde de 3px (tecla física); al pasar el cursor, un barrido de izquierda a derecha.
- **WhatsApp:** verde encía con texto verde muy oscuro; el ícono se inclina al pasar el cursor.
- **Secondary:** hoja blanca con borde gris; el barrido es verde claro.
- **Active:** se hunde (`scale(.97)`).

### Chips
- **Pendientes del día:** píldoras translúcidas sobre el héroe marino; la primera en verde encía.
- **Días de la semana:** tarjetitas de 16px con día, número y conteo de citas; hoy en marino sólido.

### Cards / Containers
- **Corner Style:** 18px.
- **Background:** hoja blanca (#ffffff), noche #1d2239.
- **Shadow Strategy:** Lift (ver Elevation).
- **Internal Padding:** encabezado 14px 18px con divisor; cuerpo 16–18px.

### Quick Tiles (signature)
Mosaicos de 22px con fondo tintado (verde, lavanda, cielo o marino), un cuadro de ícono de 44px en el color fuerte y un círculo grande del mismo color que asoma por la esquina inferior derecha. Al pasar el cursor suben 3px y el ícono gira levemente.

### Navigation
Dock lateral sobre el marco lavanda: logo arriba, mosaicos de 44px con etiqueta debajo, magnificación con física de resorte al pasar el cursor, burbujas de conteo (rojas si son urgentes). En el celular: barra inferior con 4 secciones, botón + central flotante y una hoja "Más" cuyos íconos entran escalonados.

### Signature 3D
Molar flotante con anillo orbital en el héroe y tipodonto interactivo en la ficha del paciente: esmalte marfil con contorno oscuro en los bordes, encía rosada que se enrojece con inflamación, collares de color por hallazgo.

## Do's and Don'ts

### Do:
- **Do** sacar todo color de las variables del tema (`--primary`, `--accent`, `--qa-*`, `--hero-strong*`) para que el tema noche funcione solo.
- **Do** usar el verde encía (#85b559) solo para acciones hacia el paciente y el subrayado primario.
- **Do** usar cifras tabulares en dinero, horas y fechas.
- **Do** escalonar las entradas por tipo de bloque (despliegue en el héroe, difuminado en tarjetas, rebote leve en mosaicos y chips) y respetar `prefers-reduced-motion`.
- **Do** usar el logo Dental JM (macro `logo`) como marca; nunca otro ícono de diente genérico en su lugar.

### Don't:
- **Don't** inventar testimonios, reseñas, cifras ni pacientes; solo datos reales del consultorio.
- **Don't** introducir colores fuera de la paleta Lavanda ni otra familia tipográfica.
- **Don't** poner tarjetas dentro de tarjetas.
- **Don't** usar texto con degradado ni vidrio esmerilado decorativo.
