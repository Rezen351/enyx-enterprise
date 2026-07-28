#!/usr/bin/env python3
"""
Run 7-day PPO continuous simulation for weekly validation.
"""
import sys
import os

sys.path.insert(0, '/home/almuzky/TA/Microservices/ppo-model-training')

from aeroponic_simulator_analysis import run_ppo_multi_day_simulation, plot_multi_day

base_dir = '/home/almuzky/TA/Microservices/services/ml-control'
results_dir = os.path.join(base_dir, 'results')
os.makedirs(results_dir, exist_ok=True)

history = run_ppo_multi_day_simulation(days=7, deterministic=False)
if history is not None:
    plot_multi_day(history, os.path.join(results_dir, 'ppo_multi_day_7d.png'))
    print(f"Saved: {os.path.join(results_dir, 'ppo_multi_day_7d.png')}")
