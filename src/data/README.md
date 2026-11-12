# Motor sample data

## Usage and limits

`Motor` accepts a CSV with `rpm` (rev/min), `torque` (N m), and `efficiency`
(fraction, not percent), plus an optional `duty` column (fraction, not percent).
Additional columns are retained as source information but ignored by the model.
Use one consistent motor, controller, voltage, control mode, and timing
configuration per CSV; duplicate RPM/torque pairs are rejected rather than mixed.

```python
from src.engine.motor import Motor

motor = Motor("src/data/mitsuba_m2096d3_c1_96v.csv")
efficiency = motor.get_efficiency(800, 12)
watts = motor.get_electrical_power(800, 12)
battery_amps = motor.get_battery_current(800, 12, 96)
figure, axes = motor.generate_heatmap()
```

Run `python -m src.engine.motor` to display the Mitsuba example.
`get_duty(rpm, torque)` is available only when measured duty values are supplied;
none of the bundled numeric datasets specifies duty. Duty is not inferred from
RPM or assigned 100% merely because a table says "PWM mode."

Only positive-speed, positive-torque motoring inside the measured convex hull is
supported. Outside queries raise `ValueError`; the heatmap leaves them blank.
The hull is a data-coverage boundary, not a rated or thermal operating envelope,
and may bridge unmeasured gaps. A single load sweep is not a validated full map.
Stall, zero torque, and regeneration require separate models.

Battery current is input power divided by the supplied DC voltage, not phase
current. The voltage must match the dataset's test conditions; passing a new
voltage does not recalibrate efficiency. Controller losses must not be counted
again when the source efficiency already includes them.

## Mitsuba M2096D-III (the car's motor)

- `mitsuba_m2096d3_c1_96v.csv`: 15 positive-torque points extracted from page 1 of
  the user-supplied `M2096D3_M2096C1.pdf`, preserved as
  `mitsuba_m2096d3_c1_source.pdf`. Test labels: 96 V, PWM-duty control mode,
  MTA=0; reported efficiency includes the controller. Duty itself is unspecified.
  The zero-torque/zero-efficiency point is omitted. Reported RPM and N m values
  are kept, and efficiency percentages are divided by 100. Source current (A)
  and voltage (V) are retained. This sweep covers only 743-833 RPM.
- `mitsuba_m2096d3_dyno_series.csv` and `mitsuba_m2096d3_dyno_parallel.csv`:
  13 points each from `Dyno Testing.xlsx`, preserved as
  `mitsuba_m2096d3_dyno_source.xlsx`. The `Dyno Data` ranges are A2:F14 and
  O2:T14 respectively, with the sheet's Series/Parallel labels retained.
  Efficiency is calculated from reported output/input power. The 101.64 V value
  comes from B16/V2. Controller mode, timing, and actual winding configuration
  need confirmation before these sweeps can be combined. Formula-derived phase
  current and estimated-torque columns are not treated as measurements.
- `mitsuba_controller_comparison_source.xlsx`: the original user-supplied
  `M2096_controller compare C1 and C2.xlsx`, retained for later digitization.
  Its 50/70/90/100% PWM curves are embedded images rather than numeric cells.
  The main plots do not unambiguously identify which trace is C1 versus C2;
  they have not been merged into a numeric calibration or the C1 datasheet.

The dyno CSV labels are taken from the workbook, not independent confirmation of
the car's wiring. The manufacturer table and dyno tests are separate datasets.
Published manufacturer context: [Mitsuba M2096-III](https://www.mitsuba.co.jp/scr/product/m2096-iii.html).

## Golden Motor HPM3000 numeric test data

`golden_motor_hpm3000_48v.csv` contains all 25 measurements from Golden Motor's
[HPM3000 48 V, 3 kW test report](https://www.goldenmotor.com/hubmotors/hubmotor-imgs/HPM3000-48V3KW%20Data.pdf), dated 2014-12-31.

The original report is included as
[golden_motor_hpm3000_48v_data.pdf](golden_motor_hpm3000_48v_data.pdf), downloaded
2026-11-09 without modification. All CSV rows were checked against its table.

Columns: `rpm` (rev/min), `torque` (N m), `efficiency` (fraction).
RPM and torque are transcribed as reported; efficiency percentages are divided by 100.

This is one load sweep, not a full efficiency map. It is example data, not a
calibration for the solar car. Interpolation between separated parts of the sweep
is unvalidated. A measured map spanning independent torque and RPM settings is
still needed for driving-strategy predictions. The report does not specify
whether controller losses are included.

SHA-256: `b0e19b07df2fe2221177a62c09f9fb3b52767d5edf34e61408e1fc1645fa6392`

## Hyundai Sonata reference maps

The following CSVs contain positive-torque motoring points from the ORNL test-data
workbooks published in the US EPA ALPHA packages, version 2023-03:

- `hyundai_sonata_30kw_270v.csv`: 90 points from the `Combined` sheet in the
  [2011 Sonata 30 kW package](https://www.epa.gov/system/files/other-files/2023-04/2011-Hyundai-Sonata-30kW-270V-EMOT-ALPHA-Map-Package-Dated-03-23-23.zip), covering motor and inverter efficiency.
- `hyundai_sonata_8_5kw_270v.csv`: 211 points from the `Motor Inverter Belt` sheet in the
  [2012 Sonata 8.5 kW package](https://www.epa.gov/system/files/other-files/2023-04/2012-Hyundai-Sonata-8.5kW-270V-BISG-ALPHA-Map-Package-Dated-03-23-23.zip), including belt losses.

Each matching `_source.xlsx` is the unmodified `3c- ... ORNL Test Data File.xlsx`
from its package. RPM and torque retain the source coordinates; efficiency
percentages are divided by 100. Blank cells, zero-torque rows, and regeneration
are omitted. These use the supplied test tables, not EPA's completed ALPHA maps.

Source: [US EPA eMotor map packages](https://www.epa.gov/vehicle-and-fuel-emissions-testing/combining-data-complete-emotor-alpha-maps), downloaded 2026-11-12.
These are separate reference configurations, not calibrations for the solar car.

## Integration candidates (not changed)

- [StateNode.Power_calc](../engine/nodes.py): replace the fixed 90% efficiency;
  convert speed to motor RPM and pass torque per motor, then sum input power
  across motors. This shared method serves cruising and acceleration.
- [StateNode.solve_cruise_state](../engine/nodes.py): replace the old
  `speed_from_torque` feasibility check with an operating-point query, handling
  unsupported points explicitly rather than clamping them.
- [DynamicNode.solve_DynamicNode](../engine/nodes.py): its SOC update already
  consumes `P_in`, so it receives the new power calculation through the shared
  method; stall, braking, and regeneration must be handled before integration.
- [simulate_speed_profile](../experiments/velocity_simulator.py) and
  [set_target_speed_profile](../optimizer/optimize_main.py): check candidate
  operating points through the same shared model so unsupported speeds are not
  scored as valid. Load the model once per simulation, not once per time step.
