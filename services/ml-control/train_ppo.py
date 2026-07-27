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

class AdaptiveEntropyCallback(BaseCallback):
    """
    Adaptive entropy coefficient:
    - Starts high for exploration
    - Decays linearly to a minimum
    - Boosts temporarily when policy entropy drops too low
    """
    def __init__(self, ent_start=0.2, ent_end=0.02, boost_factor=1.5, window_size=10):
        super().__init__()
        self.ent_start = ent_start
        self.ent_end = ent_end
        self.boost_factor = boost_factor
        self.window_size = window_size
        self.entropy_window = []
        self.entropy_min = 0.3
        self.entropy_max = 2.5

    def _on_step(self):
        # No-op: entropy adjustment happens in _on_rollout_end
        return True

    def _on_rollout_end(self):
        # Compute entropy from the rollout buffer's log probs
        if hasattr(self.model, 'rollout_buffer') and self.model.rollout_buffer is not None:
            buf = self.model.rollout_buffer
            if hasattr(buf, 'old_log_prob') and buf.old_log_prob is not None:
                log_probs = buf.old_log_prob
                if hasattr(log_probs, 'mean'):
                    ent_val = float(-log_probs.mean())
                else:
                    ent_val = float(-np.mean(log_probs))
                
                self.entropy_window.append(ent_val)
                if len(self.entropy_window) > self.window_size:
                    self.entropy_window.pop(0)

                avg_ent = sum(self.entropy_window) / len(self.entropy_window)

                progress = min(1.0, self.num_timesteps / 500000)
                base_ent = self.ent_start + (self.ent_end - self.ent_start) * progress

                if avg_ent < self.entropy_min:
                    new_ent = min(base_ent * self.boost_factor, self.entropy_max)
                elif avg_ent > self.entropy_max:
                    new_ent = max(base_ent * 0.7, self.entropy_min)
                else:
                    new_ent = base_ent

                self.model.ent_coef = new_ent
                
                if self.verbose > 0 and self.num_timesteps % 50000 < self.n_steps:
                    print(f"  [EntropyAdaptive] avg_ent={avg_ent:.3f}, ent_coef={new_ent:.4f}")
        return True


class ValueNormalizationCallback(BaseCallback):
    """
    Track running reward statistics and normalize value targets.
    Helps stabilize value function learning when reward scale varies.
    """
    def __init__(self, alpha=0.99):
        super().__init__()
        self.alpha = alpha
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.count = 0

    def _on_step(self):
        # Update running statistics from recent rewards
        if hasattr(self.model, 'rollout_buffer'):
            buf = self.model.rollout_buffer
            if buf is not None and hasattr(buf, 'rewards'):
                rewards = buf.rewards
                if len(rewards) > 0:
                    batch_mean = np.mean(rewards)
                    batch_std = np.std(rewards) + 1e-8
                    
                    # Update running stats
                    self.count += len(rewards)
                    self.reward_mean = self.alpha * self.reward_mean + (1 - self.alpha) * batch_mean
                    self.reward_std = self.alpha * self.reward_std + (1 - self.alpha) * batch_std
                    
                    # Log for monitoring
                    if self.num_timesteps % 10000 == 0:
                        print(f"  [ValueNorm] reward_mean={self.reward_mean:.2f}, reward_std={self.reward_std:.2f}")
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
    vec_norm = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)

    # Adaptive entropy callback
    entropy_callback = AdaptiveEntropyCallback(ent_start=0.2, ent_end=0.02)
    value_norm_callback = ValueNormalizationCallback()

    model = PPO(
        policy='MlpPolicy',
        env=vec_norm,
        learning_rate=5e-4,
        n_steps=4096,
        batch_size=64,
        n_epochs=10,
        gamma=0.995,
        ent_coef=0.2,
        vf_coef=0.5,
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
    print(f"Learning rate: 5e-4")
    print(f"n_steps: 4096")
    print(f"batch_size: 64")
    print(f"n_epochs: 10")
    print(f"gamma: 0.995")
    print(f"ent_coef: 0.2 (adaptive)")
    print(f"vf_coef: 0.5")
    print(f"max_grad_norm: 0.5")
    print(f"clip_reward: 10.0")
    print(f"device: cpu")
    print(f"tensorboard_log: {tensorboard_dir}")
    print(f"model save path: {os.path.join(models_dir, 'aeroponic_ppo.zip')}")
    print("=" * 80)

    callback = [entropy_callback, value_norm_callback]
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
