from ml_wartungsplan.features.text import (
    frequency_hint,
    technical_location_area,
)


def test_location_area() -> None:
    assert technical_location_area("8160-330/00000001") == "8160-330"


def test_frequency_week() -> None:
    assert frequency_hint("wöchentlicher TPM Wartungsplan") == "week"


def test_frequency_quarter() -> None:
    assert frequency_hint("vierteljährliche Schaltschrankwartung") == "quarter"


def test_multiple_intervals() -> None:
    assert frequency_hint("Mechanik Luftaufbereiter 6M / 1J") == "multiple"
