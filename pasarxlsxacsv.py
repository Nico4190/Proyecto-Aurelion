"""
Script CLI para convertir archivos .xlsx a .csv.

Características:
- Convierte un archivo .xlsx individual o todos los .xlsx de una carpeta.
- Soporta múltiples hojas: primera, todas, por nombre o por índice.
- Opciones de separador, encoding, encabezados, index y sobreescritura.
- Manejo de errores claro (por ejemplo, dependencia openpyxl faltante).

Uso rápido (PowerShell):
  # Convertir todos los .xlsx del directorio actual (primera hoja)
  python pasarxlsxacsv.py .

    # Convertir un archivo específico (todas las hojas)
    python pasarxlsxacsv.py ruta\\al\\archivo.xlsx --sheets all

    # Convertir recursivamente una carpeta, enviar salida a otra carpeta
    python pasarxlsxacsv.py carpeta\\entrada -r -o carpeta\\salida

  # Elegir separador y encoding, incluyendo índices en el CSV
  python pasarxlsxacsv.py archivo.xlsx --sep ";" --encoding latin-1 --index
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convierte archivos .xlsx a .csv",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Ruta a un archivo .xlsx o a una carpeta con .xlsx",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Carpeta de salida para los .csv (por defecto, junto al origen)",
    )
    parser.add_argument(
        "-s",
        "--sheets",
        default="first",
        help=(
            "Hojas a exportar: 'first' (primera), 'all' (todas), "
            "lista separada por comas (nombres o índices 0..N)"
        ),
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Buscar .xlsx recursivamente en subcarpetas (solo cuando input es carpeta)",
    )
    parser.add_argument(
        "--sep",
        default=",",
        help="Separador de columnas para el CSV",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Encoding del archivo CSV (utf-8-sig suele abrir bien en Excel)",
    )
    parser.add_argument(
        "--no-header",
        dest="header",
        action="store_false",
        help="No escribir encabezados en el CSV",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Incluir índice en el CSV",
    )
    parser.add_argument(
        "-f",
        "--overwrite",
        action="store_true",
        help="Sobrescribir CSV si ya existe",
    )
    return parser.parse_args(argv)


def ensure_pandas() -> Tuple[object, Optional[Exception]]:
    try:
        import pandas as pd  # type: ignore

        return pd, None
    except Exception as ex:  # pragma: no cover - entorno
        return None, ex


def read_sheets_list(pd, xlsx_path: Path, sheets_opt: str) -> List[str]:
    """Devuelve la lista de nombres de hoja a exportar según la opción."""
    try:
        xl = pd.ExcelFile(xlsx_path)
    except ImportError as ex:
        raise RuntimeError(
            "Falta el motor de Excel (openpyxl). Instala con: pip install openpyxl"
        ) from ex
    except Exception as ex:
        raise RuntimeError(f"No se pudo abrir '{xlsx_path}': {ex}") from ex

    all_names: List[str] = list(xl.sheet_names)
    if not all_names:
        raise RuntimeError(f"El archivo '{xlsx_path}' no tiene hojas.")

    opt = sheets_opt.strip().lower()
    if opt == "first":
        return [all_names[0]]
    if opt == "all":
        return all_names

    # Parsear lista separada por comas (nombres o índices)
    requested = [s.strip() for s in sheets_opt.split(",") if s.strip()]
    result: List[str] = []
    for item in requested:
        # índice
        if item.isdigit():
            idx = int(item)
            if idx < 0 or idx >= len(all_names):
                raise RuntimeError(
                    f"Índice de hoja fuera de rango: {idx} (0..{len(all_names)-1})"
                )
            result.append(all_names[idx])
        else:
            # nombre
            if item in all_names:
                result.append(item)
            else:
                raise RuntimeError(
                    f"No existe la hoja '{item}'. Hojas disponibles: {', '.join(all_names)}"
                )
    return result


def safe_sheet_suffix(name: str) -> str:
    # Sanitizar para nombre de archivo
    keep = []
    for ch in name:
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
        else:
            keep.append("_")
    return "".join(keep).strip("_")


def convert_xlsx_to_csv(
    pd,
    xlsx_path: Path,
    out_dir: Path,
    sheets: List[str],
    sep: str = ",",
    encoding: str = "utf-8-sig",
    header: bool = True,
    index: bool = False,
    overwrite: bool = False,
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    multiple = len(sheets) > 1
    base = xlsx_path.stem

    for sheet_name in sheets:
        try:
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        except ImportError as ex:
            raise RuntimeError(
                "Falta el motor de Excel (openpyxl). Instala con: pip install openpyxl"
            ) from ex
        except Exception as ex:
            raise RuntimeError(
                f"No se pudo leer la hoja '{sheet_name}' de '{xlsx_path}': {ex}"
            ) from ex

        suffix = f"_{safe_sheet_suffix(sheet_name)}" if multiple else ""
        out_path = out_dir / f"{base}{suffix}.csv"

        if out_path.exists() and not overwrite:
            eprint(f"Omitido (ya existe): {out_path}")
            continue

        try:
            df.to_csv(out_path, sep=sep, encoding=encoding, header=header, index=index)
        except Exception as ex:
            raise RuntimeError(f"No se pudo escribir '{out_path}': {ex}") from ex

        print(f"✔ Exportado: {out_path}")
        created.append(out_path)

    return created


def iter_xlsx_files(root: Path, recursive: bool = False) -> Iterable[Path]:
    pattern = "**/*.xlsx" if recursive else "*.xlsx"
    for p in root.glob(pattern):
        # Omitir archivos temporales de Excel (~$Nombre.xlsx)
        if p.name.startswith("~$"):
            continue
        if p.is_file():
            yield p


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    pd, err = ensure_pandas()
    if err is not None:
        eprint("Error: pandas no disponible. Instala con: pip install pandas")
        eprint(str(err))
        return 2

    in_path = Path(args.input)
    if not in_path.exists():
        eprint(f"No existe la ruta: {in_path}")
        return 2

    out_dir = Path(args.output) if args.output else None

    try:
        if in_path.is_file():
            if in_path.suffix.lower() != ".xlsx":
                eprint(f"El archivo no es .xlsx: {in_path}")
                return 2
            sheets = read_sheets_list(pd, in_path, args.sheets)
            target_dir = out_dir or in_path.parent
            convert_xlsx_to_csv(
                pd,
                in_path,
                target_dir,
                sheets,
                sep=args.sep,
                encoding=args.encoding,
                header=args.header,
                index=args.index,
                overwrite=args.overwrite,
            )
        else:
            files = list(iter_xlsx_files(in_path, recursive=args.recursive))
            if not files:
                eprint("No se encontraron archivos .xlsx para convertir.")
                return 1
            print(f"Encontrados {len(files)} archivos .xlsx")

            for xlsx in files:
                try:
                    sheets = read_sheets_list(pd, xlsx, args.sheets)
                    # Si no se especificó salida, dejar CSV junto al archivo origen
                    target_dir = out_dir or xlsx.parent
                    convert_xlsx_to_csv(
                        pd,
                        xlsx,
                        target_dir,
                        sheets,
                        sep=args.sep,
                        encoding=args.encoding,
                        header=args.header,
                        index=args.index,
                        overwrite=args.overwrite,
                    )
                except Exception as ex:
                    eprint(f"Error con '{xlsx}': {ex}")
                    # Continuar con el siguiente archivo
            print("Proceso finalizado.")
    except RuntimeError as ex:
        eprint(str(ex))
        return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
