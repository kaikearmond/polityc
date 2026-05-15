from pathlib import Path
import gc
import math
import os
import sys
import time

import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

# Coloque o arquivo grande em uma destas duas opções:
# 1) data/votacao_candidato.csv.gz
# 2) votacao_candidato.csv.gz
RAW_CANDIDATES = [DATA_DIR / "votacao_candidato.csv.gz", BASE / "votacao_candidato.csv.gz"]
RAW_FILE = next((p for p in RAW_CANDIDATES if p.exists()), None)

if RAW_FILE is None:
    print("ERRO: coloque o arquivo votacao_candidato.csv.gz dentro da pasta data/ ou na raiz do projeto.")
    sys.exit(1)

OUT_FILE = DATA_DIR / "eleitos_zona.csv.gz"
TARGET_BYTES = 24 * 1024 * 1024  # para ficar abaixo do limite de 25 MiB do upload pelo navegador do GitHub

USECOLS = [
    "Gênero", "Nome candidato", "Ocupação", "Partido", "Situação totalização",
    "Faixa etária", "Cargo", "UF", "Ano de eleição", "Zona", "Votos nominais", "Turno",
]

GROUP_COLS = [
    "UF", "Zona", "Nome candidato", "Cargo", "Partido", "Gênero",
    "Ocupação", "Faixa etária", "Turno",
]


def split_if_needed(df: pd.DataFrame, file_path: Path):
    size = file_path.stat().st_size
    if size <= TARGET_BYTES:
        print(f"OK: arquivo final criado em {file_path} ({size / 1024 / 1024:.2f} MB).")
        return

    print(f"Arquivo ficou com {size / 1024 / 1024:.2f} MB. Vou dividir em partes menores.")
    file_path.unlink(missing_ok=True)

    rows_per_part = max(1, int(len(df) * (TARGET_BYTES / size) * 0.85))
    total_parts = math.ceil(len(df) / rows_per_part)

    for i in range(total_parts):
        part = df.iloc[i * rows_per_part : (i + 1) * rows_per_part]
        part_file = DATA_DIR / f"eleitos_zona_part{i+1:03d}.csv.gz"
        part.to_csv(part_file, index=False, compression="gzip")
        print(f"Parte {i+1}/{total_parts}: {part_file.name} ({part_file.stat().st_size / 1024 / 1024:.2f} MB)")

    print("Pronto. Suba para o GitHub os arquivos eleitos_zona_part*.csv.gz gerados na pasta data/.")


def main():
    print(f"Lendo arquivo grande: {RAW_FILE}")
    print("Isso pode demorar alguns minutos, mas só precisa ser feito uma vez.")
    start = time.time()
    chunks = []
    total_rows = 0
    filtered_rows = 0

    reader = pd.read_csv(
        RAW_FILE,
        sep=";",
        encoding="latin1",
        compression="gzip",
        usecols=USECOLS,
        chunksize=500_000,
        low_memory=False,
    )

    for i, chunk in enumerate(reader, start=1):
        total_rows += len(chunk)

        # O dashboard original mostra os candidatos eleitos.
        mask = (
            (chunk["Ano de eleição"] == 2022)
            & (chunk["Situação totalização"].astype(str).str.strip().str.upper() == "ELEITO")
        )
        c = chunk.loc[mask, GROUP_COLS + ["Votos nominais"]].copy()

        if not c.empty:
            c["Votos nominais"] = pd.to_numeric(c["Votos nominais"], errors="coerce").fillna(0).astype("int64")
            grouped = c.groupby(GROUP_COLS, dropna=False, as_index=False)["Votos nominais"].sum()
            chunks.append(grouped)
            filtered_rows += len(c)

        print(f"Chunk {i}: {total_rows:,} linhas lidas | {filtered_rows:,} linhas de eleitos".replace(",", "."))
        del chunk
        gc.collect()

    if not chunks:
        print("ERRO: não encontrei registros com Situação totalização = Eleito para 2022.")
        sys.exit(1)

    print("Consolidando dados...")
    df = pd.concat(chunks, ignore_index=True)
    zone_cands = df.groupby(GROUP_COLS, dropna=False, as_index=False)["Votos nominais"].sum()
    zone_cands = zone_cands.rename(columns={"Votos nominais": "votos_nominais"})

    totals = (
        zone_cands.groupby(["UF", "Nome candidato", "Cargo", "Partido", "Turno"], as_index=False)["votos_nominais"]
        .sum()
        .rename(columns={"votos_nominais": "total_votos"})
    )
    zone_cands = zone_cands.merge(
        totals,
        on=["UF", "Nome candidato", "Cargo", "Partido", "Turno"],
        how="left",
    )

    zone_cands = zone_cands.sort_values(
        ["UF", "Zona", "Cargo", "total_votos", "Nome candidato"],
        ascending=[True, True, True, False, True],
    )

    # Remove partes antigas, se existirem
    for old_part in DATA_DIR.glob("eleitos_zona_part*.csv.gz"):
        old_part.unlink(missing_ok=True)

    print("Gravando arquivo reduzido...")
    zone_cands.to_csv(OUT_FILE, index=False, compression="gzip")
    split_if_needed(zone_cands, OUT_FILE)

    elapsed = time.time() - start
    print(f"Finalizado em {elapsed / 60:.1f} minuto(s).")
    print("Agora rode: streamlit run app.py")


if __name__ == "__main__":
    main()
