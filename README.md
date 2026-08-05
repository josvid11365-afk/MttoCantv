# MttoCantv ⚙
**Gerencia General de Energía & Climatización Guárico**
Sistema de Registro de Mantenimiento – Región Los Llanos

---

## Agregar banner e ícono

Coloca tus archivos en la carpeta `assets/` antes de compilar:

```
mttocantv/
└── assets/
    ├── banner.png   ← Banner institucional (los 3 logos)
    └── icon.png     ← Ícono personalizado de la app
```

Después de instalar también puedes copiarlos manualmente:

**Linux:**
```bash
sudo cp banner.png /usr/share/mttocantv/banner.png
sudo cp icon.png   /usr/share/mttocantv/icon.png
```

**Windows:** copia `banner.png` e `icon.png` a la misma carpeta donde está `MttoCantv.exe`

---

## Instalación Linux Lite

```bash
sudo dpkg -i mttocantv_1.0.0_all.deb
sudo apt-get install -f
mttocantv
```

---

## Uso en Windows (Portable)

1. Descomprimir `MttoCantv_Windows_Portable.zip`
2. Doble clic en `MttoCantv.exe`
3. No requiere instalación — funciona en Windows 7, 10 y 11

La base de datos se guarda en:
```
C:\Users\TuUsuario\AppData\Roaming\mttocantv\registros.db
```

---

## Compartir base de datos entre equipos

```
Laptop Linux (casa)          Pendrive / Drive        PC Oficina (Windows)
───────────────────          ───────────────         ────────────────────
Guardar BD  ──────────────►  registros.db  ────────► Cargar BD
Registrar   ◄──────────────  registros.db  ◄──────── Registrar
```

1. En la app: botón **💾 Guardar BD** → guarda `registros.db`
2. Copia el archivo al otro equipo (pendrive, Telegram, Drive)
3. En el otro equipo: botón **📂 Cargar BD** → selecciona el archivo

---

## Funcionalidades

- **Autocompletar** en Central, Equipo y Técnicos (aprende de registros anteriores)
- Fecha en formato D/M/A con selector de calendario 📆
- Hora en formato 12h (AM/PM) tomada del sistema
- Tipos: Preventivo, Correctivo, Predictivo, Fuera de Servicio
- Campo Técnicos con código P00
- Exportar reporte **PDF** con formato institucional
- **Guardar / Cargar BD** para moverse entre equipos
- Editar y eliminar registros
- Búsqueda y filtros en tiempo real

---

## Publicar nueva versión

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions compilará automáticamente el `.deb` (Linux) y el `.exe` (Windows)
y los publicará como Release descargable.

---

## Dependencias (se instalan solas)

| Plataforma | Dependencias |
|---|---|
| Linux | `python3-tk`, `python3-pil`, `python3-reportlab` |
| Windows | Todo incluido en el `.exe` (PyInstaller) |
