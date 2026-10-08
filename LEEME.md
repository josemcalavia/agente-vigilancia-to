# Agente de vigilancia de literatura en Terapia Ocupacional

Diseño original: **José María Calavia Balduz** · Licencia CC BY-NC-SA 4.0

Un agente que, cuando se lo pides, busca la investigación reciente de Terapia
Ocupacional en los ámbitos que tú elijas (tecnología, infancia, salud mental,
neurorrehabilitación, exclusión social...), descarta el ruido, resume en español lo
que merece la pena y te entrega un boletín en PDF con tu diseño.

**Para instalarlo y usarlo, sigue `GUIA.pdf` (o `GUIA.md`, el mismo contenido en texto).**

## Qué hay en la carpeta

| Archivo | Para qué sirve |
|---|---|
| `GUIA.pdf`, `GUIA.md` | Guía de instalación y uso, paso a paso |
| `INSTRUCCIONES.md` | Lo que lee el agente: cómo configurar y preparar cada boletín |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | Puntos de entrada para Claude Code, Codex y Gemini CLI |
| `LICENCIA.md` | Condiciones de uso |
| `perfil_ejemplo.json` | Ejemplo de configuración (la tuya se crea sola la primera vez) |
| `claves_ejemplo.json` | Plantilla para las claves de bases de pago, si las tienes |
| `herramientas/` | Los scripts de búsqueda, maquetación y memoria |
| `estilo/` | Deja aquí tu logo y, si quieres, tus tipografías |

Al usarlo se crean `perfil.json` (tu configuración), `datos/` (memoria entre
números), `boletines/` (los PDF) y, si activas la descarga, `articulos/`.
