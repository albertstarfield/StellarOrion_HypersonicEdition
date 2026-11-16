/-- Laptop detection (2026-11-08 20:48 WIB). Core inference that could fail:
EarU sensor set contains macOS SMC/fan/thermal keys AND lid_angle = 102 deg (open)
AND weather timezone = Asia/Jakarta => device is an Apple-silicon Mac laptop in Jakarta.
Empirical step (NOT Lean-provable): sensor values themselves; replaced by EARU snapshot source.
-/
def has_apple_smc_keys : Bool := true   -- sensor_smc_PDBR, PHPC, PHPM, etc.
def has_fan_thermal_keys : Bool := true -- sensor_fan_F0Ac 10978, sensor_temp_TCMz 78.9
def lid_open_deg_102 : Bool := true     -- lid angle 102.0 deg, not 0
def jakarta_coords : Bool := true       -- lat=-6.333047 lon=106.971167 Asia/Jakarta

def is_mac_laptop_observed : Bool :=
  has_apple_smc_keys && has_fan_thermal_keys && lid_open_deg_102

theorem laptop_inference :
    has_apple_smc_keys = true → has_fan_thermal_keys = true → lid_open_deg_102 = true →
    is_mac_laptop_observed = true := by
  intro h1 h2 h3
  simp [is_mac_laptop_observed, h1, h2, h3]

-- Counterexample check: docked phone would lack SMC keys
def lacks_smc : Bool := true
theorem phone_counterexample : lacks_smc = true → has_apple_smc_keys = false → is_mac_laptop_observed = false := by
  intro _ h
  simp [is_mac_laptop_observed, h]
