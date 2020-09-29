import numpy as np
from joblib import Parallel, delayed

from matplotlib import pyplot as plt
from mcts import MCTS
from tree_env import SyntheticTree


def experiment():
    mcts = MCTS(exploration_coeff=exploration_coeff, algorithm='uct')

    v_hat = np.zeros((n_trees, n_simulations))
    diff = np.zeros_like(v_hat)
    for i in range(n_trees):
        tree = SyntheticTree(k, d)
        v_hat[i] = mcts.run(tree, n_simulations)
        diff[i] = np.abs(v_hat[i] - tree.optimal_v_root)

    return v_hat, diff


n_exp = 5
n_trees = 5
n_simulations = 10000
exploration_coeff = 0.1
k = 100
d = 1

out = Parallel(n_jobs=-1)(delayed(experiment)() for _ in range(n_exp))
v_hat = np.array([o[0]]for o in out)
diff = np.array([o[1] for o in out])

avg_diff = diff.mean(0).mean(0)
plt.plot(avg_diff)
plt.show()
