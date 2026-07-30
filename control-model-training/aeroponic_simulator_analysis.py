#!/usr/bin/env python3
"""
Aeroponic Simulator - Analysis, Validation, and Plotting Utilities
Depends on core environment from aeroponic_simulator.py.
"""

import os
import math
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from aeroponic_simulator import AeroponicSimulatorEnv


def run_validation():
    env = AeroponicSimulatorEnv()
    print("=" * 80)
    print("AEROPONIC SIMULATOR NUMERICAL VALIDATION (TIMER-BASED)")
    print("=" * 80)

    print("\n[TEST 1] Initial state matches notebook section 3.8")
    init = env.reset()
    # Indonesian dawn initialization (episode starts at 06:00)
    # T_in: 22-24°C, H_in: 85-95%, T_out: 23-26°C, H_out: 75-85%
    expected_ranges = [
        (8.0, 8.0, 0.01),      # L_root: exact
        (0.95, 0.95, 0.01),    # U_status: exact
        (22.0, 24.0, None),    # T_in: dawn/night residual range
        (85.0, 95.0, None),    # H_in: dawn/night humidity range
        (23.0, 26.0, None),    # T_out: dawn/night range
        (75.0, 85.0, None),    # H_out: dawn/night range
        (1.4, 2.0, None),      # EC: tropical range
        (5.6, 6.2, None),      # pH: tropical range
        (22.0, 26.0, None),    # T_nut: near T_in
        (1.0, 1.0, 0.01)       # I_day: exact
    ]
    labels = ["L_root", "U_status", "T_in", "H_in", "T_out", "H_out", "EC", "pH", "T_nut", "I_day"]
    for i, (v, e, lbl) in enumerate(zip(init, expected_ranges, labels)):
        low, high, tol = e
        if tol is None:
            ok = low <= v <= high
            print(f"  {lbl:10s}: {v:.4f} (expected [{low:.1f}, {high:.1f}]) {'OK' if ok else 'FAIL'}")
        else:
            ok = math.isclose(v, low, rel_tol=tol, abs_tol=tol)
            print(f"  {lbl:10s}: {v:.4f} (expected {low:.4f}) {'OK' if ok else 'FAIL'}")

    print("\n[TEST 2] Timer-based cycle: ON 180s + OFF 540s")
    env.reset()
    initial_time = env.current_time
    _, reward, terminated, truncated, info = env.step([180.0, 540.0, 0.0])
    elapsed = env.current_time - initial_time
    # Allow ±120s variance due to actuator noise and substep truncation
    ok = 600 <= elapsed <= 840
    print(f"  Cycle elapsed: {elapsed:.0f}s (expected ~720s ±120s) {'OK' if ok else 'FAIL'}")
    print(f"  Terminated: {terminated}, Truncated: {truncated}")

    print("\n[TEST 3] Full episode with sensible policy")
    env.reset()
    initial_time = env.current_time
    captures = 0
    cycles = 0
    while not env.current_time >= env.episode_duration - 1:
        action = [180.0, 540.0, 0.0]
        _, reward, terminated, truncated, info = env.step(action)
        cycles += 1
        if terminated or truncated:
            break
    print(f"  Cycles completed: {cycles}")
    print(f"  Final time: {env.current_time:.0f}s / {env.episode_duration:.0f}s")
    print(f"  Final L_root: {env.state[0]:.4f}")

    print("\n[TEST 4] A_valve bottom zone effects")
    env.reset()
    EC_before = env.state[6]
    _, _, _, _, info = env.step([180.0, 540.0, 1.0])
    EC_after = env.state[6]
    print(f"  EC before valve: {EC_before:.4f}, after valve=1.0: {EC_after:.4f}")
    # Allow ±0.15 variance due to sensor noise and dynamics
    ok = 1.4 <= EC_after <= 1.6
    print(f"  Expected reset to 1.5 ±0.1 {'OK' if ok else 'FAIL'}")

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


def run_episode_and_plot(policy_name, actions):
    """Run one full episode with given action list and plot time series."""
    env = AeroponicSimulatorEnv()
    state = env.reset()
    terminated = False
    truncated = False
    steps = 0
    cycle_times = [0.0]
    history = {
        'time': [],
        'cycle': [],
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
    }
    while not terminated and not truncated:
        action = actions[min(steps, len(actions) - 1)]
        state, reward, terminated, truncated, info = env.step(action)
        history['time'].append(env.current_time / 3600.0)  # hours
        history['cycle'].append(steps)
        history['L_root'].append(state[0])
        history['H_in'].append(state[3])
        history['T_in'].append(state[2])
        history['T_out'].append(state[4])
        history['H_out'].append(state[5])
        history['EC'].append(state[6])
        history['pH'].append(state[7])
        history['T_nut'].append(state[8])
        history['O2_status'].append(info['O2_status'])
        history['total_reward'].append(reward)
        history['D_mist'].append(action[0])
        history['interval_sec'].append(action[1])
        history['A_valve'].append(action[2])
        steps += 1
        cycle_times.append(env.current_time)
    return history


def plot_episode(history, policy_name, out_path=None):
    times = history['time']
    fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)
    ax1, ax2, ax3, ax4 = axes

    # Panel 1: Root length
    ax1.plot(times, history['L_root'], label='L_root', color='tab:blue')
    ax1.set_ylabel('L_root (cm)')
    ax1.set_title(f'{policy_name} — Root Length')
    ax1.grid(True)

    # Panel 2: Internal vs External Humidity
    ax2.plot(times, history['H_in'], label='H_in', color='tab:green')
    ax2.plot(times, history['H_out'], label='H_out', color='tab:olive', linestyle='--')
    ax2.set_ylabel('Humidity (%)')
    ax2.set_title('Internal vs External Humidity')
    ax2.legend()
    ax2.grid(True)

    # Panel 3: Internal vs External Temperature
    ax3.plot(times, history['T_in'], label='T_in', color='tab:red')
    ax3.plot(times, history['T_out'], label='T_out', color='tab:orange', linestyle='--')
    ax3.set_ylabel('Temperature (°C)')
    ax3.set_title('Internal vs External Temperature')
    ax3.legend()
    ax3.grid(True)

    # Panel 4: EC, pH, and T_nut
    ax4.plot(times, history['EC'], label='EC', color='tab:red')
    ax4.plot(times, history['pH'], label='pH', color='tab:purple')
    ax4.plot(times, history['T_nut'], label='T_nut', color='tab:brown', linestyle=':')
    ax4.set_ylabel('EC / pH / T_nut')
    ax4.set_title('EC, pH, and Nutrient Temperature')
    ax4.set_xlabel('Time (hours)')
    ax4.legend()
    ax4.grid(True)

    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=150)
        print(f"  Saved: {out_path}")
    else:
        plt.show()
    plt.close(fig)


def run_multi_day_simulation(days=90, action=None, verbose=True):
    """
    Run continuous multi-day simulation without full episode reset.
    
    Each episode is 3 hours (180 steps * 60s). We run days*8 episodes,
    carrying over L_root and climate state across episodes via continuous reset.
    
    Args:
        days: Number of days to simulate (default: 90)
        action: Fixed action [D_mist, interval_sec, A_valve] to apply each cycle.
                If None, uses sensible default [180s, 540s, 0.0].
        verbose: If True, print daily progress
        
    Returns:
        dict with history of daily snapshots
    """
    if action is None:
        action = [180.0, 540.0, 0.0]
    
    env = AeroponicSimulatorEnv()
    state = env.reset(mode='simulation', continuous=True, episode_duration=10800.0, max_steps=1440)
    
    episodes_per_day = 8  # 3h per episode * 8 = 24h
    total_episodes = days * episodes_per_day
    target_simulation_time = days * 86400.0  # total seconds to simulate
    
    history = {
        'day': [0],
        'time_s': [0.0],
        'L_root': [state[0]],
        'H_in': [state[3]],
        'T_in': [state[2]],
        'T_out': [state[4]],
        'H_out': [state[5]],
        'EC': [state[6]],
        'pH': [state[7]],
        'T_nut': [state[8]],
        'reward': [0.0],
    }
    
    total_reward = 0.0
    episode_count = 0
    last_logged_day = 0
    
    while env.current_time < target_simulation_time and episode_count < total_episodes:
        state, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        
        if terminated:
            if verbose:
                print(f"Day {last_logged_day + 1}: EARLY TERMINATED at {env.current_time:.0f}s "
                      f"(episode {episode_count + 1})")
                print(f"  EC={state[6]:.4f}, pH={state[7]:.4f}, H_in={state[3]:.2f}%")
                print(f"  Final L_root={state[0]:.4f} cm")
            return history
        
        if truncated:
            episode_count += 1
            current_day = int(env.current_time / 86400.0)
            
            while last_logged_day < current_day and last_logged_day < days:
                last_logged_day += 1
                history['day'].append(last_logged_day)
                history['time_s'].append(env.current_time)
                history['L_root'].append(state[0])
                history['H_in'].append(state[3])
                history['T_in'].append(state[2])
                history['T_out'].append(state[4])
                history['H_out'].append(state[5])
                history['EC'].append(state[6])
                history['pH'].append(state[7])
                history['T_nut'].append(state[8])
                history['reward'].append(total_reward)
                
                if verbose and (last_logged_day % 7 == 0 or last_logged_day == 1):
                    growth = state[0] - history['L_root'][0]
                    print(f"Day {last_logged_day:3d}: L_root={state[0]:.4f} cm (growth: +{growth:.4f} cm), "
                          f"EC={state[6]:.2f}, pH={state[7]:.2f}, "
                          f"T_in={state[2]:.1f}C, T_nut={state[8]:.1f}C")
            
            if episode_count < total_episodes:
                state = env.reset(L_root=state[0], continuous=True, mode='simulation', episode_duration=10800.0, max_steps=1440)
    
    # Log final state if simulation ended mid-day
    if last_logged_day < days:
        last_logged_day += 1
        history['day'].append(last_logged_day)
        history['time_s'].append(env.current_time)
        history['L_root'].append(state[0])
        history['H_in'].append(state[3])
        history['T_in'].append(state[2])
        history['T_out'].append(state[4])
        history['H_out'].append(state[5])
        history['EC'].append(state[6])
        history['pH'].append(state[7])
        history['T_nut'].append(state[8])
        history['reward'].append(total_reward)
    
    if verbose:
        print("\n" + "=" * 70)
        print(f"SIMULATION COMPLETE: {days} days")
        print(f"Initial L_root: {history['L_root'][0]:.4f} cm")
        print(f"Final L_root:   {history['L_root'][-1]:.4f} cm")
        print(f"Total growth:   {history['L_root'][-1] - history['L_root'][0]:.4f} cm")
        print(f"Total reward:   {total_reward:.2f}")
        print("=" * 70)
    
    return history


def plot_multi_day(history, out_path=None):
    """
    Plot multi-day simulation results.
    """
    days = history['day']
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    
    # Row 1: L_root and T_in/T_out
    ax1 = axes[0, 0]
    ax2 = axes[0, 1]
    ax1.plot(days, history['L_root'], marker='o', markersize=2, linewidth=1.5, color='tab:blue')
    ax1.set_xlabel('Day')
    ax1.set_ylabel('L_root (cm)')
    ax1.set_title('Root Length Over 90 Days')
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(days, history['T_in'], label='T_in', color='tab:red', alpha=0.7)
    ax2.plot(days, history['T_out'], label='T_out', color='tab:orange', linestyle='--', alpha=0.7)
    ax2.plot(days, history['T_nut'], label='T_nut', color='tab:brown', linestyle=':', alpha=0.7)
    ax2.set_xlabel('Day')
    ax2.set_ylabel('Temperature (°C)')
    ax2.set_title('Temperature Trends')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Row 2: EC and pH
    ax3 = axes[1, 0]
    ax4 = axes[1, 1]
    ax3.plot(days, history['EC'], marker='s', markersize=2, linewidth=1.5, color='tab:red')
    ax3.set_xlabel('Day')
    ax3.set_ylabel('EC (mS/cm)')
    ax3.set_title('Electrical Conductivity')
    ax3.grid(True, alpha=0.3)
    
    ax4.plot(days, history['pH'], marker='^', markersize=2, linewidth=1.5, color='tab:purple')
    ax4.set_xlabel('Day')
    ax4.set_ylabel('pH')
    ax4.set_title('pH Over Time')
    ax4.grid(True, alpha=0.3)
    
    # Row 3: H_in and H_out
    ax5 = axes[2, 0]
    ax6 = axes[2, 1]
    ax5.plot(days, history['H_in'], marker='d', markersize=2, linewidth=1.5, color='tab:green')
    ax5.set_xlabel('Day')
    ax5.set_ylabel('H_in (%)')
    ax5.set_title('Internal Humidity')
    ax5.grid(True, alpha=0.3)
    
    ax6.plot(days, history['H_out'], marker='v', markersize=2, linewidth=1.5, color='tab:olive')
    ax6.set_xlabel('Day')
    ax6.set_ylabel('H_out (%)')
    ax6.set_title('External Humidity')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=150)
        print(f"Saved multi-day plot: {out_path}")
    else:
        plt.show()
    plt.close(fig)


def plot_reward(history, policy_name, out_path=None):
    times = history['time']
    cycles = history['cycle']
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    ax1, ax2 = axes

    ax1.plot(cycles, history['total_reward'], label='Total Reward', color='tab:blue')
    ax1.set_ylabel('Reward')
    ax1.set_title(f'{policy_name} — Reward per Cycle')
    ax1.grid(True)

    ax2.plot(cycles, history['D_mist'], label='D_mist', color='tab:orange', alpha=0.7)
    ax2.plot(cycles, history['interval_sec'], label='Interval', color='tab:green', alpha=0.7)
    ax2.set_ylabel('Seconds')
    ax2.set_xlabel('Cycle')
    ax2.set_title('Action Parameters per Cycle')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=150)
        print(f"  Saved: {out_path}")
    else:
        plt.show()
    plt.close(fig)


def run_test_plots():
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    print("=" * 80)
    print("AEROPONIC SIMULATOR PLOTTING (TIMER-BASED)")
    print("=" * 80)
    print(f"Results directory: {results_dir}")

    policy_a_actions = [[180.0, 540.0, 0.0]] * 200
    print("\n[PLOT A] Field-realistic cycle: ON 3 min, OFF 9 min, valve OFF")
    hist_a = run_episode_and_plot("Policy A: 3min ON / 9min OFF", policy_a_actions)
    plot_episode(hist_a, "Policy A: 3min ON / 9min OFF", os.path.join(results_dir, "policy_a_state.png"))
    plot_reward(hist_a, "Policy A: 3min ON / 9min OFF", os.path.join(results_dir, "policy_a_reward.png"))

    policy_b_actions = [[120.0, 360.0, 0.0]] * 200
    print("\n[PLOT B] Aggressive cycle: ON 2 min, OFF 6 min, valve OFF")
    hist_b = run_episode_and_plot("Policy B: 2min ON / 6min OFF", policy_b_actions)
    plot_episode(hist_b, "Policy B: 2min ON / 6min OFF", os.path.join(results_dir, "policy_b_state.png"))
    plot_reward(hist_b, "Policy B: 2min ON / 6min OFF", os.path.join(results_dir, "policy_b_reward.png"))

    policy_c_actions = [[240.0, 540.0, 1.0]] * 200
    print("\n[PLOT C] Long ON + valve ON: ON 4 min, OFF 9 min, valve ON")
    hist_c = run_episode_and_plot("Policy C: 4min ON / 9min OFF + valve", policy_c_actions)
    plot_episode(hist_c, "Policy C: 4min ON / 9min OFF + valve", os.path.join(results_dir, "policy_c_state.png"))
    plot_reward(hist_c, "Policy C: 4min ON / 9min OFF + valve", os.path.join(results_dir, "policy_c_reward.png"))

    print("\n" + "=" * 80)
    print("PLOTTING COMPLETE")
    print("=" * 80)


def run_ppo_multi_day_simulation(days=90, deterministic=False):
    """
    Run continuous multi-day simulation using trained PPO agent.
    
    Each episode is 3 hours. Uses a single environment instance across all
    episodes to preserve climate continuity (weather events, nutrient age,
    chronological time).
    
    Args:
        days: Number of days to simulate
        deterministic: If True, use deterministic actions; if False, stochastic
        
    Returns:
        dict with history of state evolution per day
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    except ImportError:
        print("ERROR: stable_baselines3 not installed. Cannot run PPO simulation.")
        return None
    
    base_dir = '/home/almuzky/TA/Microservices/ppo-model-training'
    model_path = f'{base_dir}/models/aeroponic_ppo.zip'
    vec_norm_path = f'{base_dir}/models/vec_normalize.pkl'
    
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        return None
    
    try:
        from train_ppo import AeroponicGymnasiumEnv
    except ImportError:
        print("ERROR: Cannot import AeroponicGymnasiumEnv from train_ppo.py")
        return None
    
    gym_env_local = AeroponicGymnasiumEnv()
    vec_env_local = DummyVecEnv([lambda: gym_env_local])
    vec_norm_local = VecNormalize.load(vec_norm_path, vec_env_local)
    vec_norm_local.training = False
    vec_norm_local.norm_reward = False
    
    model = PPO.load(model_path, env=vec_norm_local)
    
    print("\n" + "=" * 80)
    print(f"PPO {days}-DAY CONTINUOUS SIMULATION ({days} days)")
    print("=" * 80)
    
    history = {
        'day': [0],
        'time_s': [0.0],
        'L_root': [8.0],
        'H_in': [82.0],
        'T_in': [27.0],
        'T_out': [26.0],
        'H_out': [70.0],
        'EC': [1.7],
        'pH': [5.9],
        'T_nut': [27.0],
        'O2_status': [1.0],
        'D_mist': [],
        'interval_sec': [],
        'A_valve': [],
    }
    
    L_root_carry = 8.0
    total_growth = 0.0
    episode_count = 0
    episodes_per_day = 8
    total_episodes = days * episodes_per_day
    target_simulation_time = days * 86400.0
    last_logged_day = 0
    L_root_init = L_root_carry
    episode_actions = {'D_mist': [], 'interval_sec': [], 'A_valve': []}
    
    raw_obs, _ = gym_env_local.reset(L_root=L_root_carry, mode='simulation', continuous=True, episode_duration=10800.0, max_steps=1440)
    obs = vec_norm_local.normalize_obs(raw_obs.reshape(1, -1))
    
    while gym_env_local.sim.current_time < target_simulation_time and episode_count < total_episodes:
        episode_terminated = False
        last_action = None
        
        while not episode_terminated:
            sim = gym_env_local.sim
            pre_L_root = sim.state[0]
            pre_H_in = sim.state[3]
            pre_T_in = sim.state[2]
            pre_T_out = sim.state[4]
            pre_H_out = sim.state[5]
            pre_EC = sim.state[6]
            pre_pH = sim.state[7]
            pre_T_nut = sim.state[8]
            pre_O2 = sim.T_continuous
            pre_time = sim.current_time
            
            action, _ = model.predict(obs, deterministic=deterministic)
            action = np.asarray(action).flatten()
            action = np.clip(action, gym_env_local.action_space.low, gym_env_local.action_space.high)
            last_action = action
            
            raw_obs, reward, terminated, truncated, info = gym_env_local.step(action)
            obs = vec_norm_local.normalize_obs(raw_obs.reshape(1, -1))
            current_O2 = info.get('O2_status', max(0.2, 1.0 - 0.08 * max(0, pre_O2 - 3)))
            
            if terminated:
                episode_terminated = True
                print(f"Day {last_logged_day + 1}: EARLY TERMINATED at {pre_time:.0f}s "
                      f"(episode {episode_count + 1}/{total_episodes})")
                print(f"  EC={pre_EC:.4f}, pH={pre_pH:.4f}, H_in={pre_H_in:.2f}%")
                print(f"  Final L_root={pre_L_root:.4f} cm")
                break
            
            if truncated:
                episode_terminated = True
                episode_count += 1
                current_day = int(sim.current_time / 86400.0)
                
                if last_action is not None:
                    episode_actions['D_mist'].append(last_action[0])
                    episode_actions['interval_sec'].append(last_action[1])
                    episode_actions['A_valve'].append(last_action[2])
                
                # Log at each day boundary
                while last_logged_day < current_day and last_logged_day < days:
                    last_logged_day += 1
                    history['day'].append(last_logged_day)
                    history['time_s'].append(pre_time)
                    history['L_root'].append(pre_L_root)
                    history['H_in'].append(pre_H_in)
                    history['T_in'].append(pre_T_in)
                    history['T_out'].append(pre_T_out)
                    history['H_out'].append(pre_H_out)
                    history['EC'].append(pre_EC)
                    history['pH'].append(pre_pH)
                    history['T_nut'].append(pre_T_nut)
                    history['O2_status'].append(current_O2)
                    
                    print(f"Day {last_logged_day:3d}: L_root={pre_L_root:.4f} cm, "
                          f"H_in={pre_H_in:.1f}%, EC={pre_EC:.2f}, pH={pre_pH:.2f}, "
                          f"O2={current_O2:.2f}, D_mist={last_action[0]:.0f}s, interval={last_action[1]:.0f}s, "
                          f"growth_this_day={pre_L_root - L_root_init:.4f} cm")
                
                L_root_carry = pre_L_root
                total_growth += pre_L_root - L_root_init
                L_root_init = pre_L_root
                
                if episode_count < total_episodes:
                    raw_obs, _ = gym_env_local.reset(L_root=L_root_carry, mode='simulation', continuous=True, episode_duration=10800.0, max_steps=1440)
                    obs = vec_norm_local.normalize_obs(raw_obs.reshape(1, -1))
                break
    
    history['D_mist'] = episode_actions['D_mist']
    history['interval_sec'] = episode_actions['interval_sec']
    history['A_valve'] = episode_actions['A_valve']
    
    final_L = L_root_carry
    print(f"\nFinal L_root: {final_L:.4f} cm")
    print(f"Total growth over {days} days: {final_L - 8.0:.4f} cm")
    print(f"Average growth per day: {(final_L - 8.0)/days:.4f} cm/day")
    print("=" * 80)
    
    return history


if __name__ == "__main__":
    run_validation()
    print("\n")
    run_test_plots()
    
    # Run multi-day simulation demonstration
    print("\n" + "=" * 80)
    print("MULTI-DAY SIMULATION DEMO (90 days continuous)")
    print("=" * 80)
    multi_history = run_multi_day_simulation(days=90, action=[180.0, 540.0, 0.0], verbose=True)
    
    # Save multi-day plot
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    plot_multi_day(multi_history, os.path.join(results_dir, "multi_day_90d.png"))
    print(f"\nMulti-day simulation complete. Plot saved to: {results_dir}/multi_day_90d.png")
    
    # Run PPO agent 90-day simulation
    print("\n" + "=" * 80)
    print("PPO AGENT 90-DAY CONTINUOUS SIMULATION")
    print("=" * 80)
    ppo_history = run_ppo_multi_day_simulation(days=90, deterministic=False)
    if ppo_history is not None:
        plot_multi_day(ppo_history, os.path.join(results_dir, "ppo_multi_day_90d.png"))
        print(f"\nPPO multi-day simulation complete. Plot saved to: {results_dir}/ppo_multi_day_90d.png")
