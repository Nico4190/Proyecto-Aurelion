import os
import re
from pathlib import Path
import unicodedata

class Menu():
    """Interactive menu to navigate the project markdown documentation.

    Public methods:
    - seleccionar(): run the interactive loop
    - mostrar(), general(), dataset(), pasos_programa(), pseudocodigo_diagrama(), sugerencias_copilot()
    """
    def __init__(self):
        self.opcion = 0
        self.salir = False
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.doc_path = os.path.join(self.base_dir, "documentacion.md")
        self.self_path = os.path.abspath(__file__)

        if not os.path.exists(self.doc_path):
            print("Error: No se encontró el archivo 'documentacion.md'.")
            # Raise an OSError so callers (or tests) can handle this programmatically
            raise OSError("documentacion.md no encontrado en: {}".format(self.doc_path))

        try:
            self.lines = self.read_lines(Path(self.doc_path))
        except Exception as e:
            # Bubble up a descriptive error
            raise IOError(f"Error leyendo {self.doc_path}: {e}")
        self.paras = self.all_paragraphs(self.lines)

    ''' HELPER FUNCTIONS
    '''

    def limpiar_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def read_lines(self, path):
        """Return the file content as a list of lines using UTF-8 encoding.

        Raises
        ------
        IOError: if the file cannot be read.
        """
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            raise IOError(f"No se pudo leer el archivo {path}: {e}")

    def parse_headings(self, lines):
        """Return list of (line_no, level, title)."""
        headings = []
        for i, ln in enumerate(lines):
            m = re.match(r'^(#{1,6})\s*(.+)$', ln)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                headings.append((i, level, title))
        return headings
    
    def all_paragraphs(self, lines):
        """Return list of paragraphs across the whole document (headings excluded)."""
        paras = []
        buf = []
        for ln in lines:
            if re.match(r'^(#{1,6})\s*', ln):
                continue
            if ln.strip() == "":
                if buf:
                    paras.append("\n".join(buf).strip())
                    buf = []
            else:
                buf.append(ln)
        if buf:
            paras.append("\n".join(buf).strip())
        return paras

    def get_section(self, lines, title_search):
        """Find section whose title contains title_search (case-insensitive)."""
        headings = self.parse_headings(lines)
        for idx, level, title in headings:
            if title_search.lower() in title.lower():
                start = idx + 1
                end = len(lines)
                for idx2, level2, _ in headings:
                    if idx2 > idx and level2 <= level:
                        end = idx2
                        break
                return lines[start:end]
        return []

    def extract_code_block(self, lines):
        """Extrae el bloque de código contenido entre ``` ... ```"""
        inside_code = False
        code_lines = []
        for ln in lines:
            if ln.strip().startswith("```"):
                inside_code = not inside_code
                continue
            if inside_code:
                code_lines.append(ln)
        return "\n".join(code_lines).strip()

    def show_text(self, text):
        """Clear the terminal, print `text` and wait for the user to press Enter.

        Handles KeyboardInterrupt gracefully so the program can exit cleanly
        from anywhere the user presses Ctrl+C.
        """
        self.limpiar_terminal()
        print("\n" + text + "\n")
        try:
            input("Presione Enter para regresar al menú...")
        except KeyboardInterrupt:
            # Allow the user to interrupt and return to the main loop safely
            print("\nInterrumpido por el usuario. Volviendo al menú...")

    ''' MENU MODULES
    '''

    def mostrar(self):
        self.limpiar_terminal()
        print("¡Bienvenido a la documentación del proyecto 01: Tienda Aurelion!")
        print("\nSeleccione la opción deseada:")
        print("1. Información general")
        print("2. Dataset de referencia")
        print("\nPuedes consultar también sobre el trabajo detrás de este programa interactivo:")
        print("3. Información y pasos del programa")    
        print("4. Pseudocódigo y diagrama")
        print("5. Sugerencias de Copilot")
        print("\n6. Salir")

    def general(self):
        """Mostrar la sección 'Información general' desde `documentacion.md`.

        Si la sección no existe, muestra un mensaje informativo.
        """
        sec_lines = self.get_section(self.lines, "Información general")
        if not sec_lines:
            self.show_text("No se encontró la sección 'Información general' en el documento.")
            return
        text = "\n".join(sec_lines).strip()
        self.show_text(text)

    def dataset(self):
        """Mostrar submenú del Dataset con opciones 'a' (resumen) y 'b' (detalle).

        Esta función maneja entradas inválidas y permite regresar con Enter.
        """
        while True:
            self.limpiar_terminal()
            print("\nSubmenú de Dataset:")
            print("a) Resumen")
            print("b) Detalle")
            print("Presione Enter para regresar al menú principal.")
            choice = input("Elija a/b\n").strip().lower()

            if choice == "a":
                # Mostrar desde el encabezado nivel 2 'Dataset de referencia'
                # hasta antes del encabezado nivel 3 'Tabla clientes' (incluyendo encabezados)
                headings = self.parse_headings(self.lines)

                def _norm(s):
                    s2 = unicodedata.normalize('NFD', s)
                    s2 = ''.join(c for c in s2 if unicodedata.category(c) != 'Mn')
                    return s2.lower()

                ds_idx = None
                tabla_idx = None
                for idx, level, title in headings:
                    n = _norm(title)
                    if ds_idx is None and level == 2 and 'dataset' in n and 'referenc' in n:
                        ds_idx = idx
                    if tabla_idx is None and level == 3 and 'tabla' in n and 'clientes' in n:
                        tabla_idx = idx

                if ds_idx is None:
                    self.show_text("No se encontró la sección 'Dataset de referencia' en el documento.")
                    continue
                if tabla_idx is None or tabla_idx <= ds_idx:
                    self.show_text("No se encontró el subtítulo 'Tabla clientes' después de 'Dataset de referencia'.")
                    continue

                out_lines = self.lines[ds_idx:tabla_idx]
                self.show_text("\n".join(out_lines).strip())

            elif choice == "b":
                # Mostrar desde el subtítulo nivel 3 'Tabla clientes' hasta antes del
                # subtítulo nivel 2 'Programa Interactivo' (incluyendo encabezados)
                headings = self.parse_headings(self.lines)

                def _norm(s):
                    s2 = unicodedata.normalize('NFD', s)
                    s2 = ''.join(c for c in s2 if unicodedata.category(c) != 'Mn')
                    return s2.lower()

                tabla_idx = None
                prog_idx = None
                for idx, level, title in headings:
                    n = _norm(title)
                    if tabla_idx is None and level == 3 and 'tabla' in n and 'clientes' in n:
                        tabla_idx = idx
                    if prog_idx is None and level == 2 and 'programa' in n and 'interact' in n:
                        # first level-2 match for 'Programa Interactivo' after tabla
                        prog_idx = idx

                if tabla_idx is None:
                    self.show_text("No se encontró el subtítulo 'Tabla clientes' en el documento.")
                    continue

                # Si no se encontró 'Programa Interactivo' después, tomar hasta el final
                end_idx = prog_idx if (prog_idx and prog_idx > tabla_idx) else len(self.lines)
                out_lines = self.lines[tabla_idx:end_idx]
                self.show_text("\n".join(out_lines).strip())

            elif choice == "":
                return

    def pasos_programa(self):
        """Mostrar la sección 'Pasos' del documento.

        No falla si la sección no existe (silencioso).
        """
        sec_lines = self.get_section(self.lines, "Pasos")
        if not sec_lines:
            self.show_text("No se encontró la sección 'Pasos' en el documento.")
            return
        text = "\n".join(sec_lines).strip()
        if text:
            self.show_text(text)

    def pseudocodigo_diagrama(self):
        """
        Extrae e imprime las subsecciones de nivel 3 relacionadas con
        'Pseudocódigo' y 'Diagrama' (incluyendo sus propias líneas de
        encabezado) desde el documento.
        """
        headings = self.parse_headings(self.lines)
        if not headings:
            self.show_text("No se encontraron encabezados en el documento.")
            return

        # Normalizar para comparar sin tildes
        def _norm(s):
            s2 = unicodedata.normalize('NFD', s)
            s2 = ''.join(c for c in s2 if unicodedata.category(c) != 'Mn')
            return s2.lower()

        terms = ["pseudocodigo", "diagrama"]
        sections = []

        for idx, level, title in headings:
            # Buscamos subtítulos de nivel 3 que contengan los términos
            if level != 3:
                continue
            low_title = _norm(title)
            if any(t in low_title for t in terms):
                # Incluir la línea de encabezado (start = idx)
                start = idx
                end = len(self.lines)
                for idx2, level2, _ in headings:
                    if idx2 > idx and level2 <= level:
                        end = idx2
                        break
                section_lines = self.lines[start:end]
                sections.append("\n".join(section_lines).strip())

        if sections:
            # Mostrar las secciones encontradas, manteniendo títulos y formato
            out = "\n\n".join(sections)
            self.show_text(out)
        else:
            self.show_text("No se encontraron secciones de 'Pseudocódigo' o 'Diagrama' en el documento.")

    def sugerencias_copilot(self):
        # Buscamos la sección completa incluyendo su encabezado
        headings = self.parse_headings(self.lines)
        target_idx = None
        for idx, level, title in headings:
            if "sugerencias copilot" in title.lower():
                target_idx = idx
                target_level = level
                break

        if target_idx is None:
            self.show_text("No se encontró la sección 'Sugerencias Copilot'.")
            return

        start = target_idx
        end = len(self.lines)
        for idx2, level2, _ in headings:
            if idx2 > start and level2 <= target_level:
                end = idx2
                break

        # Normalizar función interna para comparaciones sin tildes
        def _norm(s):
            s2 = unicodedata.normalize('NFD', s)
            s2 = ''.join(c for c in s2 if unicodedata.category(c) != 'Mn')
            return s2.lower()

        # Recolectar subsecciones nivel 2 y 3 dentro del rango [start, end)
        sections = []
        # Build a list of headings within the doc for quick lookup
        for idx, level, title in headings:
            if idx < start or idx >= end:
                continue
            if level in (2, 3):
                # compute subsection end
                sub_start = idx
                sub_end = end
                for idx2, level2, _ in headings:
                    if idx2 > idx and idx2 < end and level2 <= level:
                        sub_end = idx2
                        break
                section_lines = self.lines[sub_start:sub_end]
                sections.append("\n".join(section_lines).strip())

        # If no level 2/3 headings found, fallback to show whole section (including header)
        if not sections:
            sec = self.lines[start:end]
            out = "\n".join(sec).strip()
            self.show_text(out if out else "No hay contenido en 'Sugerencias Copilot'.")
            return

        out = "\n\n".join(sections)
        self.show_text(out)

    def seleccionar(self):
        """Run the main interactive loop until the user chooses to exit.

        Handles ValueError for non-integer input and KeyboardInterrupt to exit
        gracefully when the user presses Ctrl+C.
        """
        while not self.salir:
            self.mostrar()
            try:
                raw = input("Seleccione una opción: ").strip()
                # allow empty input handling
                if raw == "":
                    input("Opción vacía. Presione Enter para continuar...")
                    continue
                self.opcion = int(raw)
                if self.opcion == 1:
                    self.general()
                elif self.opcion == 2:
                    self.dataset()
                elif self.opcion == 3:
                    self.pasos_programa()
                elif self.opcion == 4:
                    self.pseudocodigo_diagrama()
                elif self.opcion == 5:
                    self.sugerencias_copilot()
                elif self.opcion == 6:
                    self.limpiar_terminal()
                    print("Saliendo del programa...")
                    self.salir = True
                else:
                    input("Opción no válida. Presione Enter para continuar...")
            except ValueError:
                input("Entrada no válida. Presione Enter para continuar...")
            except KeyboardInterrupt:
                # Allow the user to quit with Ctrl+C
                print("\nInterrupción por teclado. Saliendo...")
                self.salir = True

if __name__ == "__main__":
    menu = Menu()
    menu.seleccionar()