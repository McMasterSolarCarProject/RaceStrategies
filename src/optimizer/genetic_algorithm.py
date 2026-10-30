import numpy as np
from typing import Callable

MIN_SPEED=20., MAX_SPEED=100.
L = np.array([1000.0, 500.0, 1500.0, 800.0, 1200.0])
THETA = np.array([0.0, 0.05, -0.02, 0.04, 0.0])
def objective(profile: list[float], A=0.002, B=1500., C=0.8, D=5000., T_TARGET=3000):
    v = np.array(profile) / 3.6
    energy_cost = np.sum(A * (v**3) + B * np.sin(C * v) * np.exp(THETA))
    
    total_time = np.sum(L / v)
    time_penalty = D * max(0.0, total_time - T_TARGET) ** 2
    
    return float(energy_cost + time_penalty)

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
