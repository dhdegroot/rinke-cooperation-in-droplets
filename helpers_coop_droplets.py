import numpy as np
import os
import pandas as pd
import scipy
import seaborn as sns
from itertools import product
from matplotlib import pyplot as plt
from scipy.special import gammaln
from scipy.stats import poisson


def findTriplets(lst, key):
    def valid(val):
        return sum(val) == key

    return list(filter(valid, list(product(lst, repeat=3))))


def log_factorial(x):
    """Returns the logarithm of x!
    Also accepts lists and NumPy arrays in place of x."""
    return gammaln(np.array(x) + 1)


def multinomial(xs, ps):
    # The following if else statement makes it work even when one or more of the ps is zero.
    if min(ps) == 0:
        delete_inds = []
        zero_prob_indices = np.where(ps == 0)[0]
        for ind in zero_prob_indices:
            if xs[ind] > 0:
                return 0.
            else:
                delete_inds.append(ind)

        xs = np.delete(xs, delete_inds, axis=0)
        ps = np.delete(ps, delete_inds, axis=0)

    n = sum(xs)
    xs, ps = np.array(xs), np.array(ps)
    result = log_factorial(n) - sum(log_factorial(xs)) + sum(xs * np.log(ps))

    return np.exp(result)


def plot_pdf(val_freq_array, plot_type='Beautiful', xlabel='fraction cooperators', species_name='A'):
    vals = val_freq_array[:, 0]
    freqs = val_freq_array[:, 1]
    mean = np.sum(vals * freqs) / np.sum(freqs) if np.sum(freqs) != 0 else 0.

    bandwidth = 0.1 * vals.std() * vals.size ** (-1 / 5.)
    support = np.linspace(min(vals) - bandwidth, max(vals) + bandwidth, 200)
    supp_width = support[1] - support[0]

    if plot_type == 'Beautiful':
        kernels = []
        for ind, val_i in enumerate(vals):
            if ind % 1000 == 0:
                print("Calculating mu dist: '{0}' out of '{1}'".format(ind, len(vals)))
            kernel = scipy.stats.norm(val_i, bandwidth).pdf(support)
            kernel = kernel * freqs[ind]
            kernels.append(kernel)

        density = np.sum(kernels, axis=0)
        density /= scipy.integrate.trapz(density, support)
    elif plot_type == "Fast":
        density = np.zeros(len(support))
        for ind, supp_i in enumerate(support):
            supp_i_lb = supp_i - supp_width / 2
            supp_i_ub = supp_i + supp_width / 2
            density[ind] = np.sum(freqs[np.where((vals > supp_i_lb) & (vals <= supp_i_ub))])

    if plot_type != 'None':
        plt.figure()
        plt.plot(support, density)
        plt.xlabel(xlabel)
        plt.ylabel('Probability distribution')
        plt.title('PDF for ' + species_name)

    return mean


def calc_for_one_avg_nt(simu_dict, avg_nt=8, PRINT_ALOT=False, spec_names=['a', 'b', 'c']):
    freqs = simu_dict['freqs']
    CC0 = simu_dict['CC0']
    CCA_ind = simu_dict['CCA_ind']
    CCB_ind = simu_dict['CCB_ind']
    CCC_ind = simu_dict['CCC_ind']
    adv_cheat = simu_dict['adv_cheat']

    """First, find the range of the number of cells we expect in droplets"""
    nt_range = np.arange(poisson.ppf(0.0001, avg_nt), poisson.ppf(0.9999, avg_nt)).astype(int)
    droplet_df = pd.DataFrame(
        columns=['na', 'nb', 'nc', 'prob_droplet', 'pa', 'pb', 'pc', 'coop_frac', 'mua', 'mub', 'muc'])

    """Then create all possible droplet compositions for one number of cells"""
    for nt in nt_range:
        if nt % 10 == 0:
            if PRINT_ALOT:
                print("Calculated everything for droplets with less than '{0}' cells".format(nt))
        prob_nt = poisson.pmf(nt, avg_nt)
        droplets = findTriplets(np.arange(0, nt + 1), nt)
        for droplet in droplets:
            na, nb, nc = droplet
            prob_droplet = prob_nt * multinomial([na, nb, nc], freqs)

            # Calculate prob of cell of species to be in this droplet (according to maintext-file)
            # The first part is necessary if one of the freqs is 0
            freqs_corrected = freqs.copy()
            if any(freqs == 0):
                zero_freq_inds = np.where(freqs == 0)[0]
                for ind in zero_freq_inds:
                    freqs_corrected[ind] = 1  # This evades dividing through zero, result will be zero anyhow
            p_species = np.asarray([na, nb, nc]) / (freqs_corrected * avg_nt) * prob_droplet

            # Find fraction of cooperator pairs
            denom = 2 * min(na, nb) + nc
            coop_frac = 0.0 if denom == 0 else (2 * min(na, nb)) / denom

            # Find growth rates for all species in this droplet
            # Growth factor option 1
            # end_ab = CC0 * coop_frac * (1 / 2) * (1 - (nc / nt)) if nt != 0 else 0.
            # mua = (1 / na) * end_ab if na != 0 else 0.
            # mub = (1 / nb) * end_ab if nb != 0 else 0.
            # muc = (1 / nc) * (CC0 * coop_frac + CCC_ind) * (nc / nt) if nc != 0 else 0.

            # Find growth rates for all species in this droplet
            # Growth factor option 2
            # end_ab = CC0 * coop_frac * (1 / 2) * coop_frac if nt != 0 else 0.
            # mua = (1 / na) * end_ab if na != 0 else 0.
            # mub = (1 / nb) * end_ab if nb != 0 else 0.
            # muc = (1 / nc) * (CC0 * coop_frac + CCC_ind) * (1 - coop_frac) if nc != 0 else 0.

            # Find growth rates for all species in this droplet
            # Growth factor option 3 (best option)
            end_fc = min(1, (1 + adv_cheat) * (nc / nt) - adv_cheat * (nc / nt) ** 2 if nt != 0 else 0.)
            end_fab = (1 / 2) * (1 - end_fc)

            mua = max((1 - coop_frac)* (1 / na)* CCA_ind + coop_frac * (1/na) * CC0 * end_fab,1) if na != 0 else 0.
            mub = max((1 - coop_frac) * (1 / nb) * CCB_ind + coop_frac * (1 / nb) * CC0 * end_fab,1) if nb != 0 else 0.
            muc = max((1 - coop_frac) * (1 / nc) * CCC_ind + coop_frac * (1 / nc) * CC0 * end_fc,1) if nc != 0 else 0.

            droplet_df = droplet_df.append(
                {'na': na, 'nb': nb, 'nc': nc, 'prob_droplet': prob_droplet, 'pa': p_species[0], 'pb': p_species[1],
                 'pc': p_species[2], 'coop_frac': coop_frac, 'mua': mua, 'mub': mub, 'muc': muc}, ignore_index=True)

    # Replace all nans by zero. These nans occur when no cells are around, so growth rate should be zero then.
    return droplet_df


def calc_for_one_simu(simu_ind, simu_dict, avg_nt_range, spec_names=['a', 'b', 'c'], MAKE_PLOTS=False, PRINT_ALOT=False,
                      SAVE_FIGURES=False, MAKE_EACH_SIMU_FIGURE=False):
    working_dir = os.getcwd()
    if type(avg_nt_range) is not np.ndarray:
        avg_nt_range = np.array([avg_nt_range])

    G_array = np.zeros((avg_nt_range.size, 4))
    end_freq_array = np.zeros((avg_nt_range.size, 4))
    G_array[:, 0] = avg_nt_range
    end_freq_array[:, 0] = avg_nt_range

    for nt_ind, avg_nt in enumerate(avg_nt_range):
        if nt_ind % 10 == 9:
            print("Starting calculation for the '{0}'th lambda".format(nt_ind + 1))

        """Calculate for one choice of avg_nt a droplet_dataframe, and the average growth rate"""
        droplet_df_simu = calc_for_one_avg_nt(simu_dict=simu_dict, avg_nt=avg_nt)

        # Plot probability distribution for each species of being in a droplet with pairs of cooperators
        # And the probability distribution for the growth rates, and calculate average growth in the meantime
        plot_type = 'Fast' if MAKE_PLOTS else 'None'
        for spec_ind, spec in enumerate(spec_names):
            val_freq_coop_frac = np.hstack((droplet_df_simu[['coop_frac']], droplet_df_simu[['p' + spec]]))
            plot_pdf(val_freq_coop_frac, xlabel='fraction cooperators', species_name=spec, plot_type=plot_type)
            if SAVE_FIGURES:
                plt.savefig(os.path.join(working_dir, "results", "pdf_frac_coop_" + spec + ".png"))

            val_freq_G = np.hstack((droplet_df_simu[['mu' + spec]], droplet_df_simu[['p' + spec]]))
            G_array[nt_ind, 1 + spec_ind] = plot_pdf(val_freq_G, xlabel='growth factor', species_name=spec,
                                                     plot_type=plot_type)
            if SAVE_FIGURES:
                plt.savefig(os.path.join(working_dir, "results", "pdf_G_" + spec + ".png"))

    # G_diff_avg_coop_min_cheater = np.zeros((G_array.shape[0],1))
    G_diff_avg_coop_min_cheater = 0.5 * (G_array[:, 1] + G_array[:, 2]) - G_array[:, 3]
    # G_array = np.concatenate((G_array, 0.5 * (G_array[:, 1] + G_array[:, 2]) - G_array[:, 3]))
    end_freq_array[:, 1:] = np.tile(simu_dict['freqs'], (end_freq_array.shape[0], 1)) * G_array[:, 1:]
    norm_column = np.sum(end_freq_array[:, 1:], axis=1)
    norm_column[norm_column == 0] = 1
    norm_column = norm_column[:, np.newaxis]
    end_freq_array[:, 1:] = end_freq_array[:, 1:] / np.tile(norm_column, (1, 3))

    G_array = np.concatenate((G_array, int(simu_ind) * np.ones((avg_nt_range.size, 1)).astype(int)), axis=1)
    end_freq_array = np.concatenate((end_freq_array, int(simu_ind) * np.ones((avg_nt_range.size, 1)).astype(int)),
                                    axis=1)
    G_df_simu = pd.DataFrame(data=G_array, columns=['lambda', 'A', 'B', 'C', 'simulation'])
    end_freq_df_simu = pd.DataFrame(data=end_freq_array, columns=['lambda', 'A', 'B', 'C', 'simulation'])
    G_df_simu['coop_advantage'] = G_diff_avg_coop_min_cheater
    G_df_simu_tidy = pd.melt(G_df_simu, ['lambda', 'simulation'], var_name='species', value_name='G')
    end_freq_df_simu_tidy = pd.melt(end_freq_df_simu, ['lambda', 'simulation'], var_name='species',
                                    value_name='end_freq')

    if MAKE_EACH_SIMU_FIGURE:
        ax = sns.lineplot(x="lambda", y="G", hue="species", data=G_df_simu_tidy)
        plt.savefig(os.path.join(working_dir, "results", "growth_dep_on_lambda.png"))

        plt.show()

    return G_df_simu_tidy, end_freq_df_simu_tidy


def get_starting_parameters():
    freqs = np.asarray([5 / 12, 5 / 12, 2 / 12])
    CC0 = 750
    CCA_ind = 50
    CCB_ind = 50
    CCC_ind = 100
    adv_cheat = 2/5

    return freqs, CC0, CCA_ind, CCB_ind, CCC_ind, adv_cheat


def plot_stacked_bars(x_variable, y_variable, **kwargs):
    ax = plt.gca()
    data = kwargs.pop("data")
    species = kwargs.pop("species")
    new_color = kwargs.pop("new_color")
    data = data[data['species'] == species]
    sns.barplot(x=x_variable, y=y_variable, ax=ax, data=data, color=new_color)


def mullerplot(x_variable, y_variable, **kwargs):
    ax = plt.gca()
    data = kwargs.pop("data")
    data = data.sort_values('lambda')
    x = np.unique(np.sort(data['lambda'])).tolist()
    ya = data[data['species'] == 'A'][['end_freq']].values.flatten()
    yb = data[data['species'] == 'B'][['end_freq']].values.flatten()
    yc = data[data['species'] == 'C'][['end_freq']].values.flatten()
    new_colors = kwargs.pop("new_colors")
    y = np.vstack((ya, yb, yc)).tolist()

    ax.stackplot(x, y, colors=new_colors)


def mullerplot_fig2(x_variable, y_variable, **kwargs):
    ax = plt.gca()
    data = kwargs.pop("data")
    data = data.sort_values('iteration')
    x = np.unique(np.sort(data['iteration'])).tolist()
    ya = data[data['species'] == 'A'][['end_freq']].values.flatten()
    yb = data[data['species'] == 'B'][['end_freq']].values.flatten()
    yc = data[data['species'] == 'C'][['end_freq']].values.flatten()
    new_colors = kwargs.pop("new_colors")
    y = np.vstack((ya, yb, yc)).tolist()

    ax.stackplot(x, y, colors=new_colors)
