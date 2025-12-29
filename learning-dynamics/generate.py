from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).parent

INDEX_MD = ROOT / "index.md"
ABSTRACT_MD = ROOT / "abstract.md"
APPENDIX_MD = ROOT / "appendix.md"
OUT = ROOT / "article.tex"

PREAMBLE = r"""
\documentclass[11pt]{article}

% ----------------- Packages -----------------
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath, amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{geometry}
\usepackage{cite}

\geometry{a4paper, margin=1in}

\title{Learning Dynamics}
\author{Eric Hermosis \\ \texttt{eric.hermosis@gmail.com}}
\date{\today}

\begin{document}
\maketitle
"""

POSTAMBLE = r"""
\newpage
\bibliographystyle{unsrt}
\bibliography{references}
\end{document}
"""

# ----------------- Utilities -----------------

def strip_title(text: str) -> str:
    return re.sub(r"^\s*#\s+.*\n+", "", text)

def strip_citation_section(text: str) -> str:
    return re.sub(r"\n##\s+Citation[\s\S]*$", "", text)

def sanitize_unicode(text: str) -> str:
    text = text.replace("\u200B", "")
    return text

# ----------------- Converters -----------------

def convert_math(text: str) -> str:
    def repl(m):
        return "\\begin{equation}\n" + m.group(1).strip() + "\n\\end{equation}"
    return re.sub(r"\$\$(.*?)\$\$", repl, text, flags=re.S)

def convert_sections(text: str) -> str:
    # ### → subsection
    text = re.sub(r"^###\s+(.*)$", r"\\subsection*{\1}", text, flags=re.M)
    # ## → section
    text = re.sub(r"^##\s+(.*)$", r"\\section*{\1}", text, flags=re.M)
    return text

def convert_lists(text: str) -> str:
    lines = text.splitlines()
    out, in_list = [], False
    for line in lines:
        if re.match(r"^\s*-\s+", line):
            if not in_list:
                out.append(r"\begin{itemize}")
                in_list = True
            out.append(r"  \item " + line.lstrip("- ").strip())
        else:
            if in_list:
                out.append(r"\end{itemize}")
                in_list = False
            out.append(line)
    if in_list:
        out.append(r"\end{itemize}")
    return "\n".join(out)

def convert_citations(text: str) -> str:
    return re.sub(r"\[@([^\]]+)\]", r"\\cite{\1}", text)

def cleanup(text: str) -> str:
    return text.replace("&", r"\&").replace("%", r"\%")

def markdown_to_latex(text: str) -> str:
    text = convert_math(text)
    text = convert_sections(text)
    text = convert_lists(text)
    text = convert_citations(text)
    return cleanup(text)

# ----------------- Appendix handling -----------------

def convert_appendix(text: str) -> str:
    """
    Convert appendix markdown to LaTeX.
    The first ## header becomes the appendix section,
    subsequent ### headers become subsections.
    """
    lines, out = text.splitlines(), []
    first_section = True
    for line in lines:
        m_sec = re.match(r"^##\s+(.*)$", line)
        if m_sec and first_section: 
            out.append(rf"\section*{{Appendix: {m_sec.group(1)}}}") 
            first_section = False
            continue
        m_sub = re.match(r"^###\s+(.*)$", line)
        if m_sub:
            out.append(rf"\subsection*{{{m_sub.group(1)}}}")
            continue
        out.append(line)
    return markdown_to_latex("\n".join(out))

# ----------------- Transpiler -----------------

def transpile():
    abstract = sanitize_unicode(ABSTRACT_MD.read_text(encoding="utf-8").strip())
    body = sanitize_unicode(INDEX_MD.read_text(encoding="utf-8"))
    body = strip_title(body)
    body = strip_citation_section(body)

    abstract_tex = markdown_to_latex(abstract)
    body_tex = markdown_to_latex(body)

    appendix_tex = ""
    if APPENDIX_MD.exists():
        appendix_md = sanitize_unicode(APPENDIX_MD.read_text(encoding="utf-8"))
        appendix_tex = "\n\\newpage\n\\appendix\n\n" + convert_appendix(appendix_md)

    latex = (
        PREAMBLE
        + "\n\\begin{abstract}\n"
        + abstract_tex
        + "\n\\end{abstract}\n\n"
        + body_tex
        + appendix_tex
        + POSTAMBLE
    )

    OUT.write_text(latex, encoding="utf-8")
    print(f"Generated {OUT}")

    # ----------------- Compile PDF -----------------
    pdf_file = OUT.with_suffix(".pdf")
    try:
        subprocess.run(["pdflatex", str(OUT)], check=True)
        subprocess.run(["bibtex", OUT.stem], check=True)
        subprocess.run(["pdflatex", str(OUT)], check=True)
        subprocess.run(["pdflatex", str(OUT)], check=True)
        print(f"Generated PDF: {pdf_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during PDF compilation: {e}")

if __name__ == "__main__":
    transpile()
