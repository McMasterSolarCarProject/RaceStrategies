import numpy as np
from typing import Callable
from ..config import Vehicle, constants, vehicle_default
from ..models import Route

MIN_SPEED=20
MAX_SPEED=100

def objective(
		profile: list[float], route: Route, vehicle: Vehicle = vehicle_default,
		target_time: float = 3000.0, time_penalty_weight: float = 5000.0,
		speed_penalty_weight: float = 5000.0,
	) -> float:
	speeds = np.asarray(profile, dtype=float)/3.6
	segments = route.segments

	total_time = 0.0
	energy_joules = 0.0
	speed_violation = 0.0

	for (speed, segment) in zip(speeds, segments):
		grade_sin = segment.gradient.sin()
		grade_cos = segment.gradient.cos()
		segment_time = segment.dist/speed
		total_time += segment_time
		speed_violation += max(0.0, speed - segment.speed_limit) ** 2
		aerodynamic_force = (0.5*constants.air_density*vehicle.coef_drag
		                     *vehicle.cross_section*(speed + segment.wind_speed)**2)
		rolling_force = vehicle.coef_rr * vehicle.car_mass * constants.g * grade_cos
		grade_force = vehicle.car_mass * constants.g * grade_sin
		net_tractive_force = aerodynamic_force + rolling_force + grade_force

		mechanical_work = net_tractive_force * segment.dist
		recovered_energy = max(0.0, -mechanical_work) * vehicle.regen_eff
		solar_energy = segment.ghi * vehicle.cell_area * segment_time
		energy_joules += max(0.0, mechanical_work) + (
			vehicle.passive_consumption*segment_time) - recovered_energy - solar_energy

	time_penalty = time_penalty_weight * max(0.0, total_time - target_time) ** 2
	speed_penalty = speed_penalty_weight * speed_violation
	return float(energy_joules / 1000.0 + time_penalty + speed_penalty)

def selection(pop: list[list[float]], scores: list[float],
    tournament_size: int = 5,) -> list[float]:
    indices = np.random.randint(
        0,
        len(pop),
        size=min(tournament_size, len(pop)),
    )
    winner = min(indices, key=lambda index: scores[index])
    return pop[int(winner)]

def crossover(p1: list[float], p2: list[float], r_cross: float):
	# children are copies of parents by default
	c1, c2 = p1.copy(), p2.copy()
	# check for recombination
	if np.random.random() < r_cross:
		# select crossover point that is not on the end of the string
		pt = np.random.randint(1, len(p1)-1)
		# perform crossover
		c1 = p1[:pt] + p2[pt:]
		c2 = p2[:pt] + p1[pt:]
	return [c1, c2]

def mutation(profile, r_mut, scale=0.1):
	for i in range(len(profile)):
		# check for a mutation
		if np.random.random() < r_mut:
			# change speed
			speed_range = min(profile[i] - MIN_SPEED, MAX_SPEED - profile[i])
			if speed_range > 0:
				profile[i] += np.random.normal(0, scale*speed_range)
			profile[i] = max(
                MIN_SPEED,
                min(MAX_SPEED, profile[i]),
            )

def genetic_algorithm(objective: Callable, route: Route, n_iter: int, n_pop: int, 
                      r_cross: float=0.9, r_mut: float=0.05, elite: int=2):
	n_seg = len(route.segments)
	# initial population of random bitstring
	pop = [np.random.uniform(MIN_SPEED, MAX_SPEED, n_seg).tolist() for _ in range(n_pop)]
	# keep track of best solution
	best, best_eval = pop[0].copy(), objective(pop[0], route)
	history = []
	# enumerate generations
	for gen in range(n_iter):
		# evaluate all candidates in the population
		scores = [objective(c, route) for c in pop]
		# check for new best solution
		for i in range(n_pop):
			if scores[i] < best_eval:
				best, best_eval = pop[i], scores[i]
				print(f">{gen:d}, new best f({[round(x, 2) for x in pop[i][:3]]}) = {scores[i]:.3f}")
		history.append(best_eval)
		# elitism
		sorted_indices = np.argsort(scores)
		children = []
		for i in range(elite):
			children.append(pop[sorted_indices[i]].copy())
		# select parents
		selected = [selection(pop, scores) for _ in range(n_pop)]
		# create the next generation
		for i in range(0, n_pop, 2):
			if len(children) >= n_pop:
				break
			# get selected parents in pairs
			p1, p2 = selected[i], selected[(i + 1) % n_pop]
			# crossover and mutation
			for c in crossover(p1, p2, r_cross):
				# mutation
				c_mut = c.copy()
				mutation(c_mut, r_mut)
				# store for next generation
				children.append(c_mut)
		# replace population
		pop = children
	return [best, best_eval, history]


if __name__=="__main__":
	import matplotlib.pyplot as plt
	from src.database.route_table import RouteTable

	DB_PATH = "ASC_2024.sqlite"
	ROUTE_NAME = "A. Independence to Topeka"


	route = RouteTable.fetch_route(
		placemark_name=ROUTE_NAME,
		db_path=DB_PATH,
	)

	best_profile, best_score, history = genetic_algorithm(
		objective=objective,
		route=route,
		n_iter=300,
		n_pop=100,
		r_cross=0.9,
		r_mut=0.05,
	)

	print(f"Route: {route.name}")
	print(f"Best objective value: {best_score:.3f}")

	distance_edges_km = np.concatenate((
		[0.0],
		np.cumsum([segment.dist for segment in route.segments]) / 1000.0,
	))
	distances_km = (
		distance_edges_km[:-1] + distance_edges_km[1:]
	) / 2

	speed_limits = [
		segment.speed_limit * 3.6
		for segment in route.segments
	]
	raw_profile = np.asarray(best_profile)
	smoothing_window = min(21, len(raw_profile))
	if smoothing_window % 2 == 0:
		smoothing_window -= 1
	padding = smoothing_window // 2
	padded_profile = np.pad(raw_profile, padding, mode="edge")
	smoothed_profile = np.array([
		np.median(padded_profile[index:index + smoothing_window])
		for index in range(len(raw_profile))
	])

	figure, axes = plt.subplots(
		2,
		1,
		figsize=(14, 8),
		constrained_layout=True,
	)
	figure.patch.set_facecolor("#f7f8fa")

	axes[0].plot(
		distances_km,
		raw_profile,
		color="#4c78a8",
		alpha=0.18,
		linewidth=0.8,
		label="Raw optimized speed",
	)
	axes[0].plot(
		distances_km,
		smoothed_profile,
		color="#1f4e79",
		linewidth=2.5,
		label="Smoothed strategy",
	)
	axes[0].stairs(
		speed_limits,
		distance_edges_km,
		color="#e4572e",
		linewidth=2,
		linestyle="--",
		label="Speed limit",
	)
	axes[0].set_title("Optimized Speed Profile", loc="left", weight="bold")
	axes[0].set_xlabel("Distance (km)")
	axes[0].set_ylabel("Speed (km/h)")
	axes[0].set_ylim(MIN_SPEED - 5, max(MAX_SPEED + 5, max(speed_limits) + 5))
	axes[0].grid(True, alpha=0.25)
	axes[0].legend(frameon=False, ncol=3, loc="upper right")

	axes[1].plot(
		range(1, len(history) + 1),
		history,
		color="#59a14f",
		linewidth=2,
	)
	axes[1].set_title("Genetic Algorithm Convergence", loc="left", weight="bold")
	axes[1].set_xlabel("Generation")
	axes[1].set_ylabel("Best objective value")
	axes[1].set_yscale("log")
	axes[1].grid(True, which="both", alpha=0.25)

	figure.suptitle("Race Strategy Optimization", fontsize=18, weight="bold")
	plt.show()