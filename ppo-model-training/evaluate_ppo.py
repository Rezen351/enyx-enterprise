#!/usr/bin/env python3
"""
Evaluate trained PPO model on Aeroponic Simulator and plot results.
"""

import os
import sys
import math
import random

sys.path.insert(0, '/home/almuzky/TA/Microservices/ppo-model-training')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from aeroponic_simulator import AeroponicSimulatorEnv
from train_ppo import AeroponicGymnasiumEnv


def load_model_and_env():
    base_dir = '/home/almuzky/TA/Microservices/ppo-model-training'
    model_path = os.path.join(base_dir, 'models', 'aeroponic_ppo.zip')
    vec_norm_path = os.path.join(base_dir, 'models', 'vec_normalize_ppo.pkl')

    env = AeroponicGymnasiumEnv()
    vec_env = DummyVecEnv([lambda: env])
    vec_norm = VecNormalize.load(vec_norm_path, vec_env)
    vec_norm.training = False
    vec_norm.norm_reward = False

    model = PPO.load(model_path, env=vec_norm)
    return model, vec_norm


def evaluate_policy(model, vec_env, num_episodes=5, curriculum_weather_scale=1.0, domain_randomization=True, dr_overrides=None):
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
        sim.curriculum_weather_scale = float(curriculum_weather_scale)

        if not domain_randomization:
            sim.sensor_noise_T = 0.0
            sim.sensor_noise_H = 0.0
            sim.sensor_noise_EC = 0.0
            sim.sensor_noise_pH = 0.0
            sim.actuator_noise_D_mist = 0.0
            sim.actuator_noise_spray_delay = 0.0
        elif dr_overrides is not None:
            for key, value in dr_overrides.items():
                if hasattr(sim, key):
                    setattr(sim, key, float(value))

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
            'event_type': [],
            'event_active': [],
            'event_spans': [],
        }
        L_root_init = sim.state[0]

        current_event_type = 'none'
        current_event_start = None

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

            # Map normalized PPO actions to physical values for accurate logging
            a_01 = (action + 1.0) / 2.0
            D_mist_phys = 120.0 + a_01[0] * 480.0
            interval_phys = 120.0 + a_01[1] * 480.0
            A_valve_phys = 1.0 if action[2] >= 0.0 else 0.0

            obs, reward, done, info = vec_env.step(action.reshape(1, -1))
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
            history['D_mist'].append(D_mist_phys)
            history['interval_sec'].append(interval_phys)
            history['A_valve'].append(A_valve_phys)
            history['captured'].append(sim._captured_this_step)

            event_active = False
            event_type = 'none'
            event_checks = [
                ('extreme_heat', 'extreme_heat_intensity'),
                ('extreme_cold', 'extreme_cold_intensity'),
                ('drought', 'drought_intensity'),
                ('storm', 'storm_intensity'),
                ('heat_wave', 'heat_wave_intensity'),
                ('cold_snap', 'cold_snap_intensity'),
                ('rain', 'rain_humidity_boost'),
            ]
            for etype, attr in event_checks:
                if hasattr(sim, attr) and getattr(sim, attr) > 0:
                    if hasattr(sim, 'event_start_time') and hasattr(sim, 'event_end_time'):
                        if sim.event_start_time <= sim.current_time < sim.event_end_time:
                            event_active = True
                            event_type = etype
                            break

            if event_active and event_type != current_event_type:
                current_event_start = log_time / 3600.0
                current_event_type = event_type
            elif not event_active and current_event_type != 'none' and current_event_start is not None:
                history['event_spans'].append((current_event_type, current_event_start, log_time / 3600.0))
                current_event_type = 'none'
                current_event_start = None

            history['event_type'].append(event_type)
            history['event_active'].append(event_active)

            steps += 1

        if current_event_type != 'none' and current_event_start is not None:
            history['event_spans'].append((current_event_type, current_event_start, history['time_h'][-1]))

        all_histories.append(history)
        L_final = history['L_root'][-1]
        L_growth = L_final - L_root_init
        print(f"Episode {ep+1}: {steps} cycles, captures={sum(history['captured'])}, "
              f"final L_root={L_final:.4f}, growth={L_growth:.4f} cm, time={history['time_s'][-1]:.0f}s")

    return all_histories


def evaluate_with_curriculum(model, vec_env, num_episodes=5):
    """
    Evaluate policy across multiple curriculum weather scales.
    Tests: 0.0, 0.3, 0.5, 0.7, 1.0, 1.5
    """
    scales = [0.0, 0.3, 0.5, 0.7, 1.0, 1.5]
    results = {}

    for scale in scales:
        print(f"\n{'='*80}")
        print(f"CURRICULUM EVALUATION - weather_scale={scale}")
        print(f"{'='*80}")

        histories = evaluate_policy(model, vec_env, num_episodes=num_episodes, curriculum_weather_scale=scale)

        growths = [hist['L_root'][-1] - 8.0 for hist in histories]
        rewards = [sum(hist['total_reward']) for hist in histories]
        event_counts = {}
        for hist in histories:
            for etype in hist['event_type']:
                event_counts[etype] = event_counts.get(etype, 0) + 1

        results[scale] = {
            'growths': growths,
            'rewards': rewards,
            'event_counts': event_counts,
            'mean_growth': np.mean(growths),
            'std_growth': np.std(growths),
            'mean_reward': np.mean(rewards),
            'std_reward': np.std(rewards),
        }

        print(f"  Growth: {np.mean(growths):.4f} ± {np.std(growths):.4f} cm")
        print(f"  Reward: {np.mean(rewards):.2f} ± {np.std(rewards):.2f}")
        print(f"  Events: {event_counts}")

    return results


def evaluate_domain_randomization(model, vec_env, num_episodes=5):
    """
    Evaluate policy with different domain randomization levels.
    Tests: no DR, partial DR, full DR
    """
    dr_levels = [
        ('no_dr', {'sensor_noise_T': 0.0, 'sensor_noise_H': 0.0, 'sensor_noise_EC': 0.0, 'sensor_noise_pH': 0.0, 'actuator_noise_D_mist': 0.0, 'actuator_noise_spray_delay': 0.0}),
        ('partial_dr', {'actuator_noise_D_mist': 0.0, 'actuator_noise_spray_delay': 0.0}),
        ('full_dr', None),
    ]

    results = {}

    for name, overrides in dr_levels:
        print(f"\n{'='*80}")
        print(f"DOMAIN RANDOMIZATION EVALUATION - {name}")
        print(f"{'='*80}")

        histories = evaluate_policy(model, vec_env, num_episodes=num_episodes, domain_randomization=True, dr_overrides=overrides)

        growths = [hist['L_root'][-1] - 8.0 for hist in histories]
        rewards = [sum(hist['total_reward']) for hist in histories]

        results[name] = {
            'growths': growths,
            'rewards': rewards,
            'mean_growth': np.mean(growths),
            'std_growth': np.std(growths),
            'mean_reward': np.mean(rewards),
            'std_reward': np.std(rewards),
        }

        print(f"  Growth: {np.mean(growths):.4f} ± {np.std(growths):.4f} cm")
        print(f"  Reward: {np.mean(rewards):.2f} ± {np.std(rewards):.2f}")

    return results


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
    ax3.hist(all_A_valve, bins=[-0.5, 0.5, 1.5], color='tab:red', alpha=0.7, edgecolor='black', rwidth=0.6)
    ax3.set_xlabel('A_valve')
    ax3.set_ylabel('Count')
    ax3.set_title('Bottom Valve Actuation Distribution')
    ax3.set_xticks([0, 1])
    ax3.set_xticklabels(['OFF (0)', 'ON (1)'])
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
        writer.writerow(['episode', 'cycles', 'captures', 'final_L_root', 'final_time_s', 'final_time_h', 'events'])
        for i, hist in enumerate(histories):
            event_counts = {}
            for etype in hist.get('event_type', []):
                event_counts[etype] = event_counts.get(etype, 0) + 1
            writer.writerow([
                i + 1,
                len(hist['cycle']),
                sum(hist['captured']),
                hist['L_root'][-1],
                hist['time_s'][-1],
                hist['time_h'][-1],
                str(event_counts),
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


def plot_events(histories, out_path):
    """
    Plot extreme/normal weather events over episode time.
    """
    import os

    event_colors = {
        'extreme_heat': 'tab:red',
        'extreme_cold': 'tab:blue',
        'drought': 'tab:brown',
        'storm': 'tab:purple',
        'heat_wave': 'tab:orange',
        'cold_snap': 'tab:cyan',
        'rain': 'tab:green',
        'none': 'tab:gray',
    }

    fig, axes = plt.subplots(len(histories), 1, figsize=(14, 4 * len(histories)), squeeze=False)
    axes = axes.flatten()

    for i, hist in enumerate(histories):
        ax = axes[i]
        times_h = np.array(hist['time_h'])
        event_types = hist['event_type']
        event_actives = hist['event_active']
        event_spans = hist.get('event_spans', [])

        for etype, start_h, end_h in event_spans:
            color = event_colors.get(etype, 'tab:gray')
            ax.axvspan(start_h, end_h, color=color, alpha=0.3, linewidth=0)

        for j, (t, etype, active) in enumerate(zip(times_h, event_types, event_actives)):
            color = event_colors.get(etype, 'tab:gray')
            if active:
                ax.plot(t, 0.5, marker='o', color=color, markersize=4)

        ax.set_xlabel('Time (h)')
        ax.set_ylabel('Event')
        ax.set_title(f'Episode {i+1} - Weather Events')
        ax.set_yticks([])
        ax.set_ylim(0, 1)

        legend_elements = [
            plt.Line2D([0], [0], color=event_colors['extreme_heat'], lw=4, label='Extreme Heat'),
            plt.Line2D([0], [0], color=event_colors['extreme_cold'], lw=4, label='Extreme Cold'),
            plt.Line2D([0], [0], color=event_colors['drought'], lw=4, label='Drought'),
            plt.Line2D([0], [0], color=event_colors['storm'], lw=4, label='Storm'),
            plt.Line2D([0], [0], color=event_colors['heat_wave'], lw=4, label='Heat Wave'),
            plt.Line2D([0], [0], color=event_colors['cold_snap'], lw=4, label='Cold Snap'),
            plt.Line2D([0], [0], color=event_colors['rain'], lw=4, label='Rain'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(out_path, 'ppo_events.png')
    plt.savefig(out_path, dpi=150)
    print(f"Saved events plot: {out_path}")
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

        event_counts = {}
        for etype in hist['event_type']:
            event_counts[etype] = event_counts.get(etype, 0) + 1
        print(f"  Events: {event_counts}")


def run_evaluation():
    base_dir = '/home/almuzky/TA/Microservices/ppo-model-training'
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
    plot_events(histories, results_dir)
    save_episode_summary(histories, results_dir)
    print_summary(histories)

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
