import anthropic
import json

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Ești un expert în marketing digital și publicitate pe META (Facebook/Instagram).
Ai experiență vastă în crearea de campanii de succes, scripturi UGC, copywriting performant și analiza datelor publicitare.

Când analizezi date, ești meticulos și orientat spre rezultate concrete.
Când creezi conținut, ești creativ, persuasiv și adaptat publicului țintă.

Răspunzi întotdeauna în limba română, dacă nu ți se cere altfel.
Structurezi răspunsurile clar, cu secțiuni bine delimitate."""


def build_analysis_prompt(
    product_info: str,
    competition_info: str,
    ads_data: str,
    output_types: list[str],
) -> str:
    sections = []

    if product_info.strip():
        sections.append(f"## INFORMAȚII PRODUS/SERVICIU\n{product_info}")

    if competition_info.strip():
        sections.append(f"## DATE COMPETIȚIE / PIAȚĂ\n{competition_info}")

    if ads_data.strip():
        sections.append(f"## DATE RECLAME META (din fișier)\n{ads_data}")

    context = "\n\n".join(sections) if sections else "Nu au fost furnizate date."

    output_labels = {
        "concepts": "1. CONCEPTE DE CAMPANII (minim 3 concepte creative cu unghi de mesaj, hook și propunere de valoare)",
        "scripts": "2. SCRIPTURI VIDEO/UGC (2-3 scripturi complete, cu hook de 3 secunde, dezvoltare și CTA)",
        "copy": "3. COPY PENTRU RECLAME META (headline, primary text și CTA pentru fiecare concept)",
        "report": "4. RAPORT + RECOMANDĂRI (analiză date, ce funcționează, ce trebuie schimbat, pași următori)",
    }

    requested = [output_labels[t] for t in output_types if t in output_labels]
    outputs_section = "\n".join(requested) if requested else "\n".join(output_labels.values())

    return f"""Pe baza datelor de mai jos, creează următoarele:

{outputs_section}

---

{context}

---

Fii specific, practic și orientat spre conversii. Adaptează tot conținutul la contextul dat."""


def stream_analysis(
    product_info: str,
    competition_info: str,
    ads_data: str,
    output_types: list[str],
):
    """Generator that yields text chunks from Claude using streaming."""
    prompt = build_analysis_prompt(product_info, competition_info, ads_data, output_types)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text
