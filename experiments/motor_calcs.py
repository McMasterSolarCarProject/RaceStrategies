# BLDC/PMSM steady-state visualization with Matplotlib
# - X axis: current iq (A)
# - Y axis: speed (RPM) or torque (N·m)
# - PWM utilization (modulation index) shown as marker size or as a contour
#
# How it works:
#   Vd = -we * L * iq
#   Vq =  R * iq + we * (L * id + lam_f)      (steady-state, id = 0 here)
#   |Vdq| = sqrt(Vd^2 + Vq^2)
#   mod_index m = |Vdq| / (Vdc / sqrt(3))     (≈ SVPWM linear-region limit)
#   Torque T = 1.5 * p * lam_f * iq           (surface PM)
#
# Replace the parameters with your motor/controller values.

import numpy as np
import matplotlib.pyplot as plt

# -------- Parameters (EDIT these to your motor) --------
R      = 0.05        # phase resistance [ohm]
L      = 120e-6      # synchronous inductance [H] (Ld≈Lq)
lam_f  = 0.03        # flux linkage [V·s/rad]
p      = 7           # pole pairs
Vdc    = 96.0        # DC bus voltage [V]
Imax   = 120.0       # current limit you want to visualize [A]
rpm_max = 2000.0     # top speed for the grid [RPM]

# -------- Derived --------
Vmax = Vdc / np.sqrt(3.0)  # dq peak voltage limit in linear SVPWM

# -------- Grid to evaluate --------
currents = np.linspace(0.0, Imax, 80)        # iq (A)
speeds_rpm = np.linspace(0.0, rpm_max, 80)   # mechanical speed (RPM)

Iq, RPM = np.meshgrid(currents, speeds_rpm, indexing="xy")
wm = RPM * 2*np.pi/60.0             # mech rad/s
we = p * wm                         # elec rad/s

# Assume no field-weakening for the plots (id = 0)
Id = np.zeros_like(Iq)

# dq voltages (steady state)
Vd = - we * L * Iq
Vq =   R * Iq + we * (L * Id + lam_f)
Vmag = np.sqrt(Vd*Vd + Vq*Vq)

# PWM utilization (modulation index 0..1)
mod_index = np.clip(Vmag / Vmax, 0.0, 1.0)

# Torque (surface PM approximation)
Torque = 1.5 * p * lam_f * Iq

# Helper: map modulation index -> marker size
def size_from_m(m):
    return 8 + 220*m  # tweak if you want bigger/smaller markers

# ========== Plot 1: Speed vs Current (PWM as marker size) ==========
plt.figure(figsize=(8, 6))
x = Iq.ravel()
y = RPM.ravel()
s = size_from_m(mod_index.ravel())
plt.scatter(x, y, s=s, alpha=0.45, edgecolors="none")
plt.xlabel("Current $i_q$ [A]")
plt.ylabel("Mechanical speed [RPM]")
plt.title("Speed vs Current — marker size encodes PWM utilization")
plt.grid(True)
plt.tight_layout()

# ========== Plot 2: Torque vs Current at a few speeds (PWM as marker size) ==========
for slice_rpm in [500.0, 1000.0, 1500.0]:  # add/remove slices as you like
    idx = np.argmin(np.abs(speeds_rpm - slice_rpm))
    iq_slice = Iq[idx, :]
    tq_slice = Torque[idx, :]
    m_slice  = mod_index[idx, :]
    plt.figure(figsize=(8, 6))
    plt.scatter(iq_slice, tq_slice, s=size_from_m(m_slice), alpha=0.6, edgecolors="none")
    plt.xlabel("Current $i_q$ [A]")
    plt.ylabel("Torque [N·m]")
    plt.title(f"Torque vs Current at {speeds_rpm[idx]:.0f} RPM — marker size encodes PWM utilization")
    plt.grid(True)
    plt.tight_layout()

# ========== Plot 3: Contour map of PWM utilization over (Current, Speed) ==========
plt.figure(figsize=(8, 6))
levels = np.linspace(0.0, 1.0, 11)  # contours at 0.0, 0.1, ..., 1.0
cs = plt.contourf(Iq, RPM, mod_index, levels=levels)
cbar = plt.colorbar(cs)
cbar.set_label("PWM utilization (modulation index)")
plt.xlabel("Current $i_q$ [A]")
plt.ylabel("Mechanical speed [RPM]")
plt.title("PWM utilization over (Current, Speed)")
plt.grid(True)
plt.tight_layout()

plt.show()
