#!/usr/bin/env python3
"""
Stress testing for PPO aeroponic model across 5 weather scenarios.
"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, '/home/almuzky/TA/Microservices/services/ml-control')

from stable_baselines3 import PPO
from aeroponic_simulator import AeroponicSimulatorEnv


def run_scenario(scenario_name, seed, **kwargs):
    """Run one evaluation episode with forced weather scenario."""
    import random
    random.seed(seed)
    np.random.seed(seed)
    
    env = AeroponicSimulatorEnv()
    env.reset()
    obs = env.state[:]
    
    # Override environment parameters for scenario
    for key, value in kwargs.items():
        if hasattr(env, key):
            setattr(env, key, value)
    
    # Also override state values if provided
    if 'T_in_override' in kwargs:
        env.state[2] = kwargs['T_in_override']
    if 'H_in_override' in kwargs:
        env.state[3] = kwargs['H_in_override']
    
    model = PPO.load('/home/almuzky/TA/Microservices/services/ml-control/models/aeroponic_ppo.zip')
    
    total_reward = 0
    actions = []
    captures = 0
    L_root_history = []
    T_root_history = []
    H_in_history = []
    
    for step in range(200):
        action, _ = model.predict(obs, deterministic=False)
        actions.append(action.tolist())
        obs, reward, term, trunc, info = env.step(action)
        total_reward += reward
        captures += int(info.get('captured', False))
        L_root_history.append(env.state[0])
        T_root_history.append(env.T_root)
        H_in_history.append(env.state[3])
        if term or trunc:
            break
    
    growth = env.state[0] - 8.0
    
    result = {
        'name': scenario_name,
        'growth': growth,
        'total_reward': total_reward,
        'episode_length': len(actions),
        'captures': captures,
        'final_L_root': env.state[0],
        'final_T_root': env.T_root,
        'final_H_in': env.state[3],
        'min_L_root': min(L_root_history),
        'max_L_root': max(L_root_history),
        'min_T_root': min(T_root_history),
        'max_T_root': max(T_root_history),
        'min_H_in': min(H_in_history),
        'max_H_in': max(H_in_history),
    }
    
    # Action diversity
    if len(actions) > 1:
        d_mist_vals = [a[0] for a in actions]
        interval_vals = [a[1] for a in actions]
        a_valve_vals = [a[2] for a in actions]
        
        result['D_mist_mean'] = np.mean(d_mist_vals)
        result['D_mist_std'] = np.std(d_mist_vals)
        result['D_mist_cv'] = np.std(d_mist_vals) / np.mean(d_mist_vals) if np.mean(d_mist_vals) > 0 else 0
        
        result['interval_mean'] = np.mean(interval_vals)
        result['interval_std'] = np.std(interval_vals)
        result['interval_cv'] = np.std(interval_vals) / np.mean(interval_vals) if np.mean(interval_vals) > 0 else 0
        
        result['A_valve_mean'] = np.mean(a_valve_vals)
        result['A_valve_usage'] = sum(1 for v in a_valve_vals if v >= 0.5) / len(a_valve_vals)
    
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario_name}")
    print(f"  Growth: {growth:.4f} cm")
    print(f"  Total reward: {total_reward:.2f}")
    print(f"  Episode length: {len(actions)} cycles")
    print(f"  Captures: {captures}")
    print(f"  Final L_root: {env.state[0]:.4f}")
    print(f"  Final T_root: {env.T_root:.2f}°C")
    print(f"  Final H_in: {env.state[3]:.2f}%")
    if 'D_mist_mean' in result:
        print(f"  D_mist CV: {result['D_mist_cv']:.3f}")
        print(f"  Interval CV: {result['interval_cv']:.3f}")
        print(f"  A_valve usage: {result['A_valve_usage']:.1%}")
    
    return result


def main():
    print("=" * 80)
    print("PPO STRESS TESTING - 5 WEATHER SCENARIOS")
    print("=" * 80)
    
    seed = 42
    scenarios = [
        ("Baseline", seed, {}),
        ("Hot & Dry", seed + 1, {
            'T_in_override': 32.0,
            'H_in_override': 50.0,
        }),
        ("Cool & Humid", seed + 2, {
            'T_in_override': 22.0,
            'H_in_override': 90.0,
        }),
        ("Rainy", seed + 3, {
            'T_in_override': 25.0,
            'H_in_override': 95.0,
            'light_intensity': 0.3,
        }),
        ("Night", seed + 4, {
            'light_intensity': 0.1,
        }),
    ]
    
    results = []
    for name, s, kwargs in scenarios:
        result = run_scenario(name, s, **kwargs)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 80)
    print("STRESS TEST SUMMARY")
    print("=" * 80)
    
    all_pass = True
    for r in results:
        passed = r['growth'] > 0.05 and r['final_L_root'] > 8.0
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{r['name']:15s}: growth={r['growth']:6.4f} cm | reward={r['total_reward']:8.2f} | {status}")
        if not passed:
            all_pass = False
    
    print(f"\nOverall: {'✅ ALL PASSED' if all_pass else '❌ SOME FAILED'}")
    
    # CV metrics
    print(f"\nAction Diversity (CV > 0.25 = good):")
    for r in results:
        if 'D_mist_cv' in r:
            d_cv = r['D_mist_cv']
            i_cv = r['interval_cv']
            a_usage = r['A_valve_usage']
            status = "✅" if d_cv > 0.25 and i_cv > 0.25 and 0.4 <= a_usage <= 0.6 else "⚠️"
            print(f"  {r['name']:15s}: D_mist={d_cv:.3f}, interval={i_cv:.3f}, A_valve={a_usage:.1%} {status}")
    
    print("\n" + "=" * 80)
    print("STRESS TESTING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
