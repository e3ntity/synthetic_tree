import numpy as np
from scipy.special import logsumexp


class MCTS:
    def __init__(self, exploration_coeff, algorithm, tau):
        self._exploration_coeff = exploration_coeff
        self._algorithm = algorithm
        self._tau = tau

    def run(self, tree_env, n_simulations):
        v_hat = np.zeros(n_simulations)
        for i in range(n_simulations):
            tree_env.reset()
            v_hat[i] = self._simulation(tree_env)

        return v_hat

    def _simulation(self, tree_env):
        path = self._navigate(tree_env)

        leaf_node = tree_env.tree.nodes[path[-1][1]]

        leaf_node['V'] = (leaf_node['V'] * leaf_node['N'] +
                          tree_env.rollout(path[-1][1])) / (leaf_node['N'] + 1)
        leaf_node['N'] += 1
        for e in reversed(path):
            current_node = tree_env.tree.nodes[e[0]]
            next_node = tree_env.tree.nodes[e[1]]

            tree_env.tree[e[0]][e[1]]['Q'] = next_node['V']
            tree_env.tree[e[0]][e[1]]['N'] += 1
            if self._algorithm == 'uct':
                current_node['V'] = (current_node['V'] * current_node['N'] +
                                     tree_env.tree[e[0]][e[1]]['Q']) / (current_node['N'] + 1)
            else:
                out_edges = [e for e in tree_env.tree.edges(e[0])]
                qs = np.array(
                    [tree_env.tree[e[0]][e[1]]['Q'] for e in out_edges])
                if self._algorithm == 'ments':
                    current_node['V'] = self._tau * logsumexp(qs / self._tau)
                elif self._algorithm == 'rents':
                    visitation_ratio = np.array(
                        [tree_env.tree[e[0]][e[1]]['N'] / (tree_env.tree.nodes[e[0]][
                            'N'] + 1e-10) for e in out_edges]
                    )
                    current_node['V'] = self._tau * np.log(np.sum(visitation_ratio * np.exp(qs / self._tau)))
                elif self._algorithm == 'tents':
                    q_exp_tau = np.exp(qs / self._tau)
                    sorted_q = np.sort(qs)
                    kappa = list()
                    for i, q in enumerate(reversed(sorted_q)):
                        if 1 + (i + 1) * sorted_q[i] > sorted_q[:i + 1].sum():
                            idx = np.argwhere(qs == sorted_q[i]).ravel()[0]
                            qs[idx] = np.nan
                            kappa.append(idx)
                    kappa = np.array(kappa)

                    sparse_max = q_exp_tau / 2 - (np.array([q_exp_tau[i] for i in kappa]) - 1) ** 2 / (2 * len(kappa) ** 2)
                    sparse_max = sparse_max.sum() + .5
                    current_node['V'] = self._tau * sparse_max
                else:
                    raise ValueError

            current_node['N'] += 1

        return tree_env.tree.nodes[0]['V']

    def _navigate(self, tree_env):
        state = tree_env.state
        action = self._select(tree_env)
        next_state = tree_env.step(action)
        if next_state not in tree_env.leaves:
            return [[state, next_state]] + self._navigate(tree_env)
        else:
            return [[state, next_state]]

    def _select(self, tree_env):
        out_edges = [e for e in tree_env.tree.edges(tree_env.state)]
        n_state_action = np.array(
            [tree_env.tree[e[0]][e[1]]['N'] for e in out_edges])
        qs = np.array(
            [tree_env.tree[e[0]][e[1]]['Q'] for e in out_edges])
        if self._algorithm == 'uct':
            n_state = np.sum(n_state_action)
            if n_state > 0:
                ucb_values = qs + self._exploration_coeff * np.sqrt(
                    np.log(n_state) / (n_state_action + 1e-10)
                )
            else:
                ucb_values = np.ones(len(n_state_action)) * np.inf

            return np.random.choice(np.argwhere(ucb_values == np.max(ucb_values)).ravel())
        else:
            n_actions = len(out_edges)
            lambda_coeff = np.clip(self._exploration_coeff * n_actions / np.log(
                np.sum(n_state_action) + 1 + 1e-10), 0, 1)
            q_exp_tau = np.exp(qs / self._tau)

            if self._algorithm == 'ments':
                probs = (1 - lambda_coeff) * q_exp_tau / q_exp_tau.sum() + lambda_coeff / n_actions
                probs[np.random.randint(len(probs))] += 1 - probs.sum()

                return np.random.choice(np.arange(n_actions), p=probs)
            elif self._algorithm == 'rents':
                visitation_ratio = np.array(
                    [tree_env.tree[e[0]][e[1]]['N'] / (tree_env.tree.nodes[e[0]]['N'] + 1e-10) for e in out_edges]
                )
                probs = (1 - lambda_coeff) * visitation_ratio * q_exp_tau / q_exp_tau.sum() + lambda_coeff / n_actions
                probs[np.random.randint(len(probs))] += 1 - probs.sum()

                return np.random.choice(np.arange(n_actions), p=probs)
            elif self._algorithm == 'tents':
                sorted_q = np.sort(qs)
                kappa = list()
                for i, q in enumerate(reversed(sorted_q)):
                    if 1 + (i + 1) * sorted_q[i] > sorted_q[:i + 1].sum():
                        idx = np.argwhere(qs == sorted_q[i]).ravel()[0]
                        qs[idx] = np.nan
                        kappa.append(idx)
                kappa = np.array(kappa)

                q_exp_tau = q_exp_tau[kappa]
                max_omega = np.maximum(q_exp_tau - (q_exp_tau - 1).sum() / len(kappa),
                                       np.zeros(len(kappa)))
                probs = (1 - lambda_coeff) * max_omega + lambda_coeff / n_actions
            else:
                raise ValueError

            return np.random.choice(np.arange(n_actions), p=probs)
