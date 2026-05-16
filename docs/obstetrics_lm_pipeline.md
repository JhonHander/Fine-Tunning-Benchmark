# Obstetrics Dataset Pipeline

Este documento describe el pipeline activo del proyecto. Los pipelines antiguos de MedQuad, BioASQ y PubMedQA fueron retirados.

## Flujo Principal

```text
PDFs en pdfs/obstetrics
  -> extracción por página
  -> limpieza clínica
  -> segmentación en chunks
  -> datasets/obstetrics/lm/train_lm.jsonl / validation_lm.jsonl / test_lm.jsonl
  -> QA sintético opcional
```

## Pipeline Incremental

Uso normal cuando agregas PDFs nuevos:

```bash
python scripts/run_incremental.py
```

Características:

- Detecta PDFs nuevos o modificados.
- Procesa solo esos PDFs.
- Reemplaza registros previos si un PDF cambió.
- Hace append de chunks aceptados a los JSONL existentes.
- Mantiene el manifiesto `artifacts/obstetrics/processed_pdfs_manifest.json`.

Opciones:

```bash
python scripts/run_incremental.py --recursive
python scripts/run_incremental.py --force
python scripts/run_incremental.py --keep-temp
python scripts/run_incremental.py --input-dir path/to/pdfs
```

## Reconstrucción Completa

Úsalo cuando cambies reglas de limpieza/chunking o quieras reproducir todo desde cero:

```bash
python scripts/run_full_pipeline.py
```

## Pasos Internos

Los runners llaman internamente:

```bash
python scripts/extract_pdfs.py
python scripts/clean_text.py
python scripts/build_lm_dataset.py
python scripts/audit_dataset.py
```

## Salidas LM

```text
artifacts/obstetrics/raw_pages.jsonl
artifacts/obstetrics/clean_pages.jsonl
artifacts/obstetrics/chunks.jsonl
datasets/obstetrics/lm/train_lm.jsonl
datasets/obstetrics/lm/validation_lm.jsonl
datasets/obstetrics/lm/test_lm.jsonl
artifacts/obstetrics/audit_report.json
```

Formato:

```json
{"text": "Texto clínico limpio...", "metadata": {"source": "obstetrics_spanish", "source_pdf": "...", "pages": [1, 2], "chunk_id": "..."}}
```

## QA Sintético

Dry run:

```bash
python scripts/generate_synthetic_qa.py --dry-run --limit 5
```

Generación real:

```bash
set OPENAI_API_KEY=your_key_here
python scripts/generate_synthetic_qa.py --limit 20
```

Salidas:

```text
datasets/obstetrics/qa/synthetic_qa_raw.jsonl
datasets/obstetrics/qa/synthetic_qa_sft.jsonl
datasets/obstetrics/qa/.qa_generation_progress.json
datasets/obstetrics/qa/qa_generation_report.json
```

Formato SFT:

```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], "metadata": {"source": "obstetrics_spanish_synthetic"}}
```

El checkpoint permite reanudar. Los errores de API no se marcan como procesados, por lo que se reintentan al relanzar.

## Notas

- `PyMuPDF` es el extractor principal.
- `pdfplumber` es fallback para páginas con poco texto.
- OCR real no está incluido todavía; páginas problemáticas se marcan como `needs_ocr`.
- Revisa `audit_report.json` antes de entrenar.
- Revisa `docs/research_notes/` para estado metodológico, decisiones y plan de benchmark.
