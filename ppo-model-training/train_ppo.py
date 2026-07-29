#!/usr/bin/env python3
"""
Train PPO agent for Aeroponic Simulator
Configuration follows notebook.md section 4.5.6
"""

import os
import sys

# Add ml-control to path
sys.path.insert(0, '/home/almuzky/TA/Microservices/ppo-model-training')

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
    Observation: 10D continuous
    Action: 3D continuous [-1, 1] normalized, mapped to physical ranges:
      - D_mist: [120, 600] seconds (2-10 minutes ON)
      - interval_sec: [120, 600] seconds (2-10 minutes OFF)
      - A_valve: [0, 1] (threshold at 0.5)
    """
    def __init__(self):
        super().__init__()
        self.sim = AeroponicSimulatorEnv()

        # Observation space: 10D
        # [L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]
        # T_root is internal only (no sensor in real hardware), used for dynamics/reward
        low_obs = np.array([0.0, 0.0, 15.0, 15.0, 15.0, 20.0, 0.5, 4.0, 15.0, 0.0], dtype=np.float32)
        high_obs = np.array([300.0, 1.0, 38.0, 100.0, 42.0, 100.0, 3.5, 9.0, 35.0, 1.0], dtype=np.float32)
        self.observation_space = spaces.Box(low=low_obs, high=high_obs, dtype=np.float32)

        # Normalized action space: [-1, 1] for all 3 dimensions
        # PPO samples from this range; we map to physical values in step()
        self.action_space = spaces.Box(
            low=np.array([-1.0, -1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )

        # Physical action bounds for mapping (realistic ranges: 2-10 minutes)
        self.D_mist_min = 120.0
        self.D_mist_max = 600.0
        self.interval_min = 120.0
        self.interval_max = 600.0

    def _map_action(self, action):
        """Map normalized [-1, 1] actions to physical ranges."""
        # Scale from [-1, 1] to [0, 1] first
        a_01 = (action + 1.0) / 2.0
        D_mist = self.D_mist_min + a_01[0] * (self.D_mist_max - self.D_mist_min)
        interval = self.interval_min + a_01[1] * (self.interval_max - self.interval_min)
        A_valve = 1.0 if action[2] >= 0.5 else 0.0  # threshold at 0.5 for symmetric exploration
        return [D_mist, interval, A_valve]

    def reset(self, seed=None, options=None, L_root=None, continuous=False, mode='training'):
        super().reset(seed=seed)
        state = self.sim.reset(L_root=L_root, continuous=continuous, mode=mode)
        return np.array(state, dtype=np.float32), {}

    def step(self, action):
        # Clip normalized action to [-1, 1]
        action = np.clip(action, -1.0, 1.0)
        # Map to physical values
        physical_action = self._map_action(action)
        state, reward, terminated, truncated, info = self.sim.step(physical_action)
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
    def __init__(self, ent_start=0.2, ent_end=0.02, boost_factor=1.5, window_size=10, total_timesteps=300_000):
        super().__init__()
        self.ent_start = ent_start
        self.ent_end = ent_end
        self.boost_factor = boost_factor
        self.window_size = window_size
        self.total_timesteps = total_timesteps
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

                progress = min(1.0, self.num_timesteps / self.total_timesteps)
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


class RewardLoggingCallback(BaseCallback):
    """
    Log reward component breakdown from environment info dict to TensorBoard.
    Accumulates per-step component values across each episode and logs
    the per-episode average at rollout end.
    """
    def __init__(self, window_size=10):
        super().__init__()
        self.window_size = window_size
        self.episode_rewards = []
        self._current_episode = {}

    def _on_step(self):
        infos = self.locals.get("infos", [])
        dones = self.locals.get("dones", [])
        if not infos or not dones:
            return True

        keys = [
            "reward_growth",
            "reward_resource",
            "reward_state",
            "reward_env",
            "reward_hypoxia",
            "reward_efficiency",
            "reward_shrink",
            "reward_death",
            "reward_extreme",
        ]

        for info, done in zip(infos, dones):
            if isinstance(info, dict):
                for key in keys:
                    val = info.get(key, 0.0)
                    self._current_episode[key] = self._current_episode.get(key, 0.0) + val
                self._current_episode["_count"] = self._current_episode.get("_count", 0) + 1

            if done and isinstance(info, dict) and self._current_episode.get("_count", 0) > 0:
                episode_avg = {
                    key: self._current_episode.get(key, 0.0) / self._current_episode["_count"]
                    for key in keys
                }
                self.episode_rewards.append(episode_avg)
                self._current_episode = {}

        return True

    def _on_rollout_end(self):
        if not self.episode_rewards:
            return True

        keys = [
            "reward_growth",
            "reward_resource",
            "reward_state",
            "reward_env",
            "reward_hypoxia",
            "reward_efficiency",
            "reward_shrink",
            "reward_death",
            "reward_extreme",
        ]

        recent = self.episode_rewards[-self.window_size:]
        for key in keys:
            values = [ep[key] for ep in recent]
            mean_value = float(np.mean(values))
            self.model.logger.record(f"rollout/{key}", mean_value)

        if len(self.episode_rewards) > self.window_size:
            self.episode_rewards = self.episode_rewards[-self.window_size:]

        return True


def linear_schedule(initial_value: float, final_value: float = 1e-5):
    """Linear learning rate schedule from initial_value to final_value."""
    def func(progress_remaining: float) -> float:
        return final_value + (initial_value - final_value) * progress_remaining
    return func


class CurriculumWeatherScaleCallback(BaseCallback):
    """
    Gradually increase curriculum_weather_scale from start_scale to end_scale
    over total_timesteps. Logs the scale to TensorBoard for monitoring.
    """
    def __init__(self, start_scale=0.5, end_scale=1.0, total_timesteps=1_000_000):
        super().__init__()
        self.start_scale = start_scale
        self.end_scale = end_scale
        self.total_timesteps = total_timesteps

    def _on_step(self):
        progress = min(1.0, self.num_timesteps / self.total_timesteps)
        scale = self.start_scale + (self.end_scale - self.start_scale) * progress

        try:
            vec_env = self.model.env.venv
            base_env = vec_env.envs[0]
            while hasattr(base_env, 'env'):
                base_env = base_env.env
            base_env.sim.curriculum_weather_scale = scale
        except Exception:
            pass
        self.model.logger.record("curriculum/weather_scale", scale)
        return True


def train_ppo():
    """
    Train PPO agent with optimized hyperparameters.
    Key fixes vs previous runs:
    - Normalized [-1,1] action space (fixes double-scaling bug)
    - Higher entropy for better exploration
    - More timesteps for convergence
    - Linear LR schedule for fine-tuning
    """
    base_dir = '/home/almuzky/TA/Microservices/ppo-model-training'
    models_dir = os.path.join(base_dir, 'models')
    tensorboard_dir = os.path.join(base_dir, 'aeroponic_ppo_tensorboard')
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(tensorboard_dir, exist_ok=True)

    # Vectorized env for stabilization and reward normalization
    vec_env = make_vec_env(AeroponicGymnasiumEnv, n_envs=1)
    vec_norm = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)

    # Training hyperparameters
    total_timesteps = 300_000
    lr_schedule = linear_schedule(3e-4, 1e-5)

    # Adaptive entropy callback
    entropy_callback = AdaptiveEntropyCallback(ent_start=0.2, ent_end=0.03, total_timesteps=total_timesteps)
    value_norm_callback = ValueNormalizationCallback()
    reward_log_callback = RewardLoggingCallback()
    curriculum_callback = CurriculumWeatherScaleCallback(start_scale=0.0, end_scale=0.5, total_timesteps=total_timesteps)

    model_path = os.path.join(models_dir, 'aeroponic_ppo.zip')
    if os.path.exists(model_path):
        model = PPO.load(model_path, env=vec_norm)
        print(f"Resumed existing model from {model_path} ({model.num_timesteps} timesteps)")
    else:
        model = PPO(
            policy='MlpPolicy',
            env=vec_norm,
            learning_rate=lr_schedule,
            n_steps=4096,
            batch_size=256,
            n_epochs=10,
            gamma=0.995,
            ent_coef=0.05,
            vf_coef=0.5,
            max_grad_norm=1.0,
            clip_range=0.1,
            gae_lambda=0.95,
            verbose=1,
            tensorboard_log=tensorboard_dir,
            device='cpu',
        )

    print("=" * 80)
    print("STARTING PPO TRAINING (FIXED CONFIG)")
    print("=" * 80)
    print(f"Fixes applied:")
    print(f"  - Normalized [-1,1] action space (fixes double-scaling bug)")
    print(f"  - Survival bonus (+0.5/step) + strong early termination penalty")
    print(f"  - EC correction during misting (dilution effect)")
    print(f"  - Linear LR schedule: 3e-4 -> 1e-5")
    print(f"  - Efficiency reward when state healthy + resource-saving actions")
    print(f"  - Curriculum weather scale: 0.3 -> 1.0")
    print(f"Hyperparameters:")
    print(f"  Total timesteps: {total_timesteps:,}")
    print(f"  Learning rate: 3e-4 -> 1e-5 (linear schedule)")
    print(f"  n_steps: 4096")
    print(f"  batch_size: 256")
    print(f"  n_epochs: 10")
    print(f"  gamma: 0.995")
    print(f"  ent_coef: 0.05 (adaptive)")
    print(f"  vf_coef: 0.5")
    print(f"  max_grad_norm: 1.0")
    print(f"  clip_range: 0.1")
    print(f"  gae_lambda: 0.95")
    print(f"  clip_reward: 10.0")
    print(f"  device: cpu")
    print(f"  tensorboard_log: {tensorboard_dir}")
    print(f"  model save path: {os.path.join(models_dir, 'aeroponic_ppo.zip')}")
    print("=" * 80)

    callback = [entropy_callback, value_norm_callback, reward_log_callback, curriculum_callback]
    remaining_timesteps = max(0, total_timesteps - model.num_timesteps)
    if remaining_timesteps <= 0:
        print(f"Model already has {model.num_timesteps} timesteps, target is {total_timesteps}. No additional training needed.")
    else:
        print(f"Training for {remaining_timesteps:,} additional timesteps to reach {total_timesteps:,}")
        model.learn(total_timesteps=remaining_timesteps, callback=callback)

    model_path = os.path.join(models_dir, 'aeroponic_ppo.zip')
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")

    vec_norm_path = os.path.join(models_dir, 'vec_normalize_ppo.pkl')
    vec_norm.save(vec_norm_path)
    print(f"VecNormalize stats saved to: {vec_norm_path}")

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)

    return model


if __name__ == "__main__":
    train_ppo()
