from scripts.especialistas_liquidos import catalogo_especialistas


def main() -> None:
    print("La fase operativa fue desactivada en favor de la orquesta cognitiva.")
    print("Roles disponibles:")
    for especialista in catalogo_especialistas():
        print(f"- {especialista.nombre}: {especialista.foco}")
    print("Usa `python -m scripts.orquestador_director serve` para levantar la API.")


if __name__ == "__main__":
    main()
