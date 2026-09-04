# documents-toolkit (`doctk`)

Utilerías de línea de comandos para procesar documentos: **CFDI/XML del SAT**, **PDFs**, **imágenes** y **comprobantes SPEI**.

Todos los comandos reciben rutas por parámetro — **no hay rutas ni datos personales hardcodeados**.

## Instalación

Requiere Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Instalación con todas las dependencias
pip install -e ".[all]"
```

Grupos de dependencias opcionales (por si sólo necesitas una parte):

| Grupo   | Instala                                             | Comandos que lo usan            |
|---------|-----------------------------------------------------|---------------------------------|
| `pdf`   | pypdf, pymupdf, pillow, reportlab, pdfplumber       | `pdf *`, `spei extract`         |
| `data`  | pandas, openpyxl, pyyaml                             | `cfdi *`, `spei extract`, `pdf form` (yaml) |
| `dev`   | ruff, pytest                                        | desarrollo                      |
| `all`   | pdf + data                                          | todo                            |

```bash
pip install -e ".[pdf]"        # sólo utilerías de PDF/imagen
pip install -e ".[all,dev]"    # todo + herramientas de desarrollo
```

## Uso

```bash
doctk --help
doctk pdf --help
doctk cfdi deductions --help
python -m doctk --help          # equivalente a doctk
```

Estructura de comandos: `doctk <grupo> <comando> [opciones]`.

### `cfdi` — CFDI/XML del SAT

```bash
# Concentrar deducciones personales de una carpeta de XML a Excel
doctk cfdi deductions --input ./xml_deducciones --year 2024 --output deducciones.xlsx

# Concentrar ingresos por nómina a Excel
doctk cfdi income --input ./xml_ingresos --year 2024 --output sueldos.xlsx

# Copiar y renombrar XML de forma legible (UsoCFDI - MES - RFC - UUID.xml)
doctk cfdi rename --input ./xml_deducciones --output ./xml_renombrados
```

### `pdf` — PDFs e imágenes

```bash
# Buscar texto/patrón en PDFs (acepta archivos, carpetas o globs)
doctk pdf search --path ./estados --keyword "2,500"
doctk pdf search --path ./estados --keyword "\d{2}/\d{2}/\d{4}" --regex

# Compilar imágenes y PDFs de una carpeta en un solo PDF tamaño Carta
doctk pdf merge --input ./imagenes --output compilado.pdf --dpi 300

# Intercalar frentes y reversos en un PDF doble cara
doctk pdf duplex --fronts ./frentes --backs ./reversos --output doble_cara.pdf --reverse-backs

# Eliminar páginas (por número o por rangos, base 1 inclusivo)
doctk pdf rmpages --input documento.pdf --pages 2 5 7
doctk pdf rmpages --input documento.pdf --ranges 1-5 40-45 --output recortado.pdf

# Formularios PDF (AcroForm): listar, exportar plantilla, rellenar, aplanar
doctk pdf form --input formato.pdf --list
doctk pdf form --input formato.pdf --list --export-yaml plantilla.yaml
doctk pdf form --input formato.pdf --data datos.yaml --output relleno.pdf
doctk pdf form --input formato.pdf --data datos.yaml --output relleno_flat.pdf --flatten
```

### `spei` — comprobantes SPEI

```bash
# Extraer fecha y monto de comprobantes SPEI a Excel
doctk spei extract --input ./comprobantes --output resultado.xlsx

# Dividir cada monto en dos porciones (ej. una comisión del 10%)
doctk spei extract --input ./comprobantes --split 0.10 --label-a Comision --label-b Neto
```

## Desarrollo

```bash
pip install -e ".[all,dev]"
ruff check src tests      # lint
ruff format src tests     # formato
pytest                    # tests smoke
```

## Estructura

```
src/doctk/
├── cli.py              # árbol de subcomandos (argparse)
├── common/             # utilerías compartidas (cfdi, pdfimg, excel, paths)
└── commands/           # un módulo por subcomando (add_arguments + run)
```

## Licencia

MIT — ver [LICENSE](LICENSE).
