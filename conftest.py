import os
import sys

# NWS.py/NHC.py/util.py load Jinja templates and email fragments using paths
# ("templates/...") that are relative to the current working directory, and
# this repo has no package layout, so tests need the repo root on sys.path
# *and* as the cwd no matter where pytest is invoked from.
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pytest


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    """Keep tests offline and deterministic.

    Without this, a developer's shell (e.g. via direnv/.envrc) may already
    export real DEEPL_AUTH_KEY / AUTH_USER / SMTP_* credentials, which would
    make Translator() call the live DeepL API during "unit" tests and make
    assertions depend on translation output instead of parsing logic.
    """
    for var in (
        "DEEPL_AUTH_KEY",
        "DEEPL_GLOSSARY_ID",
        "AUTH_USER",
        "AUTH_SECRET",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
    ):
        monkeypatch.delenv(var, raising=False)
