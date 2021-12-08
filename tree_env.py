import networkx as nx
import numpy as np

from scipy.special import logsumexp


class SyntheticTree:
    def __init__(self, k, d, algorithm, tau, alpha, gamma):
        """
        Args:
            k (int): Branching factor of the tree.
            d (int): Height of the tree.
            algorithm (string): The algorithm to build the tree for.
            tau (float):
            alpha (float):
            gamma (float):
        """
        self._k = k
        self._d = d
        self._algorithm = algorithm
        self._tau = tau
        self._alpha = alpha
        self._gamma = gamma


        self._tree = nx.balanced_tree(k, d, create_using=nx.DiGraph)
        random_weights = np.random.rand(len(self._tree.edges))
        for i, e in enumerate(self._tree.edges):
            self._tree[e[0]][e[1]]['weight'] = random_weights[i]
            self._tree[e[0]][e[1]]['N'] = 0
            self._tree[e[0]][e[1]]['Q'] = 0.

            if algorithm == "w-mcts":
                self._tree[e[0]][e[1]]['q_mean'] = 0.5
                self._tree[e[0]][e[1]]['q_variance'] = 0.5

        for n in self._tree.nodes:
            self._tree.nodes[n]['N'] = 0
            self._tree.nodes[n]['V'] = 0.

            if algorithm == "w-mcts":
                self._tree.nodes[n]['v_mean'] = 0.5
                self._tree.nodes[n]['v_variance'] = 0.5
            elif algorithm == "dng":
                self._tree.nodes[n]["mu"] = 0.
                self._tree.nodes[n]["lambda"] = 1e-2
                self._tree.nodes[n]["alpha"] = 1.
                self._tree.nodes[n]["beta"] = 100.

        self.leaves = [x for x in self._tree.nodes() if
                       self._tree.out_degree(x) == 0 and self._tree.in_degree(x) == 1]

        self._compute_mean()
        means = np.array([self._tree.nodes[n]['mean'] for n in self.leaves])
        means = (means - means.min()) / (means.max() - means.min()) if len(means) > 1 else [0.]
        for i, n in enumerate(self.leaves):
            self._tree.nodes[n]['mean'] = means[i]

        self.max_mean = 0
        for leaf in self.leaves:
            self.max_mean = max(self.max_mean, self._tree.nodes[leaf]['mean'])

        self._assign_priors_maxs()

        self.optimal_v_root, self.q_root = self._solver()

        self.state = None

        self.reset()

    def reset(self, state=None):
        """Resets the active state of the tree.

        Args:
            state (int): The state to reset the tree to. Defaults to the root state.
        Returns:
            The new active state of the tree.
        """
        if state is not None:
            self.state = state
        else:
            self.state = 0

        return self.state

    def step(self, action):
        """Advances the active state of the tree.

        Args:
            action (int): The action to take in the currently active state.
        Returns:
            The new active state of the tree.
        """
        edges = [e for e in self._tree.edges(self.state)]
        self.state = edges[action][1]

        return self.state

    def rollout(self, state):
        """Computes the return of a random rollout starting in the given state.

        Simulates a random rollout by taking a sample from a normal distribution centerd at the pre-computed mean
        return of the given state.

        Args:
            state (int): The state from which to rollout.
        Returns:
            The return of the rollout.
        """
        return np.random.normal(self._tree.nodes[state]['mean'], scale=.5)
        # return np.random.normal(self._tree.nodes[state]['mean'], scale=.05)

    @property
    def tree(self):
        return self._tree

    def _compute_mean(self, node=0, weight=0):
        """Recursively computes and assigns the mean returns at each leaf node of the tree.

        Cmputes the cumulative sum of rewards when going from the root node to each leaf node. These are then assigned
        to each respective leaf node as it's mean return.
        """
        if node not in self.leaves:
            for e in self._tree.edges(node):
                self._compute_mean(e[1],
                                   weight + self._tree[e[0]][e[1]]['weight'])
        else:
            self._tree.nodes[node]['mean'] = weight

    def _assign_priors_maxs(self, node=0):
        """Recursively computes and assigns the mean returns and priors at each intermediate node in the tree."""
        successors = [n for n in self._tree.successors(node)]
        if successors[0] not in self.leaves:
            means = np.array([self._assign_priors_maxs(s) for s in successors])
            self._tree.nodes[node]['prior'] = means / means.sum()
            self._tree.nodes[node]['mean'] = means.max()

            return means.max()
        else:
            means = np.array([self._tree.nodes[s]['mean'] for s in successors])
            self._tree.nodes[node]['prior'] = means / means.sum()
            self._tree.nodes[node]['mean'] = means.max()

            return means.max()

    def _solver(self, node=0):
        if self._algorithm == 'w-mcts':
            successors = [n for n in self._tree.successors(node)]
            means = np.array([self._tree.nodes[s]['mean'] for s in successors])

            return self.max_mean, means
        elif self._algorithm == 'dng':
            successors = [n for n in self._tree.successors(node)]
            means = np.array([self._tree.nodes[s]['mean'] for s in successors])

            return self.max_mean, means
        elif self._algorithm == 'uct':
            successors = [n for n in self._tree.successors(node)]
            means = np.array([self._tree.nodes[s]['mean'] for s in successors])

            return self.max_mean, means
        else:
            successors = [n for n in self._tree.successors(node)]
            if self._algorithm == 'ments':
                if successors[0] in self.leaves:
                    x = np.array([self._tree.nodes[n]['mean'] for n in self._tree.successors(node)])

                    return self._tau * logsumexp(x / self._tau), x
                else:
                    x = np.array([self._solver(n)[0] for n in self._tree.successors(node)])

                    return self._tau * logsumexp(x / self._tau), x
            elif self._algorithm == 'rents':
                if successors[0] in self.leaves:
                    x = np.array([self._tree.nodes[n]['mean'] for n in self._tree.successors(node)])

                    return self._tau * np.log(np.sum(self._tree.nodes[node]['prior'] * np.exp(x / self._tau))), x
                else:
                    x = np.array([self._solver(n)[0] for n in self._tree.successors(node)])

                    return self._tau * np.log(np.sum(self._tree.nodes[node]['prior'] * np.exp(x / self._tau))), x
            elif self._algorithm == 'alpha-divergence':
                def sparse_max_alpha_divergence(means_tau):
                    temp_means_tau = means_tau.copy()
                    sorted_means = np.flip(np.sort(temp_means_tau))
                    kappa = list()
                    for i in range(1, len(sorted_means) + 1):
                        if self._alpha + i * sorted_means[i-1] > sorted_means[:i].sum() + i * (self._alpha - (self._alpha/(self._alpha-1))):
                            idx = np.argwhere(temp_means_tau == sorted_means[i-1]).ravel()[0]
                            temp_means_tau[idx] = np.nan
                            kappa.append(idx)
                    kappa = np.array(kappa)

                    c_s_tau = ((means_tau[kappa].sum() - self._alpha) / len(kappa)) + (self._alpha - (self._alpha/(self._alpha-1)))

                    max_omega_tmp = np.maximum(means_tau - c_s_tau, np.zeros(len(means_tau)))
                    max_omega = np.power(max_omega_tmp * ((self._alpha - 1)/self._alpha), 1/(self._alpha))
                    max_omega = max_omega/np.sum(max_omega)

                    sparse_max_tmp = max_omega * (means_tau + (1/(self._alpha - 1)) * (1 - max_omega_tmp))

                    sparse_max = sparse_max_tmp.sum()

                    return sparse_max

                if successors[0] in self.leaves:
                    x = np.array([self._tree.nodes[n]['mean'] for n in self._tree.successors(node)])

                    return self._tau * sparse_max_alpha_divergence(x / self._tau), x
                else:
                    x = np.array([self._solver(n)[0] for n in self._tree.successors(node)])

                    return self._tau * sparse_max_alpha_divergence(np.array(x / self._tau)), x
            elif self._algorithm == 'tents':
                def sparse_max(means_tau):
                    temp_means_tau = means_tau.copy()
                    sorted_means = np.flip(np.sort(temp_means_tau))
                    kappa = list()
                    for i in range(1, len(sorted_means) + 1):
                        if 1 + i * sorted_means[i-1] > sorted_means[:i].sum():
                            idx = np.argwhere(temp_means_tau == sorted_means[i-1]).ravel()[0]
                            temp_means_tau[idx] = np.nan
                            kappa.append(idx)
                    kappa = np.array(kappa)

                    sparse_max = means_tau[kappa] ** 2 / 2 - (
                        means_tau[kappa].sum() - 1) ** 2 / (2 * len(kappa) ** 2)
                    sparse_max = sparse_max.sum() + .5

                    return sparse_max

                if successors[0] in self.leaves:
                    x = np.array([self._tree.nodes[n]['mean'] for n in self._tree.successors(node)])

                    return self._tau * sparse_max(x / self._tau), x
                else:
                    x = np.array([self._solver(n)[0] for n in self._tree.successors(node)])

                    return self._tau * sparse_max(np.array(x / self._tau)), x
            else:
                raise ValueError
