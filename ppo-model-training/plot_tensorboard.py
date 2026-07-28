#!/usr/bin/env python3
"""
Plot TensorBoard training curves from PPO training events.
"""

import os
import sys

sys.path.insert(0, '/home/almuzky/TA/Microservices/ppo-model-training')

from tensorboard.backend.event_processing import event_accumulator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def load_tensorboard_events(log_dir):
    """
    Load TensorBoard event files and return a dict of metric -> [(step, value), ...]
    """
    ea = event_accumulator.EventAccumulator(log_dir)
    ea.Reload()

    metrics = {}
    for tag in ea.Tags()['scalars']:
        events = ea.Scalars(tag)
        values = [(e.step, e.value) for e in events]
        metrics[tag] = values

    return metrics


def plot_training_curves(metrics, out_path):
    """
    Plot training curves for key metrics.
    """
    # Select key metrics to plot
    key_metrics = {
        'rollout/ep_rew_mean': 'Mean Episode Reward',
        'rollout/ep_len_mean': 'Episode Length',
        'train/loss': 'Policy Loss',
        'train/value_loss': 'Value Loss',
        'train/entropy_loss': 'Entropy Loss',
        'train/clip_fraction': 'Clip Fraction',
        'train/approx_kl': 'Approximate KL Divergence',
        'train/explained_variance': 'Explained Variance',
        'train/learning_rate': 'Learning Rate',
        'rollout/reward_growth': 'Reward Growth',
        'rollout/reward_resource': 'Reward Resource',
        'rollout/reward_state': 'Reward State',
        'rollout/reward_env': 'Reward Env',
        'rollout/reward_hypoxia': 'Reward Hypoxia',
        'rollout/reward_interval': 'Reward Interval',
        'rollout/reward_efficiency': 'Reward Efficiency',
    }

    # Create subplots
    n_plots = len(key_metrics)
    n_cols = 3
    n_rows = max(1, (n_plots + n_cols - 1) // n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    if n_rows == 1 and n_cols == 1:
        axes = np.array([[axes]])
    elif n_rows == 1 or n_cols == 1:
        axes = axes.flatten()
    else:
        axes = axes.flatten()

    plot_idx = 0
    for tag, title in key_metrics.items():
        if tag in metrics and plot_idx < len(axes):
            ax = axes[plot_idx]
            values = metrics[tag]
            steps = [v[0] for v in values]
            vals = [v[1] for v in values]

            if len(vals) > 20:
                window = max(1, len(vals) // 30)
                kernel = np.ones(window) / window
                smooth = np.convolve(vals, kernel, mode='valid')
                smooth_steps = steps[window - 1:]
                ax.plot(smooth_steps, smooth, label='Smoothed', color='tab:blue', linewidth=2.0)
                ax.plot(steps, vals, label='Raw', color='tab:blue', linewidth=0.6, alpha=0.35)
                ax.legend(fontsize=8)
            else:
                ax.plot(steps, vals, label=title, color='tab:blue', linewidth=1.5)
                ax.legend(fontsize=8)

            ax.set_title(title)
            ax.set_xlabel('Timestep')
            ax.set_ylabel('Value')
            ax.grid(True, alpha=0.3)

            plot_idx += 1

    # Hide unused subplots
    for idx in range(plot_idx, len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved training curves: {out_path}")
    plt.close()


def plot_reward_components(metrics, out_path):
    """
    Plot reward components if available.
    """
    reward_tags = [tag for tag in metrics.keys() if 'reward' in tag.lower()]

    if not reward_tags:
        print("No reward metrics found in TensorBoard logs")
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    for tag in reward_tags:
        values = metrics[tag]
        steps = [v[0] for v in values]
        vals = [v[1] for v in values]
        ax.plot(steps, vals, label=tag, linewidth=1.5, alpha=0.8)

    ax.set_xlabel('Timestep')
    ax.set_ylabel('Reward Value')
    ax.set_title('Reward Metrics During Training')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved reward components: {out_path}")
    plt.close()


def print_summary(metrics):
    """
    Print summary statistics for key metrics.
    """
    print("\n" + "=" * 80)
    print("TENSORBOARD TRAINING SUMMARY")
    print("=" * 80)

    key_metrics = {
        'rollout/ep_rew_mean': 'Mean Episode Reward',
        'rollout/ep_len_mean': 'Episode Length',
        'train/loss': 'Policy Loss',
        'train/value_loss': 'Value Loss',
        'train/entropy_loss': 'Entropy Loss',
        'train/clip_fraction': 'Clip Fraction',
        'train/approx_kl': 'Approximate KL',
        'train/explained_variance': 'Explained Variance',
        'train/learning_rate': 'Learning Rate',
        'rollout/reward_growth': 'Reward Growth',
        'rollout/reward_resource': 'Reward Resource',
        'rollout/reward_state': 'Reward State',
        'rollout/reward_env': 'Reward Env',
        'rollout/reward_hypoxia': 'Reward Hypoxia',
        'rollout/reward_interval': 'Reward Interval',
        'rollout/reward_efficiency': 'Reward Efficiency',
        'rollout/reward_humidity_maintenance': 'Reward Humidity Maint.',
        'rollout/reward_temperature_maintenance': 'Reward Temp Maint.',
    }

    for tag, name in key_metrics.items():
        if tag in metrics:
            values = [v[1] for v in metrics[tag]]
            if values:
                print(f"\n{name}:")
                print(f"  First: {values[0]:.4f}")
                print(f"  Last: {values[-1]:.4f}")
                print(f"  Min: {min(values):.4f}")
                print(f"  Max: {max(values):.4f}")
                print(f"  Mean: {np.mean(values):.4f}")
                print(f"  Std: {np.std(values):.4f}")

    print("\n" + "=" * 80)


def get_latest_tensorboard_log_dir(tensorboard_base_dir):
    """Auto-detect the latest TensorBoard run directory by modification time."""
    if not os.path.exists(tensorboard_base_dir):
        raise FileNotFoundError(f"TensorBoard directory not found: {tensorboard_base_dir}")

    run_dirs = [d for d in os.listdir(tensorboard_base_dir) if os.path.isdir(os.path.join(tensorboard_base_dir, d))]
    if not run_dirs:
        raise FileNotFoundError(f"No run directories found in {tensorboard_base_dir}")

    latest_run = max(run_dirs, key=lambda d: os.path.getmtime(os.path.join(tensorboard_base_dir, d)))
    return os.path.join(tensorboard_base_dir, latest_run)


def main():
    tensorboard_base_dir = '/home/almuzky/TA/Microservices/ppo-model-training/aeroponic_ppo_tensorboard'
    results_dir = '/home/almuzky/TA/Microservices/ppo-model-training/results'
    os.makedirs(results_dir, exist_ok=True)

    log_dir = get_latest_tensorboard_log_dir(tensorboard_base_dir)
    print("=" * 80)
    print("TENSORBOARD TRAINING CURVES")
    print("=" * 80)
    print(f"Log directory: {log_dir}")

    metrics = load_tensorboard_events(log_dir)
    print(f"\nLoaded {len(metrics)} scalar metrics from TensorBoard")

    # Print available tags
    print("\nAvailable metrics:")
    for tag in sorted(metrics.keys()):
        print(f"  - {tag}")

    # Plot training curves
    plot_training_curves(metrics, os.path.join(results_dir, 'ppo_training_curves.png'))

    # Plot reward components if available
    plot_reward_components(metrics, os.path.join(results_dir, 'ppo_reward_components.png'))

    # Print summary
    print_summary(metrics)

    print("\n" + "=" * 80)
    print("TENSORBOARD PLOTTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
