#!/usr/bin/env python3
"""
Evaluate trained PPO model on Aeroponic Simulator and plot results.
"""

import os
import sys
import math
import random

sys.path.insert(0, '/home/almuzky/TA/Microservices/services/ml-control')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from aeroponic_simulator import AeroponicSimulatorEnv
from train_ppo import AeroponicGymnasiumEnv


def load_model_and_env():
    base_dir = '/home/almuzky/TA/Microservices/services/ml-control'
    model_path = os.path.join(base_dir, 'models', 'aeroponic_ppo.zip')
    vec_norm_path = os.path.join(base_dir, 'models', 'vec_normalize.pkl')

    env = AeroponicGymnasiumEnv()
    vec_env = DummyVecEnv([lambda: env])
    vec_norm = VecNormalize.load(vec_norm_path, vec_env)
    vec_norm.training = False
    vec_norm.norm_reward = False

    model = PPO.load(model_path, env=vec_norm)
    return model, vec_norm


def evaluate_policy(model, vec_env, num_episodes=5):
    """
    Evaluate trained policy and collect metrics.
    """
    all_histories = []

    for ep in range(num_episodes):
        base_env = vec_env.envs[0]
        raw = base_env
        while hasattr(raw, 'env'):
            raw = raw.env
        sim = raw.sim
        sim.curriculum_weather_scale = 1.0

        obs = vec_env.reset()
        terminated = False
        truncated = False
        steps = 0

        history = {
            'cycle': [],
            'time_s': [],
            'time_h': [],
            'L_root': [],
            'H_in': [],
            'T_in': [],
            'T_out': [],
            'H_out': [],
            'EC': [],
            'pH': [],
            'T_nut': [],
            'O2_status': [],
            'total_reward': [],
            'D_mist': [],
            'interval_sec': [],
            'A_valve': [],
            'captured': [],
        }
        L_root_init = sim.state[0]

        while not terminated and not truncated:
            action, _ = model.predict(obs, deterministic=False)
            action = np.asarray(action).flatten()
            action = np.clip(action, vec_env.action_space.low, vec_env.action_space.high)

            pre_L_root = sim.state[0]
            pre_time = sim.current_time
            pre_T_in = sim.state[2]
            pre_H_in = sim.state[3]
            pre_EC = sim.state[6]
            pre_pH = sim.state[7]
            pre_T_nut = sim.state[8]

            obs, reward, done, info = vec_env.step(action)
            terminated = bool(np.any(done)) if isinstance(done, np.ndarray) else bool(done)
            sim = raw.sim

            if terminated:
                log_L = pre_L_root
                log_time = pre_time
                log_T_in = pre_T_in
                log_H_in = pre_H_in
                log_EC = pre_EC
                log_pH = pre_pH
                log_T_nut = pre_T_nut
                info0 = info[0] if isinstance(info, (list, tuple)) else info
                log_O2 = info0.get('O2_status', 0.0)
                log_T_out = info0.get('T_out', sim.state[4])
                log_H_out = info0.get('H_out', sim.state[5])
            else:
                log_L = sim.state[0]
                log_time = sim.current_time
                log_T_in = sim.state[2]
                log_H_in = sim.state[3]
                log_EC = sim.state[6]
                log_pH = sim.state[7]
                log_T_nut = sim.state[8]
                info0 = info[0] if isinstance(info, (list, tuple)) else info
                log_O2 = info0.get('O2_status', 0.0)
                log_T_out = info0.get('T_out', sim.state[4])
                log_H_out = info0.get('H_out', sim.state[5])

            history['cycle'].append(steps)
            history['time_s'].append(log_time)
            history['time_h'].append(log_time / 3600.0)
            history['L_root'].append(log_L)
            history['H_in'].append(log_H_in)
            history['T_in'].append(log_T_in)
            history['T_out'].append(log_T_out)
            history['H_out'].append(log_H_out)
            history['EC'].append(log_EC)
            history['pH'].append(log_pH)
            history['T_nut'].append(log_T_nut)
            history['O2_status'].append(log_O2)
            history['total_reward'].append(float(reward[0]) if isinstance(reward, np.ndarray) else float(reward))
            history['D_mist'].append(action[0])
            history['interval_sec'].append(action[1])
            history['A_valve'].append(action[2])
            history['captured'].append(sim._captured_this_step)

            steps += 1

        all_histories.append(history)
        L_final = history['L_root'][-1]
        L_growth = L_final - L_root_init
        print(f"Episode {ep+1}: {steps} cycles, captures={sum(history['captured'])}, "
              f"final L_root={L_final:.4f}, growth={L_growth:.4f} cm, time={history['time_s'][-1]:.0f}s")

    return all_histories


def plot_action_histograms(histories, out_path):
    """
    Plot histograms of actions taken by the PPO agent.
    """
    import os

    # Collect all actions across episodes
    all_D_mist = []
    all_interval = []
    all_A_valve = []

    for hist in histories:
        all_D_mist.extend(hist['D_mist'])
        all_interval.extend(hist['interval_sec'])
        all_A_valve.extend(hist['A_valve'])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # D_mist histogram
    ax1 = axes[0]
    ax1.hist(all_D_mist, bins=30, color='tab:blue', alpha=0.7, edgecolor='black')
    ax1.set_xlabel('D_mist (s)')
    ax1.set_ylabel('Count')
    ax1.set_title('Misting Duration Distribution')
    ax1.axvline(x=120, color='tab:green', linestyle='--', linewidth=2, label='Min (120s)')
    ax1.axvline(x=240, color='tab:red', linestyle='--', linewidth=2, label='Max (240s)')
    ax1.axvline(x=np.mean(all_D_mist), color='tab:orange', linestyle='--', linewidth=2, label=f'Mean: {np.mean(all_D_mist):.2f}s')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Interval histogram
    ax2 = axes[1]
    ax2.hist(all_interval, bins=30, color='tab:green', alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Interval (s)')
    ax2.set_ylabel('Count')
    ax2.set_title('Misting Interval Distribution')
    ax2.axvline(x=360, color='tab:green', linestyle='--', linewidth=2, label='Min (360s)')
    ax2.axvline(x=540, color='tab:red', linestyle='--', linewidth=2, label='Max (540s)')
    ax2.axvline(x=np.mean(all_interval), color='tab:orange', linestyle='--', linewidth=2, label=f'Mean: {np.mean(all_interval):.0f}s')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # A_valve histogram
    ax3 = axes[2]
    ax3.hist(all_A_valve, bins=20, color='tab:red', alpha=0.7, edgecolor='black')
    ax3.set_xlabel('A_valve')
    ax3.set_ylabel('Count')
    ax3.set_title('Bottom Valve Actuation Distribution')
    ax3.axvline(x=0.5, color='tab:red', linestyle='--', linewidth=2, label='Threshold (0.5)')
    ax3.axvline(x=np.mean(all_A_valve), color='tab:orange', linestyle='--', linewidth=2, label=f'Mean: {np.mean(all_A_valve):.3f}')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(out_path, 'ppo_action_histograms.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved action histograms: {out_path}")
    plt.close()

    # Print statistics
    print("\n" + "=" * 80)
    print("ACTION DISTRIBUTION STATISTICS")
    print("=" * 80)
    print(f"\nD_mist (misting duration):")
    print(f"  Mean: {np.mean(all_D_mist):.2f}s")
    print(f"  Std: {np.std(all_D_mist):.2f}s")
    print(f"  Min: {min(all_D_mist):.2f}s")
    print(f"  Max: {max(all_D_mist):.2f}s")
    print(f"  Median: {np.median(all_D_mist):.2f}s")

    print(f"\nInterval (misting interval):")
    print(f"  Mean: {np.mean(all_interval):.0f}s ({np.mean(all_interval)/60:.1f} min)")
    print(f"  Std: {np.std(all_interval):.0f}s")
    print(f"  Min: {min(all_interval):.0f}s")
    print(f"  Max: {max(all_interval):.0f}s")
    print(f"  Median: {np.median(all_interval):.0f}s")

    print(f"\nA_valve (bottom valve):")
    print(f"  Mean: {np.mean(all_A_valve):.3f}")
    print(f"  Std: {np.std(all_A_valve):.3f}")
    print(f"  Min: {min(all_A_valve):.3f}")
    print(f"  Max: {max(all_A_valve):.3f}")
    print(f"  Valve usage rate: {sum(1 for v in all_A_valve if v >= 0.5) / len(all_A_valve) * 100:.1f}%")
    print("=" * 80)


def save_episode_summary(histories, out_path):
    """
    Save episode metrics summary to CSV.
    """
    import os
    import csv

    out_path = os.path.join(out_path, 'episode_summary.csv')
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['episode', 'cycles', 'captures', 'final_L_root', 'final_time_s', 'final_time_h'])
        for i, hist in enumerate(histories):
            writer.writerow([
                i + 1,
                len(hist['cycle']),
                sum(hist['captured']),
                hist['L_root'][-1],
                hist['time_s'][-1],
                hist['time_h'][-1],
            ])
    print(f"Saved episode summary: {out_path}")


def plot_reward_curve(histories, out_path):
    """
    Plot reward per cycle and cumulative reward.
    """
    import os

    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for i, hist in enumerate(histories):
        cycles = hist['cycle']
        rewards = hist['total_reward']
        cum_rewards = np.cumsum(rewards)
        axes[0].plot(cycles, rewards, label=f'Ep {i+1}', color=colors[i], alpha=0.7)
        axes[1].plot(cycles, cum_rewards, label=f'Ep {i+1}', color=colors[i], alpha=0.7)

    axes[0].set_xlabel('Cycle')
    axes[0].set_ylabel('Reward')
    axes[0].set_title('Reward per Cycle')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_xlabel('Cycle')
    axes[1].set_ylabel('Cumulative Reward')
    axes[1].set_title('Cumulative Reward over Episode')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(out_path, 'ppo_reward_curve.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved reward curve: {out_path}")
    plt.close()


def plot_episode_comparison(histories, out_path):
    """
    Plot comparison of multiple episodes.
    """
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']

    fig, axes = plt.subplots(5, 2, figsize=(14, 14))

    # Panel structure (row, col):
    # 0,0 L_root | 0,1 H_in
    # 1,0 H_out  | 1,1 T_in
    # 2,0 T_out  | 2,1 T_nut
    # 3,0 EC     | 3,1 pH
    # 4,0 D_mist | 4,1 Total Reward

    # Row 1
    ax = axes[0, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['L_root'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('L_root (cm)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Root Length')
    ax.legend()
    ax.grid(True)

    ax = axes[0, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['H_in'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('H_in (%)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Internal Humidity')
    ax.legend()
    ax.grid(True)

    # Row 2
    ax = axes[1, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['H_out'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('H_out (%)')
    ax.set_xlabel('Time (h)')
    ax.set_title('External Humidity')
    ax.legend()
    ax.grid(True)

    ax = axes[1, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['T_in'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('T_in (°C)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Internal Temperature')
    ax.legend()
    ax.grid(True)

    # Row 3
    ax = axes[2, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['T_out'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('T_out (°C)')
    ax.set_xlabel('Time (h)')
    ax.set_title('External Temperature')
    ax.legend()
    ax.grid(True)

    ax = axes[2, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['T_nut'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('T_nut (°C)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Nutrient Temperature')
    ax.legend()
    ax.grid(True)

    # Row 4
    ax = axes[3, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['EC'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('EC (mS/cm)')
    ax.set_xlabel('Time (h)')
    ax.set_title('EC')
    ax.legend()
    ax.grid(True)

    ax = axes[3, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['pH'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('pH')
    ax.set_xlabel('Time (h)')
    ax.set_title('pH')
    ax.legend()
    ax.grid(True)

    # Row 5
    ax = axes[4, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['D_mist'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('D_mist (s)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Misting Duration')
    ax.legend()
    ax.grid(True)

    ax = axes[4, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['total_reward'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    ax.set_ylabel('Reward')
    ax.set_xlabel('Time (h)')
    ax.set_title('Total Reward per Step')
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    out_path = os.path.join(out_path, 'ppo_episode_comparison.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved episode comparison: {out_path}")
    plt.close()


def print_summary(histories):
    print("\n" + "=" * 80)
    print("PPO EVALUATION SUMMARY")
    print("=" * 80)

    for i, hist in enumerate(histories):
        captures = sum(hist['captured'])
        total_reward = sum(hist['total_reward'])
        L_final = hist['L_root'][-1]
        L_growth = L_final - 8.0

        avg_D_mist = np.mean(hist['D_mist'])
        avg_interval = np.mean(hist['interval_sec'])
        avg_valve = np.mean(hist['A_valve'])

        print(f"\nEpisode {i+1}:")
        print(f"  Cycles: {len(hist['cycle'])}")
        print(f"  Captures: {captures}")
        print(f"  L_root growth: {L_growth:.4f} cm (final: {L_final:.4f} cm)")
        print(f"  Total reward: {total_reward:.2f}")
        print(f"  Avg D_mist: {avg_D_mist:.2f}s")
        print(f"  Avg interval: {avg_interval:.0f}s")
        print(f"  Avg A_valve: {avg_valve:.3f}")
        print(f"  Valve usage: {sum(1 for v in hist['A_valve'] if v >= 0.5)} cycles")


def run_evaluation():
    base_dir = '/home/almuzky/TA/Microservices/services/ml-control'
    results_dir = os.path.join(base_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 80)
    print("PPO MODEL EVALUATION")
    print("=" * 80)

    model, vec_env = load_model_and_env()
    histories = evaluate_policy(model, vec_env, num_episodes=5)
    plot_episode_comparison(histories, results_dir)
    plot_action_histograms(histories, results_dir)
    plot_reward_curve(histories, results_dir)
    print_summary(histories)

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
