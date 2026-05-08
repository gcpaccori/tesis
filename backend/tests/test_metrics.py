from app.services.metrics import calculate_core_metrics


def test_accuracy_and_mcnemar_from_acceptance_case():
    rows = [
        {
            "codigo_imagen": "1",
            "ground_truth": "normal",
            "humano": "normal",
            "ia": "normal",
            "humano_correcto": True,
            "ia_correcto": True,
            "tiempo_humano": 10,
            "tiempo_ia": 40,
        },
        {
            "codigo_imagen": "2",
            "ground_truth": "normal",
            "humano": "normal",
            "ia": "danado",
            "humano_correcto": True,
            "ia_correcto": False,
            "tiempo_humano": 12,
            "tiempo_ia": 50,
        },
        {
            "codigo_imagen": "3",
            "ground_truth": "danado",
            "humano": "normal",
            "ia": "danado",
            "humano_correcto": False,
            "ia_correcto": True,
            "tiempo_humano": 8,
            "tiempo_ia": 30,
        },
        {
            "codigo_imagen": "4",
            "ground_truth": "larvas",
            "humano": "normal",
            "ia": "larvas",
            "humano_correcto": False,
            "ia_correcto": True,
            "tiempo_humano": 10,
            "tiempo_ia": 40,
        },
    ]

    metrics = calculate_core_metrics(rows)

    assert metrics["accuracy_humano"] == 0.5
    assert metrics["accuracy_modelo"] == 0.75
    assert metrics["mcnemar"]["a"] == 1
    assert metrics["mcnemar"]["b"] == 1
    assert metrics["mcnemar"]["c"] == 2
    assert metrics["mcnemar"]["d"] == 0


def test_time_factor_acceptance_case():
    rows = [
        {"ground_truth": "normal", "humano": "normal", "ia": "normal", "humano_correcto": True, "ia_correcto": True, "tiempo_humano": 10, "tiempo_ia": 40},
        {"ground_truth": "normal", "humano": "normal", "ia": "normal", "humano_correcto": True, "ia_correcto": True, "tiempo_humano": 12, "tiempo_ia": 50},
        {"ground_truth": "normal", "humano": "normal", "ia": "normal", "humano_correcto": True, "ia_correcto": True, "tiempo_humano": 8, "tiempo_ia": 30},
    ]

    metrics = calculate_core_metrics(rows)

    assert metrics["tiempos"]["promedio_humano"] == 10
    assert round(metrics["tiempos"]["promedio_ia"], 2) == 0.04
    assert round(metrics["tiempos"]["factor_velocidad"]) == 250
