"""
Script para generar PDF desde HTML de presentación de Clima Narrado.
Requiere: weasyprint o pdfkit
"""

import os
import sys
from pathlib import Path


def generate_pdf_with_weasyprint():
    """Genera PDF usando weasyprint (recomendado)."""
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        # Rutas
        base_dir = Path(__file__).parent
        html_file = base_dir / "SkyPulse.html"
        pdf_file = base_dir / "SkyPulse.pdf"

        if not html_file.exists():
            print(f"Error: No se encuentra {html_file}")
            return False

        print("Generando PDF con WeasyPrint...")

        # Generar PDF
        HTML(filename=str(html_file)).write_pdf(
            str(pdf_file),
            stylesheets=[
                CSS(
                    string="""
                    @page {
                        size: A4;
                        margin: 1.5cm;
                    }
                    @media print {
                        .hero {
                            page-break-after: always;
                        }
                        .section {
                            page-break-inside: avoid;
                        }
                    }
                """
                )
            ],
        )

        print(f"✅ PDF generado exitosamente: {pdf_file}")
        return True

    except ImportError:
        print("❌ WeasyPrint no está instalado.")
        print("Instalar con: pip install weasyprint")
        return False
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return False


def generate_pdf_with_pdfkit():
    """Genera PDF usando pdfkit (alternativa)."""
    try:
        import pdfkit

        # Rutas
        base_dir = Path(__file__).parent
        html_file = base_dir / "SkyPulse.html"
        pdf_file = base_dir / "SkyPulse.pdf"

        if not html_file.exists():
            print(f"Error: No se encuentra {html_file}")
            return False

        print("Generando PDF con pdfkit...")

        # Opciones para PDF
        options = {
            "page-size": "A4",
            "margin-top": "1.5cm",
            "margin-right": "1.5cm",
            "margin-bottom": "1.5cm",
            "margin-left": "1.5cm",
            "encoding": "UTF-8",
            "no-outline": None,
            "enable-local-file-access": None,
        }

        # Generar PDF
        pdfkit.from_file(str(html_file), str(pdf_file), options=options)

        print(f"✅ PDF generado exitosamente: {pdf_file}")
        return True

    except ImportError:
        print("❌ pdfkit no está instalado.")
        print("Instalar con: pip install pdfkit")
        print("También necesitas wkhtmltopdf: https://wkhtmltopdf.org/downloads.html")
        return False
    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return False


def main():
    """Función principal."""
    print("=" * 60)
    print("Generador de PDF - SkyPulse")
    print("=" * 60)
    print()

    # Intentar con WeasyPrint primero (más fácil)
    if generate_pdf_with_weasyprint():
        return

    # Si falla, intentar con pdfkit
    print("\nIntentando con pdfkit...")
    if generate_pdf_with_pdfkit():
        return

    print("\n❌ No se pudo generar el PDF.")
    print("\nOpciones:")
    print("1. Instalar WeasyPrint: pip install weasyprint")
    print("2. Instalar pdfkit + wkhtmltopdf")
    print("3. Usar el navegador: Abrir HTML y 'Imprimir' -> 'Guardar como PDF'")


if __name__ == "__main__":
    main()
