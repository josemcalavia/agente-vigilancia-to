# Guía de instalación y uso

**Agente de vigilancia de literatura en Terapia Ocupacional**
Diseño original: José María Calavia Balduz · Licencia CC BY-NC-SA 4.0

Esta guía es para terapeutas ocupacionales, no para informáticos. Calcula unos 20
minutos la primera vez. Después, cada boletín es pedirlo con una frase.

---

## 1. Qué es y cómo funciona

El agente no es una aplicación que se abre sola. Es una carpeta con instrucciones y
herramientas que lee un **asistente de IA con acceso a tu ordenador**: Claude Code o
Codex. Tú le hablas en español, y él:

1. la primera vez te pregunta qué temas quieres vigilar, cuántos artículos, qué
   secciones y qué aspecto quieres que tenga el boletín;
2. cada vez que se lo pidas busca en las bases de datos que hayas elegido,
   descarta lo que no es Terapia Ocupacional o no encaja en tus temas, resume lo que
   queda y te entrega un PDF.

No funciona solo ni de forma programada: se ejecuta cuando tú lo pides.

---

## 2. Qué necesitas

| Qué | Para qué | Coste |
|---|---|---|
| Un ordenador con **Mac** o **Windows** | Donde vive la carpeta | |
| **Claude Code** (recomendado) o **Codex** | El asistente que hace de agente | Requiere suscripción: Claude Pro o superior, o ChatGPT Plus o superior |
| **Python 3.10 o posterior** | Para ejecutar las herramientas | Gratuito |
| **Google Chrome** o **Microsoft Edge** | Para convertir el boletín a PDF | Gratuito |

Cada boletín consume parte del uso incluido en tu suscripción. Un número de 10
artículos es una sesión de trabajo moderada.

---

## 3. Instalación

### Paso 1. Descarga y descomprime la carpeta

Descarga el archivo `.zip` desde la web y descomprímelo donde quieras guardarlo, por
ejemplo en `Documentos`. La carpeta se llama `vigilancia-to`. No la cambies de sitio
después, o el asistente tendrá que volver a encontrarla.

### Paso 2. Instala Python

- **Mac**: ve a https://www.python.org/downloads/ , descarga el instalador para macOS
  y ábrelo. Siguiente, siguiente, instalar.
- **Windows**: en la misma web, descarga el instalador para Windows. **Muy importante:
  en la primera pantalla marca la casilla «Add python.exe to PATH»** antes de pulsar
  «Install Now».

No hace falta que abras Python ni que sepas usarlo: el asistente lo hace por ti.

### Paso 3. Comprueba que tienes Chrome o Edge

En Windows, Edge viene instalado. En Mac, si no tienes Chrome, descárgalo de
https://www.google.com/chrome/ .

### Paso 4. Instala el asistente

**Opción A, Claude Code (recomendada).**
1. Descarga la aplicación de escritorio de Claude desde https://claude.ai/download e
   inicia sesión con tu cuenta.
2. Entra en la pestaña **Code**.
3. Elige **abrir una carpeta** y selecciona `vigilancia-to`.

**Opción B, Codex.**
1. Instala Codex siguiendo las instrucciones oficiales de OpenAI
   (https://developers.openai.com/codex) e inicia sesión con tu cuenta de ChatGPT.
2. Abre la carpeta `vigilancia-to` como espacio de trabajo.

En los dos casos, el asistente lee al abrir la carpeta el archivo de instrucciones que
le corresponde (`CLAUDE.md` o `AGENTS.md`) y ya sabe lo que tiene que hacer.

### Paso 5. La primera vez: configurar tu boletín

Escribe:

> Quiero configurar mi boletín de vigilancia.

El asistente te irá preguntando, de una en una, por:

1. **Tema y ámbitos.** La Terapia Ocupacional es siempre el eje; tú eliges con qué se
   cruza: nuevas tecnologías, infancia, salud mental, neurorrehabilitación, exclusión
   social, personas mayores... y dentro del tema, entre 2 y 7 ámbitos que serán los
   capítulos del boletín. Él prepara los términos de búsqueda en inglés, español y
   portugués y te los enseña para que los revises.
2. **Tamaño.** Cuántos artículos por número (sugiere 10) y qué periodo revisar por
   defecto (sugiere los últimos 30 días).
3. **Secciones fijas.** Los bloques que abren cada número: «El artículo del número»,
   «Lo que toca la práctica», «Para llevar a clase», «Pregunta para el equipo»... Te
   enseña un catálogo y puedes inventar las tuyas.
4. **Estética.** Cuatro plantillas de partida (azul, clásica, cálida y sobria) que
   puedes personalizar con tus colores, tus tipografías y tu logo. Te genera un PDF de
   muestra para que lo veas antes de decidir.
5. **Tus datos.** Tu nombre, institución y contacto como editora o editor del boletín.
   Es opcional.
6. **Descarga de artículos.** Si quieres que baje los PDF de acceso abierto a tu
   ordenador o que solo los enlace.
7. **Bases de datos.** Por defecto busca en PubMed, Europe PMC, OpenAlex y Crossref,
   que son gratuitas. Puedes añadir Semantic Scholar, arXiv o DOAJ, también gratuitas,
   y Scopus, Web of Science, IEEE Xplore o Consensus si tienes clave (normalmente a
   través de la biblioteca de tu universidad). Las claves se guardan en un archivo
   aparte, `claves.json`, que no debes compartir nunca.
8. **Un correo de contacto.** Las bases de datos lo piden para identificar las
   consultas. No te llegará nada ni se usa para otra cosa.

Si quieres usar tu logo o tus tipografías, antes de empezar copia los archivos en la
carpeta `estilo/`.

Toda la configuración se guarda en `perfil.json` y no tendrás que repetirla.

La primera vez, el asistente te pedirá **permiso** para ejecutar comandos (instalar
una librería, lanzar la búsqueda). Es normal: acepta los que sean de esta carpeta.

---

## 4. Uso: pedir un boletín

Cada vez que quieras un número, escribe algo como:

> Hazme un boletín.
> Hazme un boletín de los últimos 90 días.
> Prepara el boletín desde el 1 de enero.

El asistente busca, filtra, resume y genera el PDF. Tarda entre 10 y 30 minutos según
el número de artículos. Al terminar te dice dónde está el archivo (carpeta
`boletines/`), cuántos artículos lleva y cuáles descartó y por qué.

**Revisa siempre el boletín antes de difundirlo.** Está hecho con IA y tú respondes de
su contenido como editora o editor.

El agente recuerda lo que ya publicaste: un artículo no sale dos veces en números
distintos. A partir del segundo número puede señalar los temas que se repiten.

---

## 5. Cambiar la configuración

Basta con decirlo:

> Quiero añadir el ámbito «salud mental perinatal».
> Cambia los colores a verde y gris.
> Quita la sección «En el radar» y pon «Para llevar a clase».
> A partir de ahora, 15 artículos por número.
> Activa la descarga de los PDF.

---

## 6. Autoría y licencia

El agente es obra de **José María Calavia Balduz** y se distribuye con licencia
**Creative Commons BY-NC-SA 4.0**. En resumen:

- Puedes usarlo, compartirlo y adaptarlo gratis.
- Cada boletín lleva, en la portada y en la página de créditos, la línea «Agente de
  vigilancia diseñado por José María Calavia Balduz». No se puede quitar, y el
  asistente no lo hará aunque se lo pidas.
- Tu nombre y tu logo aparecen como editora o editor del boletín.
- No se puede usar con fines comerciales.
- Si lo modificas y lo compartes, mantén la misma licencia y la autoría original.

Los detalles están en `LICENCIA.md`.

---

## 7. Problemas frecuentes

**«No encuentro Python» o «python3 no se reconoce».** En Windows, reinstala Python
marcando «Add python.exe to PATH». En cualquier caso, díselo al asistente: suele saber
arreglarlo.

**«No encuentro Google Chrome, Chromium ni Microsoft Edge».** Instala Chrome. Si lo
tienes en un sitio poco habitual, dile al asistente dónde está.

**Salen muy pocos artículos.** Pide un periodo más largo («de los últimos 6 meses») o
pide que revise los términos de búsqueda de los ámbitos.

**Se cuela algún artículo que no encaja.** Dile cuál y por qué. El asistente lo
sustituye por un suplente y puede afinar el criterio del perfil para la próxima vez.

**Una base de datos no responde.** A veces una base se cae. El asistente te avisa y el
boletín sale con las demás.

**Quiero empezar de cero.** Borra `perfil.json` (configuración) y la carpeta `datos/`
(memoria de números anteriores) y vuelve al paso 5.
