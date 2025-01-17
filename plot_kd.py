import numpy as np
from matplotlib import pyplot as plt


n_exp = 5
n_trees = 5
n_simulations = 1000
k_heat = [2, 4, 6, 8]  # [50, 100, 200]
d_heat = [1, 2, 3, 4, 5]  # [50, 100, 200]
# k = [50, 50, 100, 100, 200, 200]
# d = [1, 2, 1, 2, 1, 2]
k = [2, 4, 6, 8]
d = [1, 2, 3, 4, 5]
exploration_coeff = 1.41
tau = .1
# algs = ['uct', 'ments', 'rents', 'tents']

algs = ['uct', 'ments', 'rents', 'tents', 'w-mcts', 'dng']

folder_name = 'logs/expl_%.2f_tau_%.2f' % (exploration_coeff, tau)

# PLOTS
plt.figure()

count_plot = 0
for kk, dd in zip(k, d):
    max_diff = 0
    max_diff_uct = 0
    max_regret = 0
    for alg in algs:
        subfolder_name = folder_name + '/k_%d_d_%d' % (kk, dd)
        diff = np.load(subfolder_name + '/diff_%s.npy' % (alg))
        avg_diff = diff.mean(0)
        plt.subplot(3, len(k), 1 + count_plot % len(k))
        plt.title('k=%d  d=%d' % (kk, dd), fontsize='xx-large')
        plt.tick_params(
            axis='x',
            which='both',
            bottom=False,
            top=False,
            labelbottom=False)
        plt.yticks(fontsize='xx-large')
        if count_plot == 0:
            plt.ylabel(r'$\varepsilon_\Omega$', fontsize='xx-large')
        plt.plot(avg_diff, linewidth=3)
        err = 2 * np.std(diff.reshape(n_exp * n_trees, n_simulations),
                         axis=0) / np.sqrt(n_exp * n_trees)
        plt.fill_between(np.arange(n_simulations), avg_diff - err, avg_diff + err,
                         alpha=.5)
        max_diff = max(max_diff, avg_diff.max())

        diff_uct = np.load(subfolder_name + '/diff_uct_%s.npy' % (alg))
        avg_diff_uct = diff_uct.mean(0)
        plt.subplot(3, len(k), len(k) + 1 + count_plot % len(k))
        plt.tick_params(
            axis='x',
            which='both',
            bottom=False,
            top=False,
            labelbottom=False)
        plt.yticks(fontsize='xx-large')
        if count_plot == 0:
            plt.ylabel(r'$\varepsilon_{UCT}$', fontsize='xx-large')
        plt.plot(avg_diff_uct, linewidth=3)
        err = 2 * np.std(diff_uct.reshape(n_exp * n_trees, n_simulations),
                         axis=0) / np.sqrt(n_exp * n_trees)
        plt.fill_between(np.arange(n_simulations), avg_diff_uct - err,
                         avg_diff_uct + err, alpha=.5)
        max_diff_uct = max(max_diff_uct, avg_diff_uct.max())

        regret = np.load(subfolder_name + '/regret_%s.npy' % (alg))
        avg_regret = regret.mean(0)
        plt.subplot(3, len(k), 2 * len(k) + 1 + count_plot % len(k))
        if count_plot == 0:
            plt.ylabel(r'$R$', fontsize='xx-large')
        plt.plot(avg_regret, linewidth=3)
        err = 2 * np.std(regret.reshape(n_exp * n_trees, n_simulations),
                         axis=0) / np.sqrt(n_exp * n_trees)
        plt.fill_between(np.arange(n_simulations), avg_regret - err,
                         avg_regret + err, alpha=.5)
        max_regret = max(max_regret, avg_regret.max())
        plt.xlabel('# Simulations', fontsize='xx-large')
        plt.xticks([0, 5000, 10000], ['0', '5e3', '10e3'], fontsize='xx-large')
        plt.yticks(fontsize='xx-large')
        plots = [max_diff, max_diff_uct, max_regret]

    # plt.legend([alg.upper() for alg in algs], fontsize='xx-large', loc="upper center", bbox_to_anchor=(-0.3, -0.3), ncol=len(algs), frameon=False)

    for i in range(3):
        plt.subplot(3, len(k), count_plot + 1 + i * len(k))
        plt.grid()
        plt.ylim(0, plots[i])

    count_plot += 1

plt.subplot(3, len(k), 3 * len(k) - 2)
plt.legend([alg.upper() for alg in algs], fontsize='xx-large', loc="upper center",
           bbox_to_anchor=(0.3, -0.3), ncol=len(algs), frameon=False)

# HEATMAPS
diff = np.load(folder_name + '/diff_heatmap.npy')
diff_uct = np.load(folder_name + '/diff_uct_heatmap.npy')
regret = np.load(folder_name + '/regret_heatmap.npy')

diffs = [diff, diff_uct, regret]
titles_diff = [r'$\varepsilon_\Omega$', r'$\varepsilon_{UCT}$', 'R']
for t, d in zip(titles_diff, diffs):
    fig, axs = plt.subplots(nrows=2, ncols=3)
    fig.suptitle(t, fontsize='xx-large')
    max_d = d.max()
    for i, ax in enumerate(axs.flat):
        im = ax.imshow(d[i], cmap=plt.get_cmap('inferno'))
        ax.set_title(algs[i].upper(), fontsize='xx-large')
        ax.set_xticks(np.arange(len(d_heat)))
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize('xx-large')
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize('xx-large')
        ax.set_yticks(np.arange(len(k_heat)))
        ax.set_xticklabels(d_heat)
        ax.set_yticklabels(k_heat)
        im.set_clim(0, max_d)
    # cb_ax = fig.add_axes([0.7, 0.15, 0.025, 0.7])
    cb_ax = fig.add_axes([.93, .15, .025, .7])
    cbar = fig.colorbar(im, cax=cb_ax)
    # cbar = fig.colorbar(im, orientation="horizontal", pad=0.2)
    for t in cbar.ax.get_yticklabels():
        t.set_fontsize('xx-large')

plt.show()
