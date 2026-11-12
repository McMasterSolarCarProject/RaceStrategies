# Motor sample data

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
