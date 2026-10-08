# Agente de vigilancia de literatura en Terapia Ocupacional

[![Licencia: CC BY-NC-SA 4.0](https://img.shields.io/badge/Licencia-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23249237.svg)](https://doi.org/10.5281/zenodo.23249237)

Diseño original: **José María Calavia Balduz** · Licencia CC BY-NC-SA 4.0

Un agente de IA que, cuando se lo pides, busca la investigación reciente de Terapia Ocupacional en los ámbitos que elijas (tecnología, infancia, salud mental, neurorrehabilitación, exclusión social...), descarta el ruido, resume en español lo que merece la pena y te entrega un boletín en PDF con tu diseño.

## Para quién es

Para terapeutas ocupacionales, docentes, estudiantes y equipos que quieren estar al día de la literatura científica sin dedicar horas a buscar. No hace falta saber programar.

## Qué necesitas

| Qué | Para qué | Coste |
|---|---|---|
| Un ordenador con Mac o Windows | Donde vive la carpeta | |
| Claude Code (recomendado) o Codex | El asistente que hace de agente | Suscripción Claude Pro o superior, o ChatGPT Plus o superior |
| Python 3.10 o posterior | Para ejecutar las herramientas | Gratuito |
| Google Chrome o Microsoft Edge | Para convertir el boletín a PDF | Gratuito |

## Instalación

1. Descarga la última versión desde [Releases](https://github.com/josemcalavia/agente-vigilancia-to/releases/latest) (archivo `.zip`) y descomprímela, por ejemplo en `Documentos`. También puedes clonar el repositorio.
2. Instala Python desde https://www.python.org/downloads/ . En Windows, marca la casilla «Add python.exe to PATH».
3. Comprueba que tienes Chrome o Edge.
4. Abre la carpeta con tu asistente:
   - **Claude Code**: descarga la aplicación de escritorio desde https://claude.ai/download , entra en la pestaña **Code** y abre la carpeta.
   - **Codex**: instálalo siguiendo https://developers.openai.com/codex y abre la carpeta como espacio de trabajo.

El asistente lee al abrir la carpeta su archivo de instrucciones (`CLAUDE.md` o `AGENTS.md`) y ya sabe lo que tiene que hacer. La guía completa, paso a paso, está en [`GUIA.pdf`](GUIA.pdf) y [`GUIA.md`](GUIA.md).

## Uso básico

La primera vez escribe:

> Quiero configurar mi boletín de vigilancia.

El asistente te pregunta por el tema y los ámbitos, el número de artículos, las secciones, la estética, tus datos como editor y las bases de datos. Todo se guarda en `perfil.json`.

Después, cada número es una frase:

> Hazme un boletín.
> Hazme un boletín de los últimos 90 días.

El PDF queda en la carpeta `boletines/`. Revísalo siempre antes de difundirlo: está hecho con IA y quien lo edita responde de su contenido.

## Qué hay en la carpeta

| Archivo | Para qué sirve |
|---|---|
| `GUIA.pdf`, `GUIA.md` | Guía de instalación y uso, paso a paso |
| `INSTRUCCIONES.md` | Lo que lee el agente: cómo configurar y preparar cada boletín |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | Puntos de entrada para Claude Code, Codex y Gemini CLI |
| `LEEME.md` | Resumen breve |
| `LICENCIA.md`, `LICENSE` | Condiciones de uso y texto legal de la licencia |
| `perfil_ejemplo.json` | Ejemplo de configuración |
| `claves_ejemplo.json` | Plantilla para las claves de bases de pago, si las tienes |
| `herramientas/` | Scripts de búsqueda, maquetación y memoria |
| `estilo/` | Deja aquí tu logo y, si quieres, tus tipografías |
| `ejemplo/` | Datos de muestra |

Los archivos personales (`perfil.json`, `claves.json`, `datos/`, `boletines/`, `articulos/`) se crean al usarlo y no se suben nunca al repositorio.

## Autoría

**José María Calavia Balduz** ([ORCID 0009-0001-7105-2022](https://orcid.org/0009-0001-7105-2022)), CSEU La Salle (adscrito a la UAM) y Centro Tangram.
Contacto: josemcalavia@me.com

## Licencia

[Creative Commons Reconocimiento-NoComercial-CompartirIgual 4.0 Internacional (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.es). Puedes usarlo, compartirlo y adaptarlo sin fines comerciales, manteniendo la autoría original y la misma licencia. Cada boletín lleva la línea «Agente de vigilancia diseñado por José María Calavia Balduz», que no se puede quitar. Detalles en [`LICENCIA.md`](LICENCIA.md).

## Cómo citar

Calavia Balduz, J. M. (2026). *Agente de vigilancia de literatura en Terapia Ocupacional* (Versión 1.0.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.23249237

Este DOI (10.5281/zenodo.23249237) agrupa todas las versiones y siempre apunta a la más reciente; cada versión tiene además su propio DOI en Zenodo. También puedes usar el botón «Cite this repository» de GitHub, que lee `CITATION.cff`.
