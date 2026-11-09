# 🪄 Palantidy

**Palantidy** es un puente (Addon de Stremio) de alto rendimiento que conecta el catálogo completo de **Palantir** con la interfaz moderna de **Stremio** en Google TV, Android TV, PC y móviles.

---

## ⚡ ¿Por qué Palantidy?

| Antes (Kodi + Palantir en Google TV) | Ahora (Stremio + Palantidy) |
|---|---|
| ❌ Menús lentos y pesados en la TV | ⚡ Navegación nativa fluida a 60 fps |
| ❌ Búsqueda tosca e incómoda | 🔍 Búsqueda instantánea y control por voz con el mando |
| ❌ Carga lenta de carátulas | 🖼️ Portadas y metadatos instantáneos desde CDN |
| ❌ Interfaz anticuada | 🎬 Diseño estilo Netflix / Apple TV |
| ❌ Servidores de Kodi colgados | 🚀 Enlaces directos desbloqueados por Debrid en < 1s |

---

## 🗄️ Catálogo Indexado

El catálogo se extrae y sincroniza directamente desde la base de datos oficial de Palantir (**Moria**):
- **30.000+** películas indexadas.
- **9.000+** series completas.
- **500.000+** enlaces de episodios en Castellano, Dual y 4K HDR / Dolby Vision.

---

## 🚀 Inicio Rápido

### 1. Requisitos
- Python 3.10 o superior instalado.
- Cuenta en **Real-Debrid**, **AllDebrid** o **1fichier** (para streaming directo sin esperas).

### 2. Instalación de dependencias
```bash
pip install -r requirements.txt
```

### 3. Iniciar el servidor
```bash
python main.py
```
> La primera vez descargará e indexará la base de datos `moria.db` automáticamente en unos segundos.

### 4. Configurar e Instalar en Stremio
1. Abre en tu navegador: [http://localhost:7000](http://localhost:7000).
2. Selecciona tu proveedor Debrid (p. ej. *Real-Debrid*) y pega tu API Key.
3. Haz clic en el botón **"Instalar en Stremio"**.
4. ¡Listo! Al tener tu cuenta de Stremio sincronizada, el addon aparecerá automáticamente en tu **Google TV**.

---

## 🛠️ Comandos útiles

* **Actualizar la base de datos manualmente:**
  ```bash
  python main.py --sync
  ```
* **Forzar re-descarga completa del catálogo:**
  ```bash
  python main.py --force-sync
  ```
* **Cambiar el puerto del servidor:**
  ```bash
  python main.py --port 8080
  ```

---

## 📡 Ejecución como servicio / En la nube
Puedes dejar este servidor corriendo en:
- Tu PC local o portátil en la red doméstica.
- Un mini-PC, NAS (Synology, Unraid, TrueNAS) o Raspberry Pi con Docker.
- Un servicio gratuito o VPS en la nube (Render, Railway, HuggingFace Spaces) para tenerlo 24/7 sin depender de un PC encendido.
