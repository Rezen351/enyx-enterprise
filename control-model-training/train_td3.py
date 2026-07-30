#!/usr/bin/env python3
"""
Train TD3 agent for Aeroponic Simulator.

TD3 (Twin Delayed DDPG) is chosen over PPO because:
- Off-policy: replay buffer enables data reuse in deterministic environment
- Twin critics: min(Q1,Q2) reduces overestimation bias
- Delayed policy + target updates: decouples actor/critic updates
- Target policy smoothing: smooths learning target
- Deterministic policy + action noise: more suitable for valve threshold control
"""

import os
import sys

sys.path.insert(0, '/home/almuzky/TA/Microservices/control-model-training')

import math
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import TD3
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize
from stable_baselines3.common.noise import NormalActionNoise
from stable_baselines3.common.callbacks import BaseCallback

from aeroponic_simulator import AeroponicSimulatorEnv


class AeroponicGymnasiumEnv(gym.Env):
    """
    Gymnasium wrapper for AeroponicSimulatorEnv.
    Observation: 10D continuous
    Action: 3D continuous [-1, 1] normalized, mapped to physical ranges:
      - D_mist: [120, 600] seconds (2-10 minutes ON)
      - interval_sec: [120, 600] seconds (2-10 minutes OFF)
      - A_valve: [0, 1] (threshold at 0.0 for TD3 deterministic policy)
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
        a_01 = (action + 1.0) / 2.0
        D_mist = self.D_mist_min + a_01[0] * (self.D_mist_max - self.D_mist_min)
        interval = self.interval_min + a_01[1] * (self.interval_max - self.interval_min)
        A_valve = 1.0 if action[2] >= 0.0 else 0.0
        return [D_mist, interval, A_valve]

    def reset(self, seed=None, options=None, L_root=None, continuous=False, mode='training', episode_duration=None, max_steps=None):
        super().reset(seed=seed)
        state = self.sim.reset(L_root=L_root, continuous=continuous, mode=mode, episode_duration=episode_duration, max_steps=max_steps)
        return np.array(state, dtype=np.float32), {}

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)
        physical_action = self._map_action(action)
        state, reward, terminated, truncated, info = self.sim.step(physical_action)
        return np.array(state, dtype=np.float32), float(reward), terminated, truncated, info

    def set_curriculum_weather_scale(self, scale):
        self.sim.curriculum_weather_scale = float(scale)

    def render(self):
        pass


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
        if hasattr(self.model, 'replay_buffer') and self.model.replay_buffer is not None:
            buf = self.model.replay_buffer
            if buf is not None and hasattr(buf, 'rewards'):
                rewards = buf.rewards
                if len(rewards) > 0:
                    batch_mean = float(np.mean(rewards))
                    batch_std = float(np.std(rewards)) + 1e-8

                    self.count += len(rewards)
                    self.reward_mean = self.alpha * self.reward_mean + (1 - self.alpha) * batch_mean
                    self.reward_std = self.alpha * self.reward_std + (1 - self.alpha) * batch_std

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
            "reward_growth_proxy",
            "reward_resource",
            "reward_state",
            "reward_env",
            "reward_hypoxia",
            "reward_efficiency",
            "reward_shrink",
            "reward_death",
            "reward_extreme",
            "reward_joint_tin_o2",
            "episode_phase",
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
                
                # Track episode-level metrics
                elapsed_time = info.get("elapsed_time_seconds", 0.0)
                cycle_count = info.get("cycle_count", 0)
                self.model.logger.record("rollout/episode_duration_seconds", elapsed_time)
                self.model.logger.record("rollout/cycle_count_mean", float(cycle_count))
                
                self._current_episode = {}

        return True

    def _on_rollout_end(self):
        if not self.episode_rewards:
            return True

        keys = [
            "reward_growth",
            "reward_growth_proxy",
            "reward_resource",
            "reward_state",
            "reward_env",
            "reward_hypoxia",
            "reward_efficiency",
            "reward_shrink",
            "reward_death",
            "reward_extreme",
            "reward_joint_tin_o2",
            "episode_phase",
        ]

        recent = self.episode_rewards[-self.window_size:]
        for key in keys:
            values = [ep[key] for ep in recent]
            mean_value = float(np.mean(values))
            self.model.logger.record(f"rollout/{key}", mean_value)

        if len(self.episode_rewards) > self.window_size:
            self.episode_rewards = self.episode_rewards[-self.window_size:]

        return True


class CurriculumWeatherScaleCallback(BaseCallback):
    """
    Gradually increase curriculum_weather_scale from start_scale to end_scale
    over total_timesteps using quadratic schedule for slow start and gradual increase.
    Logs the scale to TensorBoard for monitoring.
    """
    def __init__(self, start_scale=0.0, end_scale=0.8, total_timesteps=2_000_000):
        super().__init__()
        self.start_scale = start_scale
        self.end_scale = end_scale
        self.total_timesteps = total_timesteps

    def _on_step(self):
        progress = min(1.0, self.num_timesteps / self.total_timesteps)
        scale = self.start_scale + (self.end_scale - self.start_scale) * (progress ** 2)

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


def train_td3():
    """
    Train TD3 agent with optimized hyperparameters for aeroponic control.

    Key design choices:
    - Off-policy replay buffer for data reuse in deterministic environment
    - Twin critics with min(Q1,Q2) to reduce overestimation
    - Delayed policy updates (policy_delay=2) for stability
    - Target policy smoothing for smooth learning targets
    - Action noise for exploration (Gaussian, per-dimension sigma)
    - VecNormalize for observation and reward normalization
    - Curriculum weather scaling for gradual domain randomization
    """
    base_dir = '/home/almuzky/TA/Microservices/control-model-training'
    models_dir = os.path.join(base_dir, 'models')
    tensorboard_dir = os.path.join(base_dir, 'aeroponic_td3_tensorboard')
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(tensorboard_dir, exist_ok=True)

    vec_env = make_vec_env(AeroponicGymnasiumEnv, n_envs=1)
    vec_norm = VecNormalize(vec_env, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)

    total_timesteps = 3_500_000
    lr_schedule = lambda progress_remaining: 1e-4 * progress_remaining

    n_actions = vec_env.action_space.shape[-1]
    action_noise = NormalActionNoise(
        mean=np.zeros(n_actions),
        sigma=np.array([0.1, 0.18, 0.2]),
    )

    value_norm_callback = ValueNormalizationCallback()
    reward_log_callback = RewardLoggingCallback()
    curriculum_callback = CurriculumWeatherScaleCallback(
        start_scale=0.0,
        end_scale=1.0,
        total_timesteps=total_timesteps,
    )

    model_path = os.path.join(models_dir, 'aeroponic_td3.zip')
    if os.path.exists(model_path):
        model = TD3.load(model_path, env=vec_norm)
        model.tensorboard_log = tensorboard_dir
        print(f"Resumed existing model from {model_path} ({model.num_timesteps} timesteps)")
        model.action_noise = NormalActionNoise(
            mean=np.zeros(n_actions),
            sigma=np.array([0.1, 0.18, 0.2]),
        )
        model.target_noise_clip = 0.3
        print(f"Updated hyperparameters: action_noise sigma=[0.1, 0.18, 0.2], target_noise_clip=0.3")
    else:
        model = TD3(
            policy='MlpPolicy',
            env=vec_norm,
            learning_rate=lr_schedule,
            buffer_size=2_000_000,
            learning_starts=100_000,
            batch_size=256,
            tau=0.005,
            gamma=0.995,
            train_freq=(1, 'step'),
            gradient_steps=1,
            action_noise=action_noise,
            policy_delay=2,
            target_policy_noise=0.2,
            target_noise_clip=0.3,
            stats_window_size=100,
            verbose=1,
            tensorboard_log=tensorboard_dir,
            device='cpu',
        )

    print("=" * 80)
    print("STARTING TD3 TRAINING")
    print("=" * 80)
    print(f"Hyperparameters:")
    print(f"  Total timesteps: {total_timesteps:,}")
    print(f"  Learning rate: 1e-4 (linear schedule)")
    print(f"  Buffer size: 2,000,000")
    print(f"  Learning starts: 100,000")
    print(f"  Batch size: 256")
    print(f"  Tau: 0.005")
    print(f"  Gamma: 0.995")
    print(f"  Policy delay: 2")
    print(f"  Target policy noise: 0.2")
    print(f"  Target noise clip: 0.3")
    print(f"  Action noise sigma: [0.1, 0.18, 0.2]")
    print(f"  Valve threshold: 0.0 (action[2] >= 0.0 -> ON)")
    print(f"  device: cpu")
    print(f"  tensorboard_log: {tensorboard_dir}")
    print(f"  model save path: {model_path}")
    print("=" * 80)

    callback = [value_norm_callback, reward_log_callback, curriculum_callback]
    remaining_timesteps = max(0, total_timesteps - model.num_timesteps)
    if remaining_timesteps <= 0:
        print(f"Model already has {model.num_timesteps} timesteps, target is {total_timesteps}. No additional training needed.")
    else:
        print(f"Training for {remaining_timesteps:,} additional timesteps to reach {total_timesteps:,}")
        model.learn(total_timesteps=remaining_timesteps, callback=callback)

    model_path = os.path.join(models_dir, 'aeroponic_td3.zip')
    model.save(model_path)
    print(f"\nModel saved to: {model_path}")

    vec_norm_path = os.path.join(models_dir, 'vec_normalize_td3.pkl')
    vec_norm.save(vec_norm_path)
    print(f"VecNormalize stats saved to: {vec_norm_path}")

    print("\n" + "=" * 80)
    print("TRAINING COMPLETE")
    print("=" * 80)

    return model


if __name__ == "__main__":
    train_td3()
