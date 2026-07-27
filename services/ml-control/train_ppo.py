#!/usr/bin/env python3
"""
Train PPO agent for Aeroponic Simulator
Configuration follows notebook.md section 4.5.6
"""

import os
import sys

# Add ml-control to path
sys.path.insert(0, '/home/almuzky/TA/Microservices/services/ml-control')

import math
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3.common.callbacks import BaseCallback

from aeroponic_simulator import AeroponicSimulatorEnv


class AeroponicGymnasiumEnv(gym.Env):
    """
    Gymnasium wrapper for AeroponicSimulatorEnv.
    Observation: 11D continuous
    Action: 3D continuous [D_mist, interval_sec, A_valve]
    """

    def __init__(self):
        super().__init__()
        self.sim = AeroponicSimulatorEnv()

        # Observation space: 10D
        # [L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]
        # T_root is internal only (no sensor in real hardware), used for dynamics/reward
        low_obs = np.array([0.0, 0.0, 15.0, 20.0, 15.0, 20.0, 0.5, 4.0, 18.0, 0.0], dtype=np.float32)
        high_obs = np.array([300.0, 1.0, 30.0, 100.0, 30.0, 100.0, 3.5, 9.0, 25.0, 1.0], dtype=np.float32)
        self.observation_space = spaces.Box(low=low_obs, high=high_obs, dtype=np.float32)

        # Action space: 3D continuous [D_mist, interval_sec, A_valve]
        # D_mist: [120, 240] seconds (2-4 minutes ON)
        # interval_sec: [360, 540] seconds (6-9 minutes OFF)
        # A_valve: [0, 1]
        self.action_space = spaces.Box(
            low=np.array([120.0, 360.0, 0.0], dtype=np.float32),
            high=np.array([240.0, 540.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        state = self.sim.reset()
        return np.array(state, dtype=np.float32), {}

    def step(self, action):
        # Clip action to valid range
        action = np.clip(action, self.action_space.low, self.action_space.high)
        state, reward, terminated, truncated, info = self.sim.step(action.tolist())
        return np.array(state, dtype=np.float32), float(reward), terminated, truncated, info

    def set_curriculum_weather_scale(self, scale):
        self.sim.curriculum_weather_scale = float(scale)

    def render(self):
        pass

class EntropyCurriculumCallback(BaseCallback):
    """
    Decay entropy coefficient and ramp weather difficulty over training.
    """
    def __init__(self, ent_start=0.2, ent_end=0.02, weather_start=0.5, weather_end=2.0, total_steps=500000):
        super().__init__()
        self.ent_start = ent_start
        self.ent_end = ent_end
        self.weather_start = weather_start
        self.weather_end = weather_end
        self.total_steps = total_steps

    def _on_step(self):
        progress = min(1.0, self.num_timesteps / self.total_steps)
        ent_coef = self.ent_start + (self.ent_end - self.ent_start) * progress
        weather_scale = self.weather_start + (self.weather_end - self.weather_start) * progress
        self.model.ent_coef = ent_coef
        # Access the underlying env to set curriculum scale
        env = self.training_env
        # For VecEnv wrapping
        base_env = env.envs[0] if hasattr(env, "envs") else env
        if hasattr(base_env, "set_curriculum_weather_scale"):
            base_env.set_curriculum_weather_scale(weather_scale)
        return True



def train_ppo():
    """
    Train PPO agent with stabilized hyperparameters and reward normalization.
    """
    base_dir = '/home/almuzky/TA/Microservices/services/ml-control'
    models_dir = os.path.join(base_dir, 'models')
    tensorboard_dir = os.path.join(base_dir, 'aeroponic_ppo_tensorboard')
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(tensorboard_dir, exist_ok=True)

    # Vectorized env for stabilization and reward normalization
    vec_env = make_vec_env(AeroponicGymnasiumEnv, n_envs=1)
    vec_norm = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.0)

    model = PPO(
        policy='MlpPolicy',
        env=vec_norm,
        learning_rate=3e-4,
        n_steps=8192,
        batch_size=64,
        n_epochs=10,
        gamma=0.999,
        ent_coef=0.2,
        vf_coef=0.1,
        max_grad_norm=0.5,
        clip_range=0.2,
        verbose=1,
        tensorboard_log=tensorboard_dir,
        device='cpu',
    )

    print("=" * 80)
    print("STARTING PPO TRAINING")
    print("=" * 80)
    print(f"Total timesteps: 500,000")
    print(f"Learning rate: 3e-4")
    print(f"n_steps: 8192")
    print(f"batch_size: 64")
    print(f"n_epochs: 10")
    print(f"gamma: 0.999")
    print(f"ent_coef: 0.2 -> 0.02 schedule")
    print(f"vf_coef: 0.1")
    print(f"max_grad_norm: 0.5")
    print(f"curriculum: weather 0.5 -> 2.0")
    print(f"device: cpu")
    print(f"tensorboard_log: {tensorboard_dir}")
    print(f"model save path: {os.path.join(models_dir, 'aeroponic_ppo.zip')}")
    print("=" * 80)

    callback = EntropyCurriculumCallback(total_steps=500000)
    model.learn(total_timesteps=500000, callback=callback)

    model_path = os.path.join(models_dir, 'aeroponic_ppo.zip')
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")

    vec_norm_path = os.path.join(models_dir, 'vec_normalize.pkl')
    vec_norm.save(vec_norm_path)
    print(f"VecNormalize stats saved to: {vec_norm_path}")

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)

    return model


if __name__ == "__main__":
    train_ppo()
