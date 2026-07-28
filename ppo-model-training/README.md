# PPO Model Training

Training location untuk PPO model aeroponic greenhouse control.

## Directory Structure

```
ppo-model-training/
├── train_ppo.py              # Main PPO training script
├── evaluate_ppo.py           # Model evaluation with curriculum/DR testing
├── plot_tensorboard.py       # Training curve visualization
├── aeroponic_simulator.py    # Gymnasium environment with extreme weather
├── evaluate_domain_randomization.py  # Domain randomization evaluation
├── models/
│   ├── aeroponic_ppo.zip     # Trained PPO model
│   └── vec_normalize.pkl     # Observation/reward normalization stats
├── aeroponic_ppo_tensorboard/ # TensorBoard logs
└── results/                  # Training curves, evaluation plots
```

## Model Architecture

- **Policy:** MlpPolicy (2 hidden layers, 64 units each)
- **Observation space:** 10D continuous `[L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]`
- **Action space:** 3D continuous `[-1, 1]` mapped to:
  - `D_mist`: `[60, 900]` seconds (1–15 minutes ON)
  - `interval_sec`: `[60, 900]` seconds (1–15 minutes OFF)
  - `A_valve`: `[0, 1]` (threshold at 0)

## Reward Structure

| Component | Weight | Condition |
|-----------|--------|-----------|
| `R_growth` | `w_growth=15.0` | Per-step growth reward from simulator |
| `R_humidity_maintenance` | +1.5 / -3.0 | +1.5 if `80≤H_in≤95%`, -3.0 if `H_in<70%` or `H_in>97%` |
| `R_temperature_maintenance` | +1.5 / -3.0 | +1.5 if `18≤T_in≤28°C`, -3.0 if `T_in<15°C` or `T_in>32°C` |
| `R_efficiency` | +0.05/+0.03/+0.02 | If state healthy: valve OFF, `D_mist≤180s`, `interval≥600s` |
| `P_env` | `w_env=0.05` | pH/EC/H_in deviation penalty |
| `P_hypoxia` | `w_hypoxia=0.02` | Oxygen depletion penalty |
| `P_interval` | `w_interval=0.01` | Very long interval penalty (`>720s`) |
| `C_resource` | `w_valve_cost=0.15` | Per-misting valve cost |

**Target sweet spot:** Agent learns to maximize growth (~2–4 cm per episode) while keeping H_in and T_in in safe zone 98% of the time.

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Total timesteps | 500,000 |
| Learning rate | 3e-4 → 1e-5 (linear schedule) |
| `n_steps` | 4096 |
| `batch_size` | 256 |
| `n_epochs` | 10 |
| `gamma` | 0.995 |
| `clip_range` | 0.1 |
| `gae_lambda` | 0.95 |
| `ent_coef` | 0.05 (adaptive) |
| `vf_coef` | 0.5 |
| `max_grad_norm` | 1.0 |

## Curriculum & Domain Randomization

- **Curriculum weather scale:** 0.3 → 1.0 linear over training
- **Sensor noise:** ±0.3°C T, ±2% H, ±0.1 EC, ±0.1 pH
- **Actuator noise:** ±5% D_mist, ±0.3s spray delay
- **Extreme weather events:** heat wave, cold snap, drought, storm (5–8% probability each)

## Evaluation Results (500k model)

| Metric | Value |
|--------|-------|
| Mean Episode Reward | 1,576 |
| Explained Variance | 0.937 |
| Value Loss | 0.021 |
| H_in safe zone | ~58% (before maintenance reward retrain) |
| T_in safe zone | ~77% (before maintenance reward retrain) |

**Next step:** Retrain with balanced reward weights to achieve 98% safe zone for both H_in and T_in.

## How to Train

```bash
# Fresh training
python3 train_ppo.py

# Resume from existing model
python3 train_ppo.py  # Will auto-resume if model exists
```

## How to Evaluate

```bash
# Basic evaluation
python3 evaluate_ppo.py

# Domain randomization evaluation
python3 evaluate_domain_randomization.py

# Plot training curves
python3 plot_tensorboard.py
```

## Model Deployment

Trained model is used by `ppo-controller` service:
- Model path: `models/aeroponic_ppo.zip`
- VecNormalize path: `models/vec_normalize.pkl`
- Input: 10D state vector
- Output: `D_mist`, `interval_sec`, `A_valve`
