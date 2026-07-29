#!/usr/bin/env python3
"""
Aeroponic Simulator - Core Environment Only
Timer-based misting cycles with physics-based state dynamics.
"""

import math
import random
import numpy as np


class AeroponicSimulatorEnv:
    def __init__(self):
        self.dt = 60.0  # 1 minute in seconds
        self.current_time = 0.0  # current time in seconds from episode start

        # State vector: 10D
        # [L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]
        self.state = [0.0] * 10

        # Continuous misting counter for O2 model
        self.T_continuous = 0
        self._step_count = 0
        self._time_remainder = 0.0
        self.episode_duration = 86400.0  # 24 hours in seconds for training
        self._episode_start_time = 0.0
        self._mode = 'training'  # 'training' or 'simulation'

        # Action space bounds (realistic ranges: 2-10 minutes)
        self.D_mist_min = 120.0   # 2 minutes minimum ON
        self.D_mist_max = 600.0   # 10 minutes maximum ON
        self.interval_min = 120.0   # 2 minutes minimum OFF
        self.interval_max = 600.0   # 10 minutes maximum OFF

        # Reward weights (tuned for realistic penalty hierarchy)
        self.w_growth = 10.0
        self.w_mist_cost = 0.002
        self.w_valve_cost = 0.15
        self.w_env = 0.05
        self.w_hypoxia = 5.0
        self.w_interval = 1.0
        self.w_status = 10.0

        # Reward tracking for info dict
        self.last_reward_growth = 0.0
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
        self._last_P_shrink = 0.0
        self._last_P_death = 0.0
        self._last_P_extreme = 0.0

        # Action history for diversity bonus
        self._action_history = []
        self._action_history_max = 10
        self._no_more_events = False  # Flag to stop event regeneration
        
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
        
        # Cached climate base values (updated per hour, not per substep)
        self._cached_T_in_base = self.greenhouse_base_T_in
        self._cached_T_out_base = self._cached_T_in_base + 2.0
        self._cached_H_out_base = 70.0
        self._last_base_update_hour = -1

        # T_nut dynamics: passive thermal drift toward T_in
        # Time constant ~2 hours (120 minutes) for reservoir thermal inertia
        # Reference: typical 200L nutrient reservoir in greenhouse
        self.T_nut_alpha = 0.008  # drift coefficient per minute (1/120)
        self.T_nut_misting_cooling = 0.05  # cooling per minute of misting ON
        
        # Initialize state after all attributes are set
        self.reset()

    def reset(self, L_root=None, continuous=False, mode='training', episode_duration=None):
        """Reset to initial conditions based on aeroponic research.
        
        Args:
            L_root: Initial root length. If None, uses default 8.0.
            continuous: If True, preserve time and climate state for multi-day simulation.
            mode: 'training' for 24h episodes with full reset, 
                  'simulation' for continuous multi-day simulation.
            episode_duration: Override episode duration in seconds. If None, uses default.
        """
        L_root_init = L_root if L_root is not None else 8.0
        self.L_root_init = L_root_init
        self._mode = mode
        
        if not continuous:
            # Indonesian daytime initialization (episode starts at 06:00)
            T_in = random.uniform(26.0, 30.0)
            H_in = random.uniform(70.0, 85.0)
            EC = random.uniform(1.4, 2.0)
            pH = random.uniform(5.6, 6.2)
            T_nut = random.uniform(24.0, 33.0)

            self.state = [
                L_root_init,
                0.95,
                T_in,
                H_in,
                random.uniform(28.0, 33.0),
                random.uniform(60.0, 75.0),
                EC,
                pH,
                T_nut,
                1.0
            ]
            self.current_time = 0.0
            self._time_remainder = 0.0
            self._episode_start_time = 0.0
            self.T_root = T_in
            
            # Reset cached climate values to match initial state
            self._cached_T_in_base = T_in
            self._cached_T_out_base = self.state[4]
            self._cached_H_out_base = self.state[5]
            self._last_base_update_hour = 0
            
            # Random event parameters (initialized to no events)
            self.heat_wave_intensity = 0.0
            self.cold_snap_intensity = 0.0
            self.rain_humidity_boost = 0.0
            self.extreme_heat_intensity = 0.0
            self.extreme_cold_intensity = 0.0
            self.drought_intensity = 0.0
            self.storm_intensity = 0.0
            self.storm_swing = 0.0
            self.event_start_time = 0.0
            self.event_end_time = 0.0
            
            # Generate random events for this episode
            self._generate_random_events()
            self._no_more_events = True  # Don't regenerate events mid-episode in training mode
            
            # Sensor noise parameters (realistic for greenhouse sensors)
            self.sensor_noise_T = 0.3  # ±0.3°C
            self.sensor_noise_H = 2.0  # ±2% RH
            self.sensor_noise_EC = 0.1  # ±0.1 mS/cm
            self.sensor_noise_pH = 0.1  # ±0.1 pH
            
            # Actuator noise parameters
            self.actuator_noise_D_mist = 0.05  # ±5% of commanded value
            self.actuator_noise_spray_delay = 0.3  # ±0.3s variance in spray delay
            
            self._prev_L_root = L_root_init
            self._prev_U_status = self.state[1]
        else:
            # Continuous/simulation mode: preserve time, climate, and state
            self.state[0] = L_root_init
            self._prev_L_root = L_root_init
            self._prev_U_status = self.state[1]
            self._episode_start_time = self.current_time
            self._time_remainder = 0.0
            self._no_more_events = False  # Allow event regeneration in continuous mode
            
            # Reset event state for new episode
            self.heat_wave_intensity = 0.0
            self.cold_snap_intensity = 0.0
            self.rain_humidity_boost = 0.0
            self.extreme_heat_intensity = 0.0
            self.extreme_cold_intensity = 0.0
            self.drought_intensity = 0.0
            self.storm_intensity = 0.0
            self.storm_swing = 0.0
            self.event_start_time = 0.0
            self.event_end_time = 0.0
            self._generate_random_events()
            
            # Reset milestone flags for new episode in continuous mode
            self._milestone_3h = False
            self._milestone_6h = False
            self._milestone_12h = False
            self._milestone_18h = False
        
        self.T_continuous = 0
        self._step_count = 0
        self.last_reward_growth = 0.0
        
        # Set episode duration based on mode or explicit override
        if episode_duration is not None:
            self.episode_duration = episode_duration
        elif mode == 'training':
            self.episode_duration = 86400.0  # 24 hours in seconds
        else:
            self.episode_duration = 86400.0  # default 24h for simulation episodes
        
        # Reset milestone flags for new episode
        self._milestone_3h = False
        self._milestone_6h = False
        self._milestone_12h = False
        self._milestone_18h = False
        
        self._captured_this_step = False
        self._last_R_growth = 0.0
        self._last_C_resource = 0.0
        self._last_R_state = 0.0
        self._last_P_env = 0.0
        self._last_P_hypoxia = 0.0
        self._last_P_interval = 0.0
        self._last_R_efficiency = 0.0
        self._last_P_shrink = 0.0
        self._last_P_death = 0.0
        self._last_P_extreme = 0.0
        
        # Preserve action history in continuous mode for consistent diversity bonus
        if not continuous:
            self._action_history = []
        
        return self.state[:]

    def _is_event_active(self, event_start_time, event_end_time):
        """Check if current time is within event window."""
        return event_start_time <= self.current_time < event_end_time

    def _generate_random_events(self):
        """Generate realistic random events for this episode, including extreme weather.
        
        Resets all existing events and generates exactly one new event.
        In continuous mode, this is called repeatedly to maintain event variety.
        """
        # Reset all existing events first
        self.heat_wave_intensity = 0.0
        self.cold_snap_intensity = 0.0
        self.rain_humidity_boost = 0.0
        self.extreme_heat_intensity = 0.0
        self.extreme_cold_intensity = 0.0
        self.drought_intensity = 0.0
        self.storm_intensity = 0.0
        self.storm_swing = 0.0
        self.event_start_time = 0.0
        self.event_end_time = 0.0
        
        # Prioritize extreme events if they occur
        has_extreme = False
        
        # 5% chance of extreme heat wave (T_in +6-10°C for 4-8 hours)
        if random.random() < 0.05:
            has_extreme = True
            intensity = random.uniform(6.0, 10.0)
            duration = random.uniform(4.0, 8.0) * 3600
            start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
            self.extreme_heat_intensity = intensity
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # 5% chance of extreme cold snap (T_in -6-10°C for 3-6 hours)
        if random.random() < 0.05 and not has_extreme:
            has_extreme = True
            intensity = random.uniform(6.0, 10.0)
            duration = random.uniform(3.0, 6.0) * 3600
            start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
            self.extreme_cold_intensity = intensity
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # 8% chance of drought (H_in drops to 40-55%, H_out drops to 30-45% for 6-12 hours)
        if random.random() < 0.08 and not has_extreme:
            has_extreme = True
            intensity = random.uniform(0.4, 0.55)
            duration = random.uniform(6.0, 12.0) * 3600
            start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
            self.drought_intensity = intensity
            self.event_start_time = start_time
            self.event_end_time = start_time + duration
        
        # 6% chance of storm (H_out jumps to 95-100%, T_out swings ±3-5°C for 2-4 hours)
        if random.random() < 0.06 and not has_extreme:
            has_extreme = True
            intensity = random.uniform(0.95, 1.0)
            swing = random.uniform(3.0, 5.0)
            duration = random.uniform(2.0, 4.0) * 3600
            start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
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
                start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
                self.heat_wave_intensity = intensity
                self.event_start_time = start_time
                self.event_end_time = start_time + duration
            
            # 15% chance of cold snap (T_in -3-5°C for 2-3 hours)
            if random.random() < 0.15 and self.heat_wave_intensity == 0.0:
                intensity = random.uniform(3.0, 5.0)
                duration = random.uniform(2.0, 3.0) * 3600
                start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
                self.cold_snap_intensity = intensity
                self.event_start_time = start_time
                self.event_end_time = start_time + duration
            
            # 30% chance of rain (H_out +10-15% for 1-3 hours)
            if random.random() < 0.30 and self.heat_wave_intensity == 0.0 and self.cold_snap_intensity == 0.0:
                boost = random.uniform(10.0, 15.0)
                duration = random.uniform(1.0, 3.0) * 3600
                start_time = self.current_time + random.uniform(0.0, 2.0) * 3600
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
            if hasattr(self, 'drought_intensity') and self.drought_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
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
            current_hour = self.current_time / 3600.0  # hours since episode start
            
            # Update base climate values only when hour changes (not every substep)
            if int(current_hour) != self._last_base_update_hour:
                self._last_base_update_hour = int(current_hour)
                
                # Get base T_in for this hour (with daily cycle)
                hour_of_day = int((6 + current_hour) % 24)
                if 6 <= hour_of_day < 18:
                    # Daytime: 26-30°C
                    self._cached_T_in_base = self.greenhouse_base_T_in + self._normal(0.0, 0.5)
                else:
                    # Nighttime: 22-24°C
                    self._cached_T_in_base = self.greenhouse_night_T_in + self._normal(0.0, 0.3)
                
                # T_out follows similar pattern but slightly warmer during day
                if 6 <= hour_of_day < 18:
                    self._cached_T_out_base = self._cached_T_in_base + 2.0 + self._normal(0.0, 0.5 * self.curriculum_weather_scale)
                else:
                    self._cached_T_out_base = self._cached_T_in_base + 1.0 + self._normal(0.0, 0.3)
                
                # H_out inversely correlated with temperature
                if 6 <= hour_of_day < 18:
                    self._cached_H_out_base = 70.0 - (self._cached_T_out_base - 28.0) * 2.0 + self._normal(0.0, 2.0 * self.curriculum_weather_scale)
                else:
                    self._cached_H_out_base = 80.0 + self._normal(0.0, 2.0)
            
            T_in_base = self._cached_T_in_base
            T_out_base = self._cached_T_out_base
            H_out_base = self._cached_H_out_base
            
            # Apply random events (heat waves, cold snaps, rain, extreme weather)
            event_multiplier = 1.0
            if hasattr(self, 'heat_wave_intensity') and self.heat_wave_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                T_out_base += self.heat_wave_intensity
                T_in_base += self.heat_wave_intensity * 0.8
            if hasattr(self, 'cold_snap_intensity') and self.cold_snap_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                T_out_base -= self.cold_snap_intensity
                T_in_base -= self.cold_snap_intensity * 0.8
            if hasattr(self, 'rain_humidity_boost') and self.rain_humidity_boost > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                H_out_base += self.rain_humidity_boost
            
            # Extreme weather events
            if hasattr(self, 'extreme_heat_intensity') and self.extreme_heat_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                T_out_base += self.extreme_heat_intensity
                T_in_base += self.extreme_heat_intensity * 0.9
            if hasattr(self, 'extreme_cold_intensity') and self.extreme_cold_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                T_out_base -= self.extreme_cold_intensity
                T_in_base -= self.extreme_cold_intensity * 0.9
            if hasattr(self, 'drought_intensity') and self.drought_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                H_out_base = H_out_base * self.drought_intensity
                H_in_target = max(40.0, H_in * 0.6)
                H_in = H_in + (H_in_target - H_in) * 0.1
            if hasattr(self, 'storm_intensity') and self.storm_intensity > 0 and self._is_event_active(self.event_start_time, self.event_end_time):
                H_out_base = H_out_base + (self.storm_intensity * 100.0 - H_out_base) * 0.8
                T_out_base += random.uniform(-self.storm_swing, self.storm_swing)
            
            # Check if event has expired; if so, reset and regenerate in continuous mode
            if hasattr(self, 'event_end_time') and self.current_time >= self.event_end_time:
                self.heat_wave_intensity = 0.0
                self.cold_snap_intensity = 0.0
                self.rain_humidity_boost = 0.0
                self.extreme_heat_intensity = 0.0
                self.extreme_cold_intensity = 0.0
                self.drought_intensity = 0.0
                self.storm_intensity = 0.0
                self.storm_swing = 0.0
                self.event_start_time = 0.0
                self.event_end_time = 0.0
                
                if not getattr(self, '_no_more_events', False):
                    self._generate_random_events()
            
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
            # Capture every 3 hours since absolute time 0: 0, 3h, 6h, 9h, ...
            do_capture = False
            capture_interval = 3 * 3600
            if self.current_time < 1e-6:
                do_capture = True
            else:
                last_capture_time = math.floor(self.current_time / capture_interval) * capture_interval
                if abs(self.current_time - last_capture_time) < 1e-6:
                    do_capture = True

            if do_capture:
                self._captured_this_step = True
                L_root = self.state[0]
                
                # Track previous values for penalty calculation
                prev_L_root = self._prev_L_root
                prev_U_status = self._prev_U_status
                
                r_step = 0.000015
                K = 300.0
                # Use T_in for f_T calculation instead of T_root
                T_in_current = self.state[2]
                if 18 <= T_in_current <= 28:
                    f_T = 1.0
                elif T_in_current < 18:
                    f_T = max(0.3, 1.0 - (18 - T_in_current) * 0.1)
                else:
                    f_T = max(0.3, 1.0 - (T_in_current - 28) * 0.15)

                f_Hin = min(1.0, H_in / 80.0)
                f_O2 = max(0.0, 1.0 - 0.12 * max(0, self.T_continuous - 3))
                limiting_factor = min(f_Hin, f_O2, f_T)
                death_prob = max(0.0, 1.0 - limiting_factor) ** 3 * 0.05
                is_dead = random.random() < death_prob
                if is_dead or self.state[1] <= 0.0:
                    self.state[1] = 0.0
                    delta_l = -self.state[0] * 0.5
                else:
                    day_mult = 1.2 if I_day == 1.0 else 0.6
                    # Growth per capture (3-hour interval): r_step per minute * 180 minutes
                    delta_l = r_step * 180.0 * L_root * (1 - L_root / K) * limiting_factor * day_mult
                new_L_root = max(0.0, L_root + delta_l)
                captured_growth = new_L_root - L_root
                L_root = new_L_root

                if self.state[1] <= 0.0:
                    U_status = 0.0
                else:
                    U_status = self._clip(self.state[1] + self._normal(0.0, 0.01), 0.0, 1.0)

                self.state[0] = L_root
                self.state[1] = U_status
                self._prev_L_root = L_root
                self._prev_U_status = U_status
                # Growth reward is now modulated by f_Hin and f_T
                # Agent learns that good humidity/temperature → higher growth → higher reward
                self.last_reward_growth = self.w_growth * captured_growth * f_Hin * f_T
                
                # Penalize root shrinkage immediately at capture
                if L_root < prev_L_root:
                    self._last_P_shrink = self.w_growth * (prev_L_root - L_root) * 2.0
                else:
                    self._last_P_shrink = 0.0
                
                # Penalize low or dead alive status
                if U_status <= 0.0:
                    self._last_P_death = self.w_status * 5.0
                elif U_status < 0.3:
                    self._last_P_death = self.w_status * (0.3 - U_status) * 3.0
                elif U_status < 0.6:
                    self._last_P_death = self.w_status * (0.6 - U_status) * 1.5
                else:
                    self._last_P_death = 0.0

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
        raw_on = D_mist / 60.0
        on_substeps = int(raw_on)
        self._time_remainder += raw_on - on_substeps
        if self._time_remainder >= 1.0:
            extra = int(self._time_remainder)
            on_substeps += extra
            self._time_remainder -= extra
        if on_substeps == 0:
            on_substeps = 1
        self.T_continuous += on_substeps
        self._update_state_dynamics(is_misting_on=True, A_valve_active=A_valve_active, substeps=on_substeps)

        # Save T_continuous before reset for hypoxia reward
        T_continuous_for_reward = self.T_continuous

        # OFF phase
        raw_off = interval_sec / 60.0
        off_substeps = int(raw_off)
        self._time_remainder += raw_off - off_substeps
        if self._time_remainder >= 1.0:
            extra = int(self._time_remainder)
            off_substeps += extra
            self._time_remainder -= extra
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
        reward += 2.0
        
        # Survival milestone bonuses for reaching key time checkpoints
        # This provides strong positive reinforcement for longevity
        elapsed_time = self.current_time - self._episode_start_time
        if elapsed_time >= 3 * 3600 and not getattr(self, '_milestone_3h', False):
            reward += 20.0
            self._milestone_3h = True
        if elapsed_time >= 6 * 3600 and not getattr(self, '_milestone_6h', False):
            reward += 50.0
            self._milestone_6h = True
        if elapsed_time >= 12 * 3600 and not getattr(self, '_milestone_12h', False):
            reward += 100.0
            self._milestone_12h = True
        if elapsed_time >= 18 * 3600 and not getattr(self, '_milestone_18h', False):
            reward += 200.0
            self._milestone_18h = True
        
        # Frequent small survival bonuses every 30 minutes of simulated time
        # This provides dense positive reinforcement for staying alive
        if elapsed_time > 0 and int(elapsed_time / (30 * 60)) > int((elapsed_time - self.dt) / (30 * 60)):
            reward += 5.0
        
        # Step counting for tracking + completion tracking
        self._step_count += 1
        
        # Clip reward for training stability (wider range to preserve signal)
        reward = self._clip(reward, -200.0, 200.0)

        # Check termination — use slightly relaxed bounds to reduce
        # premature termination from sensor noise + natural drift
        pH_val = self.state[7]
        EC_val = self.state[6]
        terminated = (pH_val < 4.5 or pH_val > 8.5 or EC_val < 0.5 or EC_val > 3.0)
        truncated = (self.current_time - self._episode_start_time) >= self.episode_duration

        # Episode completion bonus: reward agent for surviving the full episode
        if truncated and not terminated:
            reward += 10.0  # significant bonus for full episode survival

        # Strong early termination penalty: losing remaining survival bonus + growth
        if terminated and not truncated:
            elapsed_time = self.current_time - self._episode_start_time
            remaining_time = max(0.0, self.episode_duration - elapsed_time)
            remaining_ratio = remaining_time / self.episode_duration
            
            reward -= 0.5 * remaining_ratio  # lost survival bonus (normalized)
            reward -= self.w_growth * (1.0 + self.state[0] / 100.0) * 1.0  # higher penalty for more developed plants

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
            'reward_shrink': self._last_P_shrink,
            'reward_death': self._last_P_death,
            'reward_extreme': self._last_P_extreme,
            'captured': self._captured_this_step,
            'T_in': self.state[2],
            'T_out': self.state[4],
            'H_out': self.state[5],
        }

        # Return noisy observations as agent-visible state without corrupting ground truth
        return obs_state, reward, terminated, truncated, info

    def _compute_reward(self, action, T_continuous=None):
        """Compute total reward R(t) from section 2.3"""
        D_mist, interval_sec, A_valve = action

        if T_continuous is None:
            T_continuous = self.T_continuous

        R_growth = self.last_reward_growth
        self.last_reward_growth = 0.0

        # Resource cost: baseline valve cost + additional cost when valve is ON
        # Baseline cost covers maintenance, electricity for pumps, etc.
        baseline_valve_cost = 0.01
        C_resource = baseline_valve_cost + self.w_valve_cost * (1.0 if A_valve >= 0.5 else 0.0)

        # Environmental penalties
        pH = self.state[7]
        EC = self.state[6]
        H_in = self.state[3]
        T_in = self.state[2]
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
            R_state += 0.2
        else:
            R_state -= 2.0 * (85.0 - H_in) / 10.0

        if 10.0 <= T_root <= 20.0:
            R_state += 0.3
        elif T_root < 10.0:
            R_state -= 0.5 * (10.0 - T_root)
        else:
            R_state -= 0.3 * (T_root - 20.0)

        if O2_status >= 0.6:
            R_state += 0.05
        else:
            R_state -= 0.2 * (0.6 - O2_status)

        # Action shaping: reward effective misting duration, penalize too-short intervals
        if D_mist >= 180.0:
            R_state += 0.3
        elif D_mist < 120.0:
            R_state -= 1.0

        if 300.0 <= interval_sec <= 600.0:
            R_state += 0.2
        elif interval_sec < 180.0:
            R_state -= 0.5

        P_interval = self.w_interval * (1.0 if interval_sec > 720.0 else 0.0)

        P_diversity = 0.0
        if len(self._action_history) >= 5:
            recent_actions = np.array(self._action_history[-10:])
            d_mist_std = np.std(recent_actions[:, 0])
            interval_std = np.std(recent_actions[:, 1])
            a_valve_toggles = sum(1 for i in range(1, len(recent_actions)) if recent_actions[i, 2] != recent_actions[i-1, 2])

            if d_mist_std > 30.0:
                P_diversity += 2.0
            if interval_std > 40.0:
                P_diversity += 1.0
            if a_valve_toggles >= 2:
                P_diversity += 0.5

        R_efficiency = 0.0
        stability_ok = (
            1.2 <= EC <= 2.0 and
            5.5 <= pH <= 6.5 and
            H_in >= 80.0 and
            24.0 <= T_in <= 30.0
        )
        if stability_ok:
            if D_mist <= 300.0:
                R_efficiency += 0.1 * (300.0 - D_mist) / 180.0
            if interval_sec >= 300.0:
                R_efficiency += 0.1 * (interval_sec - 300.0) / 300.0
            if A_valve < 0.5 and D_mist < 300.0 and interval_sec > 300.0:
                R_efficiency += 0.2

        # Penalize root shrinkage and low/alive status
        P_shrink = self._last_P_shrink
        P_death = self._last_P_death

        # Action regularization: penalize extreme actions to prevent mode collapse
        # This encourages the agent to use actions within sensible ranges
        P_extreme = 0.0
        if D_mist >= 850.0 or D_mist <= 70.0:
            P_extreme += 0.5
        if interval_sec <= 70.0 or interval_sec >= 850.0:
            P_extreme += 0.5
        if A_valve >= 0.5 and (D_mist <= 120.0 or interval_sec <= 120.0):
            P_extreme += 0.5
        
        R_total = R_growth + R_state + P_diversity + R_efficiency - C_resource - P_env - P_hypoxia - P_interval - P_extreme - P_shrink - P_death

        self._last_R_growth = R_growth
        self._last_C_resource = C_resource
        self._last_R_state = R_state
        self._last_P_env = P_env
        self._last_P_hypoxia = P_hypoxia
        self._last_P_interval = P_interval
        self._last_R_efficiency = R_efficiency
        self._last_P_shrink = P_shrink
        self._last_P_death = P_death
        self._last_P_extreme = P_extreme

        return R_total

    @staticmethod
    def _normal(mu, sigma):
        """Box-Muller normal variate"""
        u1 = max(min(random.random(), 1.0 - 1e-16), 1e-16)
        u2 = random.random()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + sigma * z
