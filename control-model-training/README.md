# TD3 Model Training

Training location untuk TD3 model aeroponic greenhouse control.

## Directory Structure

```
control-model-training/
├── train_td3.py              # Main TD3 training script
├── evaluate_td3.py           # 5-episode TD3 evaluation with curriculum/DR testing
├── evaluate_td3_3day.py      # 3-day continuous TD3 evaluation
├── aeroponic_simulator.py    # Gymnasium environment with extreme weather
├── evaluate_domain_randomization.py  # Domain randomization evaluation
├── models/
│   ├── aeroponic_td3.zip     # Trained TD3 model
│   └── vec_normalize_td3.pkl # Observation/reward normalization stats
├── aeroponic_td3_tensorboard/ # TensorBoard logs
└── results/                  # Training curves, evaluation plots
```

## Model Architecture

- **Policy:** TD3 MlpPolicy (twin critics, delayed policy updates, target policy smoothing)
- **Observation space:** 10D continuous `[L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]`
- **Action space:** 3D continuous `[-1, 1]` mapped to:
  - `D_mist`: `[120, 600]` seconds (2–10 minutes ON)
  - `interval_sec`: `[120, 600]` seconds (2–10 minutes OFF)
  - `A_valve`: `[0, 1]` (threshold at 0)

## Reward Structure

| Component | Weight | Condition |
|-----------|--------|-----------|
| `R_growth` | `w_growth=15.0` | Per-step growth reward from simulator |
| `R_humidity_maintenance` | +1.5 / -3.0 | +1.5 if `80≤H_in≤95%`, -3.0 if `H_in<70%` or `H_in>97%` |
| `R_temperature_maintenance` | +1.5 / -3.0 | +1.5 if `18≤T_in≤28°C`, -3.0 if `T_in<15°C` or `T_in>32°C` |
| `R_efficiency` | +0.0–0.369 | Conditional + gradual: requires stable EC(1.2–2.0), pH(5.5–6.5), H_in≥80%, T_in(24–30°C); rewards D_mist<300s, interval>300s, and valve bonus |
| `P_env` | `w_env=0.05` | pH/EC/H_in deviation penalty |
| `P_hypoxia` | `w_hypoxia=0.02` | Oxygen depletion penalty |
| `P_interval` | `w_interval=0.01` | Very long interval penalty (`>720s`) |
| `C_resource` | `w_valve_cost=0.15` | Per-misting valve cost |

**Target sweet spot:** Agent learns to maximize growth (~2–4 cm per episode) while keeping H_in and T_in in safe zone 98% of the time.

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Total timesteps | 2,000,000 |
| Learning rate | 1e-4 (linear schedule) |
| `buffer_size` | 2,000,000 |
| `batch_size` | 256 |
| `tau` | 0.005 |
| `gamma` | 0.995 |
| `policy_delay` | 2 |
| `target_policy_noise` | 0.2 |
| `target_noise_clip` | 0.5 |
| `action_noise` | NormalActionNoise sigma=[0.1, 0.1, 0.2] |
| `learning_starts` | 100,000 |

## Curriculum & Domain Randomization

- **Curriculum weather scale:** 0.0 → 1.0 quadratic over training
- **Sensor noise:** ±0.3°C T, ±2% H, ±0.1 EC, ±0.1 pH
- **Actuator noise:** ±5% D_mist, ±0.3s spray delay
- **Extreme weather events:** extreme heat/cold, drought, storm, heat wave, cold snap, rain

## Evaluation Results (2M timesteps)

| Metric | Value |
|--------|-------|
| Mean Episode Reward | 6,671 |
| Episode Length | 150 cycles |
| D_mist CV | 0.33 ✅ |
| Interval CV | 0.20 ⚠️ |
| A_valve Usage | 50.1% ✅ |

## How to Train

```bash
# Fresh training
python3 train_td3.py

# Resume from existing model
python3 train_td3.py  # Will auto-resume if model exists
```

## How to Evaluate

```bash
# Basic evaluation (5 episodes)
python3 evaluate_td3.py

# 3-day continuous evaluation
python3 evaluate_td3_3day.py

# Domain randomization evaluation
python3 evaluate_domain_randomization.py

# Plot training curves
python3 plot_td3_tensorboard.py
```

## Model Deployment

Trained model is used by `model-controller` service:
- Model path: `models/aeroponic_td3.zip`
- VecNormalize path: `models/vec_normalize_td3.pkl`
- Input: 10D state vector
- Output: `D_mist`, `interval_sec`, `A_valve`
