import copy

import numpy as np
import pytest

from afabm.config import load_config
from afabm.model import make_world


@pytest.fixture(scope="session")
def cfg():
    return load_config("configs/quick.yaml")


@pytest.fixture()
def cfg_copy(cfg):
    return copy.deepcopy(cfg)


@pytest.fixture(scope="session")
def world(cfg):
    return make_world(cfg, np.random.default_rng(1))
