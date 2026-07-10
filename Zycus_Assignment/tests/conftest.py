import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

SAMPLES_DIR = ROOT / "data" / "samples"


@pytest.fixture(scope="session")
def s2p_path():
    return SAMPLES_DIR / "S2P_Project.xlsx"


@pytest.fixture(scope="session")
def plan_b_path():
    return SAMPLES_DIR / "Project_Plan_B.xlsx"
