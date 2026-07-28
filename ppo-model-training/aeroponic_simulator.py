#!/usr/bin/env python3
"""
Aeroponic Simulator Validator - Timer-based misting cycles
Validates numerical behavior of AeroponicSimulatorEnv against documented specs.
Run: /home/almuzky/jupyter/venv/bin/python3 aeroponic_simulator.py
"""

import math
import random
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class AeroponicSimulatorEnv:
    def __init__(self):
        self.dt = 60.0  # 1 minute in seconds
        self.current_time = 0.0  # current time in seconds from episode start

        # State vector: 10D
        # [L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]
        self.state = [0.0] * 10
        self.reset()

        # Continuous misting counter for O2 model
        self.T_continuous = 0
        self.max_steps = 180
        self._step_count = 0

        # Action space bounds (timer-based cycles)
        self.D_mist_min = 120.0   # 2 minutes minimum ON
        self.D_mist_max = 240.0   # 4 minutes maximum ON
        self.interval_min = 360.0   # 6 minutes minimum OFF
        self.interval_max = 540.0   # 9 minutes maximum OFF

        # Reward weights (tuned for stable learning and growth dominance)
        self.w_growth = 25.0
        self.w_mist_cost = 0.002
        self.w_valve_cost = 0.15
        self.w_env = 0.05
        self.w_hypoxia = 0.02
        self.w_interval = 0.01

        # Reward tracking for info dict
        self.last_reward_growth = 0.0
        self.last_capture_time = -4 * 3600
        self.T_root = 24.0
        self._captured_this_step = False

        # Reward component tracking for info dict
        self._last_R_growth = 0.0
        self._last_C_resource = 0.0
        self._last_R_state = 0.0
        self._last_P_env = 0.0
        self._last_P_hypoxia = 0.0
        self._last_P_interval = 0.0
        self._last_R_efficiency = 0.0

        # Action history for diversity bonus
        self._action_history = []
        self._action_history_max = 10

        # Realistic Indonesian greenhouse parameters (dry season, July)
        # T_in: 26-30°C day, 22-24°C night
        # H_in: 70-85% day, 85-95% night
        # T_out: 28-33°C day, 23-26°C night
        # H_out: 60-75% day, 75-85% night
        self.greenhouse_base_T_in = 28.0  # daytime average
        self.greenhouse_night_T_in = 23.0  # nighttime average
        self.greenhouse_day_start = 6.0  # 06:00
        self.greenhouse_day_end = 18.0  # 18:00
        self.greenhouse_daily_swing = 6.0  # ±3°C from average
        self.curriculum_weather_scale = 1.0  # will be ramped during training

        # T_nut dynamics: passive thermal drift toward T_in
        # Time constant ~2 hours (120 minutes) for reservoir thermal inertia
        # Reference: typical 200L nutrient reservoir in greenhouse
        self.T_nut_alpha = 0.008  # drift coefficient per minute (1/120)
        self.T_nut_misting_cooling = 0.05  # cooling per minute of misting ON

    def reset(self, L_root=None):
        """Reset to initial conditions from notebook.md section 3.8
        
        Args:
            L_root: If provided, use this value as initial L_root instead of 8.0.
                    Useful for multi-day simulations where growth should carry over.
        """
        L_root_init = L_root if L_root is not None else 8.0
        self.L_root_init = L_root_init
        
        # Domain randomization for sim-to-real robustness
        # Indonesian greenhouse: T_in varies 22-32°C depending on season, time, conditions
        base_T_in = 27.0  # average tropical greenhouse temperature
        T_in = base_T_in + random.uniform(-2.0, 5.0)  # [25, 32] range
        
        H_in_base = 82.0  # average humidity
        H_in = H_in_base + random.uniform(-10.0, 10.0)  # [72, 92] range
        
        EC_base = 1.7
        EC = EC_base + random.uniform(-0.3, 0.3)  # [1.4, 2.0] range
        
        pH_base = 5.9
        pH = pH_base + random.uniform(-0.3, 0.3)  # [5.6, 6.2] range

        # T_nut starts near T_in with small random offset (reservoir thermal inertia)
        T_nut = T_in + random.uniform(-1.0, 1.0)  # starts close to air temp

        self.state = [
            L_root_init,  # L_root - carried over from previous episode for multi-day sims
            0.95,   # U_status
            T_in,   # T_in randomized for tropical greenhouse
            H_in,   # H_in randomized
            26.0,   # T_out (will be updated by dynamic profile)
            70.0,   # H_out (will be updated by dynamic profile)
            EC,     # EC randomized
            pH,     # pH randomized
            T_nut,  # T_nut randomized near T_in
            1.0     # I_day
        ]
        self.current_time = 0.0
        self.T_continuous = 0
        self._step_count = 0
        self.T_root = T_in
        self.last_reward_growth = 0.0
        self.last_capture_time = -4 * 3600
        self._captured_this_step = False
        self._last_R_growth = 0.0
        self._last_C_resource = 0.0
        self._last_R_state = 0.0
        self._last_P_env = 0.0
        self._last_P_hypoxia = 0.0
        self._last_P_interval = 0.0
        self._last_R_efficiency = 0.0
        self._action_history = []
        
        # Sensor noise parameters (realistic for greenhouse sensors)
        self.sensor_noise_T = 0.3  # ±0.3°C
        self.sensor_noise_H = 2.0  # ±2% RH
        self.sensor_noise_EC = 0.1  # ±0.1 mS/cm
        self.sensor_noise_pH = 0.1  # ±0.1 pH
        
        # Actuator noise parameters
        self.actuator_noise_D_mist = 0.05  # ±5% of commanded value
        self.actuator_noise_spray_delay = 0.3  # ±0.3s variance in spray delay
        
        # Random event parameters (initialized to no events)
        self.heat_wave_intensity = 0.0
        self.cold_snap_intensity = 0.0
        self.rain_humidity_boost = 0.0
        self.extreme_heat_intensity = 0.0
        self.extreme_cold_intensity = 0.0
        self.drought_intensity = 0.0
        self.storm_intensity = 0.0
        self.storm_swing = 0.0
        
        # Generate random events for this episode
        self._generate_random_events()
        
        return self.state[:]
    
    def _generate_random_events(self):
        """Generate realistic random events for this episode, including extreme weather."""
        self.heat_wave_intensity = 0.0
        self.cold_snap_intensity = 0.0
        self.rain_humidity_boost = 0.0
        self.extreme_heat_intensity = 0.0
        self.extreme_cold_intensity = 0.0
        self.drought_intensity = 0.0
        self.storm_intensity = 0.0
        self.storm_swing = 0.0
        
        # Prioritize extreme events if they occur
        has_extreme = False
        
        # 5% chance of extreme heat wave (T_in +6-10°C for 4-8 hours)
        if random.random() < 0.05:
            has_extreme = True
            intensity = random.uniform(6.0, 10.0)
            duration = random.uniform(4.0, 8.0) * 3600
            start_time = random.uniform(9.0, 15.0) * 3600
            self.extreme_heat_intensity = intensity
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # 5% chance of extreme cold snap (T_in -6-10°C for 3-6 hours)
        if random.random() < 0.05:
            has_extreme = True
            intensity = random.uniform(6.0, 10.0)
            duration = random.uniform(3.0, 6.0) * 3600
            start_time = random.uniform(1.0, 5.0) * 3600
            self.extreme_cold_intensity = intensity
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # 8% chance of drought (H_in drops to 40-55%, H_out drops to 30-45% for 6-12 hours)
        if random.random() < 0.08:
            has_extreme = True
            intensity = random.uniform(0.4, 0.55)
            duration = random.uniform(6.0, 12.0) * 3600
            start_time = random.uniform(6.0, 12.0) * 3600
            self.drought_intensity = intensity
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # 6% chance of storm (H_out jumps to 95-100%, T_out swings ±3-5°C for 2-4 hours)
        if random.random() < 0.06:
            has_extreme = True
            intensity = random.uniform(0.95, 1.0)
            swing = random.uniform(3.0, 5.0)
            duration = random.uniform(2.0, 4.0) * 3600
            start_time = random.uniform(10.0, 18.0) * 3600
            self.storm_intensity = intensity
            self.storm_swing = swing
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # If no extreme event, apply normal random events
        if not has_extreme:
            # 10% chance of heat wave (T_in +3-5°C for 2-4 hours)
            if random.random() < 0.10:
                intensity = random.uniform(3.0, 5.0)
                duration = random.uniform(2.0, 4.0) * 3600
                start_time = random.uniform(10.0, 14.0) * 3600
                self.heat_wave_intensity = intensity
                self.event_start_time = start_time
                self.event_end_time = start_time + duration
            
            # 15% chance of cold snap (T_in -3-5°C for 2-3 hours)
            if random.random() < 0.15:
                intensity = random.uniform(3.0, 5.0)
                duration = random.uniform(2.0, 3.0) * 3600
                start_time = random.uniform(2.0, 5.0) * 3600
                if self.heat_wave_intensity > 0:
                    self.heat_wave_intensity = 0.0
                self.cold_snap_intensity = intensity
                self.event_start_time = start_time
                self.event_end_time = start_time + duration
            
            # 30% chance of rain (H_out +10-15% for 1-3 hours)
            if random.random() < 0.30:
                boost = random.uniform(10.0, 15.0)
                duration = random.uniform(1.0, 3.0) * 3600
                start_time = random.uniform(8.0, 16.0) * 3600
                self.rain_humidity_boost = boost
                self.event_start_time = start_time
                self.event_end_time = start_time + duration

    def _clip(self, val, lo, hi):
        return max(lo, min(hi, val))

    def _update_state_dynamics(self, is_misting_on, A_valve_active, substeps=1):
        """
        Update state variables for a given time period.
        Uses 1-minute substeps for numerical integration.
        """
        for _ in range(substeps):
            T_in = self.state[2]
            H_in = self.state[3]
            EC = self.state[6]
            pH = self.state[7]
            T_nut = self.state[8]
            T_out = self.state[4]
            H_out = self.state[5]
            T_root = self.T_root

            # H_in dynamics (section 3.4) with temperature-dependent evaporation
            # Higher T_out increases evaporation rate when misting OFF
            if is_misting_on:
                H_target = 98.0
                lam = 0.2
            else:
                H_target = H_out
                # Base decay 0.02 + temperature effect up to +0.03
                T_evap_factor = max(0.0, (T_out - 20.0) / 15.0)  # 0 at 20C, 1.0 at 35C
                lam = 0.02 + 0.03 * T_evap_factor
            H_in = H_target - (H_target - H_in) * math.exp(-lam)
            
            # Apply drought effect: H_in drops toward H_in_target
            if hasattr(self, 'drought_intensity') and self.drought_intensity > 0:
                H_in_target = max(40.0, H_in * 0.6)
                H_in = H_in + (H_in_target - H_in) * 0.1

            # T_root dynamics (section 3.2)
            if is_misting_on:
                T_root = T_root - 0.3
            else:
                T_root = T_root + (T_in - T_root) * 0.05
            T_root = self._clip(T_root, 10.0, 35.0)

            # Bottom zone valve spraying effects (section 3.5)
            if A_valve_active:
                H_in = min(100.0, H_in + 2.0)
                T_root = max(10.0, T_root - 0.1)
                EC = 1.5
                pH = 6.0
                self.T_continuous = max(0, self.T_continuous - 1)

            # EC correction during misting: nutrient dilution effect
            # Misting introduces fresh water, slightly diluting EC back toward target
            if is_misting_on:
                EC += (1.6 - EC) * 0.005  # gentle drift toward target EC=1.6
                # pH correction during misting: fresh nutrient solution stabilizes pH
                pH += (6.0 - pH) * 0.003  # gentle drift toward target pH=6.0

            # EC/pH dynamics (section 3.5)
            if not is_misting_on and H_in < 85.0:
                EC += 0.00033

            # pH drift: +0.00017 per minute + positive stochastic perturbation
            pH += 0.00017
            pH_perturbation = 0.00017 * max(1.0, abs(self._normal(1.0, 0.3)))
            pH += pH_perturbation - 0.00017

            # Clip EC/pH to physical-ish ranges for sanity
            EC = self._clip(EC, 0.5, 3.5)
            pH = self._clip(pH, 4.0, 9.0)

            # Realistic Indonesian greenhouse T_out/H_out profiles
            # T_out: slightly warmer than T_in during day, cooler at night
            # H_out: inversely correlated with temperature ( drier when hot)
            hour = self.current_time / 3600.0  # hours since episode start
            
            # Get base T_in for this hour (with daily cycle)
            day_start = self.greenhouse_day_start
            day_end = self.greenhouse_day_end
            if day_start <= hour % 24 < day_end:
                # Daytime: 26-30°C
                T_in_base = self.greenhouse_base_T_in + self._normal(0.0, 0.5)
            else:
                # Nighttime: 22-24°C
                T_in_base = self.greenhouse_night_T_in + self._normal(0.0, 0.3)
            
            # T_out follows similar pattern but slightly warmer during day
            if day_start <= hour % 24 < day_end:
                T_out_base = T_in_base + 2.0 + self._normal(0.0, 0.5 * self.curriculum_weather_scale)
            else:
                T_out_base = T_in_base + 1.0 + self._normal(0.0, 0.3)
            
            # H_out inversely correlated with temperature
            if day_start <= hour % 24 < day_end:
                H_out_base = 70.0 - (T_out_base - 28.0) * 2.0 + self._normal(0.0, 2.0 * self.curriculum_weather_scale)
            else:
                H_out_base = 80.0 + self._normal(0.0, 2.0)
            
            # Apply random events (heat waves, cold snaps, rain, extreme weather)
            event_multiplier = 1.0
            if hasattr(self, 'heat_wave_intensity') and self.heat_wave_intensity > 0:
                T_out_base += self.heat_wave_intensity
                T_in_base += self.heat_wave_intensity * 0.8
            if hasattr(self, 'cold_snap_intensity') and self.cold_snap_intensity > 0:
                T_out_base -= self.cold_snap_intensity
                T_in_base -= self.cold_snap_intensity * 0.8
            if hasattr(self, 'rain_humidity_boost') and self.rain_humidity_boost > 0:
                H_out_base += self.rain_humidity_boost
            
            # Extreme weather events
            if hasattr(self, 'extreme_heat_intensity') and self.extreme_heat_intensity > 0:
                T_out_base += self.extreme_heat_intensity
                T_in_base += self.extreme_heat_intensity * 0.9
            if hasattr(self, 'extreme_cold_intensity') and self.extreme_cold_intensity > 0:
                T_out_base -= self.extreme_cold_intensity
                T_in_base -= self.extreme_cold_intensity * 0.9
            if hasattr(self, 'drought_intensity') and self.drought_intensity > 0:
                H_out_base = H_out_base * self.drought_intensity
                H_in_target = max(40.0, H_in * 0.6)
            if hasattr(self, 'storm_intensity') and self.storm_intensity > 0:
                H_out_base = H_out_base + (self.storm_intensity * 100.0 - H_out_base) * 0.8
                T_out_base += random.uniform(-self.storm_swing, self.storm_swing)
            
            T_out = self._clip(T_out_base, 15.0, 38.0)
            H_out = self._clip(H_out_base, 40.0, 100.0)
            
            # Update T_in with daily cycle (affected by events)
            T_in = self._clip(T_in_base, 18.0, 36.0)

            # I_day update based on time of day
            hour = int((6 + self.current_time / 3600.0) % 24)
            I_day = 1.0 if 6 <= hour < 18 else 0.0

            # T_nut dynamics: passive thermal drift toward T_in
            # Reservoir has large thermal inertia, time constant ~2 hours
            # Misting provides slight cooling effect
            T_nut_drift = (T_in - T_nut) * self.T_nut_alpha
            if is_misting_on:
                T_nut_drift -= self.T_nut_misting_cooling
            T_nut = T_nut + T_nut_drift
            T_nut = self._clip(T_nut, 18.0, 30.0)  # physical bounds

            # L_root and U_status update ONLY at capture times (section 3.7)
            # Capture every 4 hours since episode start: 0, 4h, 8h, 12h, 16h, 20h
            do_capture = False
            next_capture_time = self.last_capture_time + 4 * 3600
            if self.current_time >= next_capture_time - 1e-6:
                do_capture = True

            if do_capture:
                self._captured_this_step = True
                L_root = self.state[0]
                r_step = 0.00015
                K = 300.0
                f_Hin = min(1.0, H_in / 90.0)
                f_O2 = max(0.2, 1.0 - 0.08 * max(0, self.T_continuous - 3))
                if 10 <= T_root <= 20:
                    f_T = 1.0
                elif T_root < 10:
                    f_T = max(0.3, 1.0 - (10 - T_root) * 0.1)
                else:
                    f_T = max(0.3, 1.0 - (T_root - 20) * 0.15)
                day_mult = 1.2 if I_day == 1.0 else 0.6

                delta_l = r_step * 240.0 * self.L_root_init * (1 - self.L_root_init / K) * f_Hin * f_O2 * f_T * day_mult
                new_L_root = max(0.0, L_root + delta_l)
                captured_growth = new_L_root - L_root
                L_root = new_L_root

                U_status = self._clip(self.state[1] + self._normal(0.0, 0.01), 0.0, 1.0)

                self.state[0] = L_root
                self.state[1] = U_status
                self.last_capture_time = self.current_time
                self.last_reward_growth = self.w_growth * captured_growth

            # Persist T_root
            self.T_root = T_root

            # Update remaining state variables (true values, no noise yet)
            self.state[2] = T_in
            self.state[3] = H_in
            self.state[4] = T_out
            self.state[5] = H_out
            self.state[6] = EC
            self.state[7] = pH
            self.state[8] = T_nut
            self.state[9] = I_day

            # Advance simulation time by 1 minute
            self.current_time += self.dt

    def step(self, action):
        """
        Execute one timer-based misting cycle.
        action = [D_mist, interval_sec, A_valve]
        D_mist: ON duration in seconds (120-240s, already in physical range)
        interval_sec: OFF duration in seconds (360-540s, already in physical range)
        A_valve: bottom valve activation [0, 1]
        
        NOTE: Actions are expected in raw physical units. The Gymnasium wrapper
        handles mapping from normalized [-1, 1] to physical ranges.
        Do NOT rescale here — previous double-scaling bug caused agent actions
        to always saturate at maximum.
        """
        # Accept raw physical values directly (no rescaling)
        D_mist_raw = float(action[0])
        interval_raw = float(action[1])
        
        # Apply actuator noise to actions (realistic hardware)
        D_mist_noisy = D_mist_raw * (1.0 + random.uniform(-self.actuator_noise_D_mist, self.actuator_noise_D_mist))
        interval_noisy = interval_raw * (1.0 + random.uniform(-self.actuator_noise_D_mist * 0.5, self.actuator_noise_D_mist * 0.5))
        
        D_mist = self._clip(D_mist_noisy, self.D_mist_min, self.D_mist_max)
        interval_sec = self._clip(interval_noisy, self.interval_min, self.interval_max)
        A_valve = 1.0 if float(action[2]) >= 0.5 else 0.0
        A_valve_active = A_valve >= 0.5

        # Add variance to spray delay (±0.3s)
        actual_spray_delay = 1.5 + random.uniform(-self.actuator_noise_spray_delay, self.actuator_noise_spray_delay)
        D_effective = max(0.0, D_mist - actual_spray_delay)
        self._captured_this_step = False

        # ON phase
        on_substeps = int(D_mist / 60.0)  # 1-minute substeps
        if on_substeps == 0:
            on_substeps = 1
        self.T_continuous += on_substeps
        self._update_state_dynamics(is_misting_on=True, A_valve_active=A_valve_active, substeps=on_substeps)

        # Save T_continuous before reset for hypoxia reward
        T_continuous_for_reward = self.T_continuous

        # OFF phase
        off_substeps = int(interval_sec / 60.0)
        if off_substeps == 0:
            off_substeps = 1
        self.T_continuous = 0
        self._update_state_dynamics(is_misting_on=False, A_valve_active=False, substeps=off_substeps)

        # Update action history for diversity bonus
        self._action_history.append([D_mist, interval_sec, A_valve])
        if len(self._action_history) > self._action_history_max:
            self._action_history.pop(0)

        T_continuous_snapshot = T_continuous_for_reward

        # Compute reward for this cycle using processed actions
        reward = self._compute_reward([D_mist, interval_sec, A_valve], T_continuous=T_continuous_for_reward)
        
        # Survival bonus: reward agent for each step it stays alive
        # This incentivizes maintaining healthy state throughout the episode
        reward += 0.5
        
        # Step counting for 180-step milestone + completion tracking
        self._step_count += 1
        if self._step_count == self.max_steps:
            reward += 10.0  # full 180-step completion bonus
        
        # Clip reward for training stability
        reward = self._clip(reward, -50.0, 50.0)

        # Check termination — use slightly relaxed bounds to reduce
        # premature termination from sensor noise + natural drift
        pH_val = self.state[7]
        EC_val = self.state[6]
        terminated = (pH_val < 4.5 or pH_val > 8.5 or EC_val < 0.5 or EC_val > 3.0)
        truncated = self._step_count >= self.max_steps

        # Episode completion bonus: reward agent for surviving the full episode
        if truncated and not terminated:
            reward += 10.0  # significant bonus for full episode survival

        # Strong early termination penalty: losing remaining survival bonus + growth
        if terminated and not truncated:
            remaining_steps = max(1, self.max_steps - self._step_count)
            reward -= 0.5 * remaining_steps  # lost survival bonus
            reward -= self.w_growth * 5.0     # additional growth penalty

        # Robustness
        if not math.isfinite(reward):
            reward = -1e6
        if any(not math.isfinite(v) for v in self.state):
            terminated = True

        # Apply sensor noise to create noisy observations (realistic)
        # True state is in self.state, create noisy version for agent
        true_state = self.state[:]
        obs_state = true_state[:]
        
        # Add sensor noise to observations
        obs_state[2] = self._clip(true_state[2] + random.uniform(-self.sensor_noise_T, self.sensor_noise_T), 15.0, 35.0)  # T_in
        obs_state[3] = self._clip(true_state[3] + random.uniform(-self.sensor_noise_H, self.sensor_noise_H), 20.0, 100.0)  # H_in
        obs_state[4] = self._clip(true_state[4] + random.uniform(-self.sensor_noise_T, self.sensor_noise_T), 15.0, 38.0)  # T_out
        obs_state[5] = self._clip(true_state[5] + random.uniform(-self.sensor_noise_H, self.sensor_noise_H), 40.0, 100.0)  # H_out
        obs_state[6] = self._clip(true_state[6] + random.uniform(-self.sensor_noise_EC, self.sensor_noise_EC), 0.5, 3.5)  # EC
        obs_state[7] = self._clip(true_state[7] + random.uniform(-self.sensor_noise_pH, self.sensor_noise_pH), 4.0, 9.0)  # pH
        obs_state[8] = self._clip(true_state[8] + random.uniform(-self.sensor_noise_T * 0.5, self.sensor_noise_T * 0.5), 18.0, 30.0)  # T_nut
        
        # Update state with noisy observations (this is what agent sees)
        self.state = obs_state

        info = {
            'D_effective': D_effective,
            'T_continuous': self.T_continuous,
            'O2_status': max(0.2, 1.0 - 0.08 * max(0, T_continuous_snapshot - 3)),
            'reward_growth': self._last_R_growth,
            'reward_resource': self._last_C_resource,
            'reward_state': self._last_R_state,
            'reward_env': self._last_P_env,
            'reward_hypoxia': self._last_P_hypoxia,
            'reward_interval': self._last_P_interval,
            'reward_efficiency': self._last_R_efficiency,
            'captured': self._captured_this_step,
            'T_in': self.state[2],
            'T_out': self.state[4],
            'H_out': self.state[5],
        }

        return self.state[:], reward, terminated, truncated, info

    def _compute_reward(self, action, T_continuous=None):
        """Compute total reward R(t) from section 2.3"""
        D_mist, interval_sec, A_valve = action

        if T_continuous is None:
            T_continuous = self.T_continuous

        R_growth = self.last_reward_growth

        # Resource cost: only charge per misting ON event, not per second.
        # This prevents the agent from minimizing D_mist just to save cost.
        C_resource = self.w_valve_cost * (1.0 if A_valve >= 0.5 else 0.0)

        # Environmental penalties
        pH = self.state[7]
        EC = self.state[6]
        H_in = self.state[3]
        dev_pH = abs(pH - 6.0) if (pH < 5.5 or pH > 6.5) else 0.0
        dev_EC = abs(EC - 1.6) if (EC < 1.2 or EC > 2.0) else 0.0
        dev_Hin = max(0.0, 85.0 - H_in) if H_in < 85.0 else 0.0
        P_env = self.w_env * (dev_pH + dev_EC + dev_Hin)

        O2_status = max(0.2, 1.0 - 0.08 * max(0, T_continuous - 3))
        P_hypoxia = self.w_hypoxia * max(0.0, 1.0 - O2_status)

        # State-based reward: encourage healthy ranges
        T_root = self.T_root

        R_state = 0.0
        if 5.5 <= pH <= 6.5:
            R_state += 0.05
        elif pH < 5.5:
            R_state -= 0.2 * (5.5 - pH)
        else:
            R_state -= 0.1 * (pH - 6.5)

        if 1.2 <= EC <= 2.0:
            R_state += 0.05
        elif EC < 1.2:
            R_state -= 0.2 * (1.2 - EC)
        else:
            R_state -= 0.1 * (EC - 2.0)

        if H_in >= 85.0:
            R_state += 0.05
        else:
            R_state -= 0.1 * (85.0 - H_in) / 10.0

        if 10.0 <= T_root <= 20.0:
            R_state += 0.1
        elif T_root < 10.0:
            R_state -= 0.2 * (10.0 - T_root)
        else:
            R_state -= 0.1 * (T_root - 20.0)

        if O2_status >= 0.6:
            R_state += 0.05
        else:
            R_state -= 0.2 * (0.6 - O2_status)

        # Action shaping: reward effective misting duration, penalize too-short intervals
        if D_mist >= 150.0:
            R_state += 0.3
        elif D_mist < 130.0:
            R_state -= 1.0

        if 390.0 <= interval_sec <= 480.0:
            R_state += 0.2
        elif interval_sec < 360.0:
            R_state -= 0.5

        P_interval = self.w_interval * (1.0 if interval_sec > 520 else 0.0)

        P_diversity = 0.0
        if len(self._action_history) >= 5:
            recent_actions = np.array(self._action_history[-10:])
            d_mist_std = np.std(recent_actions[:, 0])
            interval_std = np.std(recent_actions[:, 1])
            a_valve_toggles = sum(1 for i in range(1, len(recent_actions)) if recent_actions[i, 2] != recent_actions[i-1, 2])

            if d_mist_std > 10.0:
                P_diversity += 2.0
            if interval_std > 20.0:
                P_diversity += 1.0
            if a_valve_toggles >= 2:
                P_diversity += 0.5

        R_efficiency = 0.0
        if P_env < 1.0 and P_hypoxia == 0.0:
            if A_valve == 0.0:
                R_efficiency += 0.05
            if D_mist <= 150.0:
                R_efficiency += 0.03
            if interval_sec >= 480.0:
                R_efficiency += 0.02

        R_total = R_growth + R_state + P_diversity + R_efficiency - C_resource - P_env - P_hypoxia - P_interval

        self._last_R_growth = R_growth
        self._last_C_resource = C_resource
        self._last_R_state = R_state
        self._last_P_env = P_env
        self._last_P_hypoxia = P_hypoxia
        self._last_P_interval = P_interval
        self._last_R_efficiency = R_efficiency

        return R_total

    @staticmethod
    def _normal(mu, sigma):
        """Box-Muller normal variate"""
        u1 = random.random()
        u2 = random.random()
        z = math.sqrt(-2.0 * math.log(u1 + 1e-12)) * math.cos(2.0 * math.pi * u2)
        return mu + sigma * z


def run_validation():
    env = AeroponicSimulatorEnv()
    print("=" * 80)
    print("AEROPONIC SIMULATOR NUMERICAL VALIDATION (TIMER-BASED)")
    print("=" * 80)

    print("\n[TEST 1] Initial state matches notebook section 3.8")
    init = env.reset()
    # Indonesian greenhouse: T_in [25,32], H_in [72,92], EC [1.4,2.0], pH [5.6,6.2]
    # T_nut starts near T_in with ±1°C random offset (passive thermal drift)
    expected_ranges = [
        (8.0, 8.0, 0.01),      # L_root: exact
        (0.95, 0.95, 0.01),    # U_status: exact
        (25.0, 32.0, None),    # T_in: tropical greenhouse range
        (72.0, 92.0, None),    # H_in: tropical range
        (26.0, 26.0, 0.01),    # T_out: exact initial
        (70.0, 70.0, 0.01),    # H_out: exact initial
        (1.4, 2.0, None),      # EC: tropical range
        (5.6, 6.2, None),      # pH: tropical range
        (24.0, 33.0, None),    # T_nut: near T_in (±1°C, T_in max 32°C)
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
    while not env.current_time >= env.episode_time - 1:
        action = [180.0, 540.0, 0.0]
        _, reward, terminated, truncated, info = env.step(action)
        cycles += 1
        if terminated or truncated:
            break
    print(f"  Cycles completed: {cycles}")
    print(f"  Final time: {env.current_time:.0f}s / {env.episode_time:.0f}s")
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
    Run continuous multi-day simulation without episode reset.
    
    This allows observing the full growth trajectory from day 1 to N
    without resetting L_root or other state variables.
    
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
    state = env.reset()  # Single reset at start, then continuous
    
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
    
    for day in range(1, days + 1):
        # Run one full day (until truncated at 86400s)
        while True:
            state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            
            if terminated:
                if verbose:
                    print(f"Day {day}: EARLY TERMINATED at {env.current_time:.0f}s")
                    print(f"  EC={state[6]:.4f}, pH={state[7]:.4f}, H_in={state[3]:.2f}%")
                    print(f"  Final L_root={state[0]:.4f} cm")
                return history
            if truncated:
                break
        
        # Record daily snapshot
        history['day'].append(day)
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
        
        if verbose and (day % 7 == 0 or day == 1):
            growth = state[0] - history['L_root'][0]
            print(f"Day {day:3d}: L_root={state[0]:.4f} cm (growth: +{growth:.4f} cm), "
                  f"EC={state[6]:.2f}, pH={state[7]:.2f}, "
                  f"T_in={state[2]:.1f}C, T_nut={state[8]:.1f}C")
    
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


def run_multi_day_simulation(days=90, action=None, verbose=True):
    """
    Run continuous multi-day simulation without episode reset.
    
    This allows observing the full growth trajectory from day 1 to N
    without resetting L_root or other state variables.
    
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
    state = env.reset()  # Single reset at start, then continuous
    
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
    
    for day in range(1, days + 1):
        # Run one full day (until truncated at 86400s)
        while True:
            state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            
            if terminated:
                if verbose:
                    print(f"Day {day}: EARLY TERMINATED at {env.current_time:.0f}s")
                    print(f"  EC={state[6]:.4f}, pH={state[7]:.4f}, H_in={state[3]:.2f}%")
                    print(f"  Final L_root={state[0]:.4f} cm")
                return history
            if truncated:
                break
        
        # Record daily snapshot
        history['day'].append(day)
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
        
        if verbose and (day % 7 == 0 or day == 1):
            growth = state[0] - history['L_root'][0]
            print(f"Day {day:3d}: L_root={state[0]:.4f} cm (growth: +{growth:.4f} cm), "
                  f"EC={state[6]:.2f}, pH={state[7]:.2f}, "
                  f"T_in={state[2]:.1f}C, T_nut={state[8]:.1f}C")
    
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
    Run 90-day continuous simulation using trained PPO agent.
    
    Each episode is 24h, so we run 90 episodes, carrying over L_root across episodes.
    
    Args:
        days: Number of days to simulate
        deterministic: If True, use deterministic actions; if False, stochastic
        
    Returns:
        dict with history of state evolution per capture point
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    except ImportError:
        print("ERROR: stable_baselines3 not installed. Cannot run PPO simulation.")
        return None
    
    base_dir = '/home/almuzky/TA/Microservices/services/ml-control'
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
    
    gym_env = AeroponicGymnasiumEnv()
    vec_env = DummyVecEnv([lambda: gym_env])
    vec_norm = VecNormalize.load(vec_norm_path, vec_env)
    vec_norm.training = False
    vec_norm.norm_reward = False
    
    model = PPO.load(model_path, env=vec_norm)
    
    print("\n" + "=" * 80)
    print(f"PPO 90-DAY CONTINUOUS SIMULATION ({days} days)")
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
    current_episode = 0
    
    L_root_init = L_root_carry
    episode_actions = {'D_mist': [], 'interval_sec': [], 'A_valve': []}
    
    while current_episode < days:
        gym_env_local = AeroponicGymnasiumEnv()
        vec_env_local = DummyVecEnv([lambda: gym_env_local])
        vec_norm_local = VecNormalize.load(vec_norm_path, vec_env_local)
        vec_norm_local.training = False
        vec_norm_local.norm_reward = False
        
        raw_obs, _ = gym_env_local.reset(L_root=L_root_carry)
        obs = vec_norm_local.normalize_obs(raw_obs.reshape(1, -1))
        
        episode_terminated = False
        last_action = None
        
        while not episode_terminated:
            # Read true state BEFORE the step so we don't get reset state
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
            action = np.clip(action, vec_env_local.action_space.low, vec_env_local.action_space.high)
            last_action = action
            
            obs, reward, done, info = vec_norm_local.step(action.reshape(1, -1))
            terminated = bool(np.any(done)) if isinstance(done, np.ndarray) else bool(done)
            info0 = info[0] if isinstance(info, list) else info
            current_O2 = info0.get('O2_status', max(0.2, 1.0 - 0.08 * max(0, pre_O2 - 3)))
            
            if terminated:
                episode_terminated = True
                
                history['day'].append(current_episode + 1)
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
                if last_action is not None:
                    episode_actions['D_mist'].append(last_action[0])
                    episode_actions['interval_sec'].append(last_action[1])
                    episode_actions['A_valve'].append(last_action[2])
                
                L_root_carry = pre_L_root
                total_growth += pre_L_root - L_root_init
                current_episode += 1
                
                print(f"Day {current_episode:3d}: L_root={pre_L_root:.4f} cm, "
                      f"H_in={pre_H_in:.1f}%, EC={pre_EC:.2f}, pH={pre_pH:.2f}, "
                      f"O2={current_O2:.2f}, D_mist={last_action[0]:.0f}s, interval={last_action[1]:.0f}s, "
                      f"growth_this_ep={pre_L_root - L_root_init:.4f} cm")
    
    history['D_mist'] = episode_actions['D_mist']
    history['interval_sec'] = episode_actions['interval_sec']
    history['A_valve'] = episode_actions['A_valve']
    
    final_L = L_root_carry
    print(f"\nFinal L_root: {final_L:.4f} cm")
    print(f"Total growth over {days} days: {final_L - L_root_init:.4f} cm")
    print(f"Average growth per day: {(final_L - L_root_init)/days:.4f} cm/day")
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
