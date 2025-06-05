import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

torque_data_series_X = np.array(
    [
        1,
        2,
        4,
        6,
        8,
        10,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        26,
        28,
        30,
        32,
        34,
        36,
        38,
        40,
        42,
        44,
        46,
        48,
        50,
        52,
        54,
        56,
        58,
        60,
        62,
        64,
        65.567,
    ]
)

current_data_series_Y = np.array(
    [
        1.61,
        2.54,
        4.36,
        6.14,
        7.88,
        9.7,
        11.42,
        13.15,
        14.84,
        16.54,
        18.25,
        19.92,
        21.6,
        23.461,
        25.197,
        26.933,
        28.669,
        30.405,
        32.141,
        33.877,
        35.613,
        37.349,
        39.085,
        40.821,
        42.557,
        44.293,
        46.029,
        47.765,
        49.501,
        51.237,
        52.973,
        54.709,
        56.445,
        57.805156,
    ]
)

rpm_data_series_Y = np.array(
    [
        889,
        892,
        884,
        877,
        870,
        863,
        856,
        850,
        843,
        837,
        831,
        825,
        820,
        811.54,
        805.12,
        798.7,
        792.28,
        785.86,
        779.44,
        773.02,
        766.6,
        760.18,
        753.76,
        747.34,
        740.92,
        734.5,
        728.08,
        721.66,
        715.24,
        708.82,
        702.4,
        695.98,
        689.56,
        684.52993,
    ]
)


degree = 1
kmph_data = rpm_data_series_Y * (2*3.14*0.2*60/1000)
torque_to_current = make_pipeline(PolynomialFeatures(degree), LinearRegression())
torque_to_rpm = make_pipeline(PolynomialFeatures(degree), LinearRegression())
torque_to_current.fit(torque_data_series_X.reshape(-1, 1), current_data_series_Y)
torque_to_rpm.fit(torque_data_series_X.reshape(-1, 1), kmph_data)

current_to_torque = make_pipeline(PolynomialFeatures(degree), LinearRegression())
current_to_rpm = make_pipeline(PolynomialFeatures(degree), LinearRegression())

# Fit models with current as input
current_to_torque.fit(current_data_series_Y.reshape(-1, 1), torque_data_series_X)
current_to_rpm.fit(current_data_series_Y.reshape(-1, 1), kmph_data)

import numpy as np
import matplotlib.pyplot as plt
from graph import plot_dual_axis_fit

#solving k:
ra = 0.4
# 16.54Amps and 837 RPM taken from data
ke = (101.64 - 16.54 * ra) / 837
v = 72
newV = (v - current_data_series_Y*ra)/ke * (2*3.14*0.2*60/1000)

plot_dual_axis_fit(current_data_series_Y, torque_data_series_X, newV, current_to_torque, current_to_rpm, "current", "torque", "kmph", "current vs torque and rpm")