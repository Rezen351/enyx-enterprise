#!/usr/bin/env python3
"""
Evaluate trained TD3 model on 3-day continuous simulation (2 episodes).
"""

import os
import sys
import csv

sys.path.insert(0, '/home/almuzky/TA/Microservices/ppo-model-training')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from stable_baselines3 import TD3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from aeroponic_simulator import AeroponicSimulatorEnv
from train_td3 import AeroponicGymnasiumEnv


def load_model_and_env():
    base_dir = '/home/almuzky/TA/Microservices/ppo-model-training'
    model_path = os.path.join(base_dir, 'models', 'aeroponic_td3.zip')
    vec_norm_path = os.path.join(base_dir, 'models', 'vec_normalize_td3.pkl')

    env = AeroponicGymnasiumEnv()
    vec_env = DummyVecEnv([lambda: env])
    vec_norm = VecNormalize.load(vec_norm_path, vec_env)
    vec_norm.training = False
    vec_norm.norm_reward = False

    model = TD3.load(model_path, env=vec_norm)
    return model, vec_norm


def evaluate_3day(model, vec_env, num_episodes=2, episode_duration=259200):
    """
    Evaluate trained policy over multiple days.
    episode_duration: seconds per episode (default 3 days = 259200s)
    """
    all_histories = []

    for ep in range(num_episodes):
        base_env = vec_env.envs[0]
        raw = base_env
        while hasattr(raw, 'env'):
            raw = raw.env
        sim = raw.sim

        # Reset in continuous mode to preserve climate state across days
        obs = vec_env.reset()
        terminated = False
        truncated = False
        steps = 0

        # Set episode duration on simulator AFTER reset so it doesn't get overwritten
        base_env = vec_env.venv.envs[0]
        raw = base_env
        while hasattr(raw, 'env'):
            raw = raw.env
        sim = raw.sim
        sim.episode_duration = float(episode_duration)
        sim.max_steps = 10_000
        print(f"  Sim episode_duration set to {sim.episode_duration}s ({sim.episode_duration/3600:.1f}h), max_steps={sim.max_steps}")

        history = {
            'cycle': [],
            'time_s': [],
            'time_h': [],
            'day': [],
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
        last_day = 0

        while not terminated and not truncated:
            action, _ = model.predict(obs, deterministic=True)
            action = np.asarray(action).flatten()
            action = np.clip(action, vec_env.action_space.low, vec_env.action_space.high)

            pre_L_root = sim.state[0]
            pre_time = sim.current_time
            pre_T_in = sim.state[2]
            pre_H_in = sim.state[3]
            pre_EC = sim.state[6]
            pre_pH = sim.state[7]
            pre_T_nut = sim.state[8]

            a_01 = (action + 1.0) / 2.0
            D_mist_phys = 120.0 + a_01[0] * 480.0
            interval_phys = 120.0 + a_01[1] * 480.0
            A_valve_phys = 1.0 if action[2] >= 0.0 else 0.0

            obs, reward, done, info = vec_env.step(action.reshape(1, -1))
            terminated = bool(np.any(done)) if isinstance(done, np.ndarray) else bool(done)
            sim = raw.sim

            # Determine day
            current_day = int(sim.current_time / 86400.0)
            if current_day != last_day:
                last_day = current_day

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
            history['day'].append(current_day)
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

            if steps % 100 == 0:
                print(f"  Step {steps}, time={log_time/3600:.1f}h, L_root={log_L:.2f}, pH={log_pH:.3f}, EC={log_EC:.3f}")

        if current_event_type != 'none' and current_event_start is not None:
            history['event_spans'].append((current_event_type, current_event_start, history['time_h'][-1]))

        all_histories.append(history)
        L_final = history['L_root'][-1]
        L_growth = L_final - L_root_init
        
        # Determine actual termination reason
        term_reason = 'unknown'
        if terminated:
            pH = sim.state[7]
            EC = sim.state[6]
            if pH < 4.5 or pH > 8.5 or EC < 0.5 or EC > 3.0:
                term_reason = f'TERMINATED (bounds) pH={pH:.3f} EC={EC:.3f}'
            else:
                term_reason = f'TERMINATED (other) pH={pH:.3f} EC={EC:.3f}'
        elif truncated:
            term_reason = f'TRUNCATED (time limit) time={history["time_s"][-1]:.0f}s'
        
        print(f"Episode {ep+1}: {steps} cycles, {term_reason}, "
              f"final L_root={L_final:.4f}, growth={L_growth:.4f} cm, time={history['time_s'][-1]/3600:.1f}h")

    return all_histories


def plot_multiday_episodes(histories, out_path):
    """
    Plot 3-day episodes with day boundaries marked.
    """
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']

    fig, axes = plt.subplots(6, 2, figsize=(16, 18))

    # Row 1: L_root
    ax = axes[0, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['L_root'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('L_root (cm)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Root Length (3-Day Simulation)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 1: H_in
    ax = axes[0, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['H_in'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('H_in (%)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Internal Humidity')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 2: H_out
    ax = axes[1, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['H_out'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('H_out (%)')
    ax.set_xlabel('Time (h)')
    ax.set_title('External Humidity')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 2: T_in
    ax = axes[1, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['T_in'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('T_in (°C)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Internal Temperature')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 3: T_out
    ax = axes[2, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['T_out'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('T_out (°C)')
    ax.set_xlabel('Time (h)')
    ax.set_title('External Temperature')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 3: T_nut
    ax = axes[2, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['T_nut'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('T_nut (°C)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Nutrient Temperature')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 4: EC
    ax = axes[3, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['EC'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    ax.axhline(y=1.2, color='tab:red', linestyle='--', alpha=0.5, label='EC bounds')
    ax.axhline(y=2.0, color='tab:red', linestyle='--', alpha=0.5)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('EC (mS/cm)')
    ax.set_xlabel('Time (h)')
    ax.set_title('EC')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 4: pH
    ax = axes[3, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['pH'], label=f'Ep {i+1}', color=colors[i], alpha=0.8)
    ax.axhline(y=5.5, color='tab:red', linestyle='--', alpha=0.5, label='pH bounds')
    ax.axhline(y=6.5, color='tab:red', linestyle='--', alpha=0.5)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('pH')
    ax.set_xlabel('Time (h)')
    ax.set_title('pH')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 5: D_mist
    ax = axes[4, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['D_mist'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('D_mist (s)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Misting Duration')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 5: interval
    ax = axes[4, 1]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['interval_sec'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Interval (s)')
    ax.set_xlabel('Time (h)')
    ax.set_title('Misting Interval')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 6: Total Reward
    ax = axes[5, 0]
    for i, hist in enumerate(histories):
        ax.plot(hist['time_h'], hist['total_reward'], label=f'Ep {i+1}', color=colors[i], alpha=0.7)
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('Reward')
    ax.set_xlabel('Time (h)')
    ax.set_title('Total Reward per Cycle')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Row 6: A_valve
    ax = axes[5, 1]
    for i, hist in enumerate(histories):
        ax.step(hist['time_h'], hist['A_valve'], label=f'Ep {i+1}', color=colors[i], alpha=0.7, where='post')
    for day in range(1, 4):
        ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    ax.set_ylabel('A_valve')
    ax.set_xlabel('Time (h)')
    ax.set_title('Bottom Valve (0=OFF, 1=ON)')
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['OFF', 'ON'])
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved 3-day episode comparison: {out_path}")
    plt.close()


def plot_action_histograms(histories, out_path):
    """Plot action distributions for 3-day episodes."""
    all_D_mist = []
    all_interval = []
    all_A_valve = []

    for hist in histories:
        all_D_mist.extend(hist['D_mist'])
        all_interval.extend(hist['interval_sec'])
        all_A_valve.extend(hist['A_valve'])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    ax1 = axes[0]
    ax1.hist(all_D_mist, bins=30, color='tab:blue', alpha=0.7, edgecolor='black')
    ax1.set_xlabel('D_mist (s)')
    ax1.set_ylabel('Count')
    ax1.set_title('Misting Duration Distribution (3-Day)')
    ax1.axvline(x=60, color='tab:green', linestyle='--', linewidth=2, label='Min (60s)')
    ax1.axvline(x=900, color='tab:red', linestyle='--', linewidth=2, label='Max (900s)')
    ax1.axvline(x=np.mean(all_D_mist), color='tab:orange', linestyle='--', linewidth=2, label=f'Mean: {np.mean(all_D_mist):.2f}s')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.hist(all_interval, bins=30, color='tab:green', alpha=0.7, edgecolor='black')
    ax2.set_xlabel('Interval (s)')
    ax2.set_ylabel('Count')
    ax2.set_title('Misting Interval Distribution (3-Day)')
    ax2.axvline(x=60, color='tab:green', linestyle='--', linewidth=2, label='Min (60s)')
    ax2.axvline(x=900, color='tab:red', linestyle='--', linewidth=2, label='Max (900s)')
    ax2.axvline(x=np.mean(all_interval), color='tab:orange', linestyle='--', linewidth=2, label=f'Mean: {np.mean(all_interval):.0f}s')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3 = axes[2]
    ax3.hist(all_A_valve, bins=[-0.5, 0.5, 1.5], color='tab:red', alpha=0.7, edgecolor='black', rwidth=0.6)
    ax3.set_xlabel('A_valve')
    ax3.set_ylabel('Count')
    ax3.set_title('Bottom Valve Actuation (3-Day)')
    ax3.set_xticks([0, 1])
    ax3.set_xticklabels(['OFF (0)', 'ON (1)'])
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved 3-day action histograms: {out_path}")
    plt.close()


def save_episode_summary(histories, out_path):
    """Save 3-day episode metrics summary to CSV."""
    out_path = os.path.join(out_path, 'episode_3day_summary.csv')
    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['episode', 'duration_h', 'cycles', 'final_L_root', 'L_growth',
                         'avg_D_mist', 'avg_interval', 'valve_usage_pct', 'events'])
        for i, hist in enumerate(histories):
            event_counts = {}
            for etype in hist.get('event_type', []):
                event_counts[etype] = event_counts.get(etype, 0) + 1
            duration_h = hist['time_s'][-1] / 3600.0 if hist['time_s'] else 0
            writer.writerow([
                i + 1,
                f'{duration_h:.2f}',
                len(hist['cycle']),
                f'{hist["L_root"][-1]:.4f}',
                f'{hist["L_root"][-1] - 8.0:.4f}',
                f'{np.mean(hist["D_mist"]):.2f}',
                f'{np.mean(hist["interval_sec"]):.0f}',
                f'{sum(1 for v in hist["A_valve"] if v >= 0.5) / len(hist["A_valve"]) * 100:.1f}',
                str(event_counts),
            ])
    print(f"Saved 3-day episode summary: {out_path}")


def print_summary(histories):
    print("\n" + "=" * 80)
    print("TD3 3-DAY EVALUATION SUMMARY")
    print("=" * 80)

    for i, hist in enumerate(histories):
        captures = sum(hist['captured'])
        total_reward = sum(hist['total_reward'])
        L_final = hist['L_root'][-1]
        L_growth = L_final - 8.0
        duration_h = hist['time_s'][-1] / 3600.0

        avg_D_mist = np.mean(hist['D_mist'])
        avg_interval = np.mean(hist['interval_sec'])
        avg_valve = np.mean(hist['A_valve'])

        print(f"\nEpisode {i+1} ({duration_h:.1f}h):")
        print(f"  Cycles: {len(hist['cycle'])}")
        print(f"  Captures: {captures}")
        print(f"  L_root: {L_final:.4f} cm (growth: {L_growth:+.4f} cm)")
        print(f"  Total reward: {total_reward:.2f}")
        print(f"  Avg D_mist: {avg_D_mist:.2f}s")
        print(f"  Avg interval: {avg_interval:.0f}s")
        print(f"  Avg A_valve: {avg_valve:.3f}")
        print(f"  Valve usage: {sum(1 for v in hist['A_valve'] if v >= 0.5)} cycles")

        event_counts = {}
        for etype in hist['event_type']:
            event_counts[etype] = event_counts.get(etype, 0) + 1
        print(f"  Events: {event_counts}")

        # Day-by-day summary
        print(f"  Day-by-day L_root:")
        for day in range(3):
            day_indices = [j for j, d in enumerate(hist['day']) if d == day]
            if day_indices:
                day_L = [hist['L_root'][j] for j in day_indices]
                day_reward = [hist['total_reward'][j] for j in day_indices]
                print(f"    Day {day+1}: final={day_L[-1]:.4f}, growth={day_L[-1]-8.0:+.4f}, reward={sum(day_reward):.2f}")


def run_evaluation():
    base_dir = '/home/almuzky/TA/Microservices/ppo-model-training'
    results_dir = os.path.join(base_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)

    print("=" * 80)
    print("TD3 3-DAY CONTINUOUS SIMULATION")
    print("=" * 80)

    model, vec_env = load_model_and_env()
    print("\nRunning 2 episodes of 72 hours each...")
    histories = evaluate_3day(model, vec_env, num_episodes=2, episode_duration=259200)

    plot_multiday_episodes(histories, os.path.join(results_dir, 'td3_3day_episode_comparison.png'))
    plot_action_histograms(histories, os.path.join(results_dir, 'td3_3day_action_histograms.png'))
    save_episode_summary(histories, results_dir)
    print_summary(histories)

    print("\n" + "=" * 80)
    print("3-DAY EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
