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
		total_time += segment.dist/segment.speed_limit
		speed_violation += max(0.0, speed - segment.speed_limit * 3.6) ** 2
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

def selection(pop: list[list[float]], scores: list[float], k: int=5):
	# first random selection
	selection_ix = np.randint(len(pop))
	for ix in np.randint(0, len(pop), k-1):
		# check if better (e.g. perform a tournament)
		if scores[ix] < scores[selection_ix]:
			selection_ix = ix
	return pop[selection_ix]

def crossover(p1: list[float], p2: list[float], r_cross: float):
	# children are copies of parents by default
	c1, c2 = p1.copy(), p2.copy()
	# check for recombination
	if np.rand() < r_cross:
		# select crossover point that is not on the end of the string
		pt = np.randint(1, len(p1)-2)
		# perform crossover
		c1 = p1[:pt] + p2[pt:]
		c2 = p2[:pt] + p1[pt:]
	return [c1, c2]

def mutation(profile, r_mut, scale=0.1):
	for i in range(len(profile)):
		# check for a mutation
		if np.rand() < r_mut:
			# change speed
			speed_range = min(profile[i] - MIN_SPEED, MAX_SPEED - profile[i])
			profile[i] += np.normal(0, scale*speed_range)
			profile[i] = max(
                MIN_SPEED,
                min(MAX_SPEED, profile[i]),
            )

def genetic_algorithm(objective: Callable, n_seg: int, n_iter: int, n_pop: int, 
                      r_cross: float=0.9, r_mut: float=0.05, elite: int=2):
	# initial population of random bitstring
	pop = [np.uniform(MIN_SPEED, MAX_SPEED, n_seg).tolist() for _ in range(n_pop)]
	# keep track of best solution
	best, best_eval = 0, objective(pop[0])
	# enumerate generations
	for gen in range(n_iter):
		# evaluate all candidates in the population
		scores = [objective(c) for c in pop]
		# check for new best solution
		for i in range(n_pop):
			if scores[i] < best_eval:
				best, best_eval = pop[i], scores[i]
				print(f">{gen:d}, new best f({[round(x, 2) for x in pop[i][:3]]}) = {scores[i]:.3f}")
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
			p1, p2 = selected[i], selected[i+1]
			# crossover and mutation
			for c in crossover(p1, p2, r_cross):
				# mutation
				c_mut = c.copy()
				mutation(c_mut, r_mut)
				# store for next generation
				children.append(c_mut)
		# replace population
		pop = children
	return [best, best_eval]
