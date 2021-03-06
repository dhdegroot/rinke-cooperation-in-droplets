from helpers_coop_droplets import *

"""Constants"""
SAVE_LAST_FIGURE = True
SAVE_FIGURES = False
MAKE_EACH_SIMU_FIGURE = False
PRINT_ALOT = False
MAKE_PLOTS = True
working_dir = os.getcwd()
N_SIMUS = 100
np.random.seed(3141)
spec_names = ['a', 'b', 'c']

# Get parameters. These can be changed in helpers_coop_droplets file. For the figures, I have used:
# freqs = np.asarray([5 / 12, 5 / 12, 2 / 12])
# CC0 = 750
# CCA_ind = 50
# CCB_ind = 50
# CCC_ind = 100
# adv_cheat = 2 / 5
freqs, CC0, CCA_ind, CCB_ind, CCC_ind, adv_cheat = get_starting_parameters()

first_avg_nt = .05
last_avg_nt = 8
n_avg_nt = 40

# sims_df = pd.DataFrame(columns=['freqs', 'CC0', 'CCC_ind'])
simu_dict_list = []

"""Generate set of parameters for all simulations"""
for ind in range(N_SIMUS):
    freqs_simu = np.random.rand(3)
    freqs_simu /= sum(freqs_simu)
    diff_between_coops = np.random.normal(loc=0.5, scale=0.1, size=1)[0]
    sum_coops = freqs_simu[0] + freqs_simu[1]
    freqs_simu[0] = diff_between_coops * sum_coops
    freqs_simu[1] = (1 - diff_between_coops) * sum_coops

    CC0_simu = CC0
    CCC_ind_simu = CC0_simu * max(np.random.uniform(low=CCC_ind / (5 * CC0), high=(CCC_ind * 1.2) / CC0, size=1), 0)[0]
    CCA_ind_simu = max(np.random.uniform(low=0, high=CCC_ind_simu, size=1), 0)[0]
    CCB_ind_simu = max(np.random.uniform(low=0, high=CCC_ind_simu, size=1), 0)[0]
    adv_cheat_simu = adv_cheat * max(np.random.normal(loc=1, scale=0.2, size=1), 0)[0]
    simu_dict_list.append(
        {'freqs': freqs_simu, 'CC0': CC0_simu, 'CCC_ind': CCC_ind_simu, 'CCA_ind': CCA_ind_simu,
         'CCB_ind': CCB_ind_simu, 'adv_cheat': adv_cheat_simu})

avg_nt_range = np.exp(np.linspace(np.log(first_avg_nt), np.log(last_avg_nt), n_avg_nt))
if avg_nt_range.size > 2:
    MAKE_PLOTS = False
    SAVE_FIGURES = False

# Initialize dataframe in which we are going to store growth factor data
G_df = pd.DataFrame(columns=['lambda', 'simulation', 'species', 'G'])
end_freq_df = pd.DataFrame(columns=['lambda', 'simulation', 'species', 'end_freq'])

# Run all different simulations
for simu_ind in range(N_SIMUS):
    print("Starting simulation '{0}'".format(simu_ind))
    simu_dict = simu_dict_list[simu_ind]

    # Calculate growth dataframe for one simulation
    G_df_simu_tidy, end_freq_df_simu_tidy = calc_for_one_simu(simu_ind, simu_dict, avg_nt_range, spec_names=spec_names,
                                                              MAKE_PLOTS=MAKE_PLOTS,
                                                              PRINT_ALOT=PRINT_ALOT, SAVE_FIGURES=SAVE_FIGURES,
                                                              MAKE_EACH_SIMU_FIGURE=MAKE_EACH_SIMU_FIGURE)
    G_df = G_df.append(G_df_simu_tidy)
    end_freq_df = end_freq_df.append(end_freq_df_simu_tidy)

"""Store G_df, with parameters added for each simulation"""
G_df['freqa'] = G_df['freqb'] = G_df['freqc'] = 0
G_df['CC0'] = G_df['CCC_ind'] = G_df['CCA_ind'] = G_df['CCB_ind'] = G_df['adv_cheat'] = 0
for simu_ind in range(N_SIMUS):
    simu_dict = simu_dict_list[simu_ind]
    for key in simu_dict:
        if key == 'freqs':
            G_df.loc[G_df.simulation == simu_ind, 'freqa'] = simu_dict[key][0]
            G_df.loc[G_df.simulation == simu_ind, 'freqb'] = simu_dict[key][1]
            G_df.loc[G_df.simulation == simu_ind, 'freqc'] = simu_dict[key][2]
        else:
            G_df.loc[G_df.simulation == simu_ind, key] = simu_dict[key]

G_df.to_csv(os.path.join(working_dir, "results", "figure3_data_G_df_manylambdas_varyparameters.csv"), index=False,
            header=True)

"""Make plot"""
ax = sns.lineplot(x="lambda", y="G", hue="simulation", data=G_df[G_df.species == 'coop_advantage'])
plt.savefig(os.path.join(working_dir, "results", "Figure3_manylambda_sampledparameters.png"))
plt.show()
