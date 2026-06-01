from syntra.db.models import ValidationStatus
from syntra.services.validation import ValidationEngine


def test_validation_is_partial_without_known_commands(tmp_path):
    status, output = ValidationEngine().run(tmp_path, [])

    assert status == ValidationStatus.PARTIAL
    assert "No known validation" in output
