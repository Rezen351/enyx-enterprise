#!/usr/bin/env python3
"""
Evaluate trained PPO model with domain randomization.
"""

import os
import sys

sys.path.insert(0, '/home/almuzky/TA/Microservices/ppo-model-training')

import numpy as np
from evaluate_ppo import load_model_and_env, evaluate_domain_randomization


def main():
    print("=" * 80)
    print("DOMAIN RANDOMIZATION EVALUATION - 500K MODEL")
    print("=" * 80)

    model, vec_env = load_model_and_env()
    results = evaluate_domain_randomization(model, vec_env, num_episodes=5)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for name, res in results.items():
        print(f"\n{name.upper()}:")
        print(f"  Growth: {res['mean_growth']:.4f} ± {res['std_growth']:.4f} cm")
        print(f"  Reward: {res['mean_reward']:.2f} ± {res['std_reward']:.2f}")


if __name__ == '__main__':
    main()
