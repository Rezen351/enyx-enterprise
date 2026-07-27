#!/usr/bin/env python3
"""
Run 30-day PPO continuous simulation.
"""
import sys
import os

sys.path.insert(0, '/home/almuzky/TA/Microservices/services/ml-control')

from aeroponic_simulator import run_ppo_multi_day_simulation, plot_multi_day

base_dir = '/home/almuzky/TA/Microservices/services/ml-control'
results_dir = os.path.join(base_dir, 'results')
os.makedirs(results_dir, exist_ok=True)

history = run_ppo_multi_day_simulation(days=30, deterministic=False)
if history is not None:
    plot_multi_day(history, os.path.join(results_dir, 'ppo_multi_day_30d.png'))
    print(f"Saved: {os.path.join(results_dir, 'ppo_multi_day_30d.png')}")
