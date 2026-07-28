import os
import sys
import numpy as np

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv
from gymnasium.spaces import Box as GymBox
import gymnasium as gym


SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL_PATH = os.path.join(SERVICE_DIR, "models", "aeroponic_ppo.zip")
DEFAULT_VEC_NORM_PATH = os.path.join(SERVICE_DIR, "models", "vec_normalize.pkl")


class _DummyAeroponicEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.observation_space = GymBox(
            low=np.array([0.0, 0.0, 15.0, 20.0, 15.0, 20.0, 0.5, 4.0, 18.0, 0.0], dtype=np.float32),
            high=np.array([300.0, 1.0, 30.0, 100.0, 30.0, 100.0, 3.5, 9.0, 25.0, 1.0], dtype=np.float32),
        )
        self.action_space = GymBox(low=np.array([-1.0, -1.0, -1.0], dtype=np.float32), high=np.array([1.0, 1.0, 1.0], dtype=np.float32))

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(10, dtype=np.float32), {}

    def step(self, action):
        return np.zeros(10, dtype=np.float32), 0.0, False, False, {}


class PPOModelLoader:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, vec_norm_path: str = DEFAULT_VEC_NORM_PATH, device: str = "cpu"):
        self.model_path = model_path
        self.vec_norm_path = vec_norm_path
        self.device = device
        self.model = None
        self.vec_norm = None
        self.loaded = False

    def load(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        if not os.path.exists(self.vec_norm_path):
            raise FileNotFoundError(f"VecNormalize not found: {self.vec_norm_path}")

        self.model = PPO.load(self.model_path, device=self.device)
        dummy_env = DummyVecEnv([lambda: _DummyAeroponicEnv()])
        self.vec_norm = VecNormalize.load(self.vec_norm_path, dummy_env)
        self.vec_norm.training = False
        self.vec_norm.norm_reward = False
        self.loaded = True
        return self

    def predict(self, state: list) -> np.ndarray:
        if not self.loaded:
            raise RuntimeError("Model not loaded")
        obs = np.array(state, dtype=np.float32).reshape(1, -1)
        obs = self.vec_norm.normalize_obs(obs)
        action, _ = self.model.predict(obs, deterministic=False)
        action = np.asarray(action).flatten()
        return self._map_action(action)

    def _map_action(self, action: np.ndarray) -> np.ndarray:
        a_01 = (action + 1.0) / 2.0
        D_mist = 60.0 + a_01[0] * (900.0 - 60.0)
        interval_sec = 60.0 + a_01[1] * (900.0 - 60.0)
        A_valve = 1.0 if action[2] >= 0.0 else 0.0
        return np.array([D_mist, interval_sec, A_valve], dtype=np.float32)

    def is_loaded(self) -> bool:
        return self.loaded
