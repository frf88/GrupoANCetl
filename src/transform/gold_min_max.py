import duckdb

# Tabla chica escrita directo en la Power Query original (sin fuente externa)
MIN_MAX = [
    ("Chuleton", 10, 20),
    ("Corazon de pollo", 10, 20),
    ("Cordero", 15, 25),
    ("Hongos", 10, 20),
    ("Keperi", 50, 60),
    ("Llama", 25, 35),
    ("Matambre de cerdo", 20, 30),
    ("Ojo de bife", 60, 70),
    ("Oreja de cerdo", 10, 20),
    ("Ossobuco", 25, 35),
    ("Panza", 20, 30),
    ("Pato", 15, 25),
    ("Pechuga de pollo", 20, 30),
    ("Pescado amazonico", 20, 30),
    ("Trucha", 35, 45),
]


def build_dim_min_max_porciones(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE OR REPLACE TABLE gold.dim_min_max_porciones (insumo VARCHAR, min_porc BIGINT, max_porc BIGINT)")
    con.executemany("INSERT INTO gold.dim_min_max_porciones VALUES (?, ?, ?)", MIN_MAX)
