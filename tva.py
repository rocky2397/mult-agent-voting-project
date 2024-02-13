"""
The Tactical Voter Analyst (TVA) for the course: Multi-Agent Systems

@authors: Diyon Wickrameratne, Kaspar Kallast, Luca Forte, Lucas Padolevicius, Olmo Denegri

"""

import importlib
import os.path
import random
import numpy as np
from copy import copy

from agents.agent import Agent, get_winner


class TVA:
    """
    Tactical Voting Analyst class
    """

    def __init__(self, candidate_string, voting_scheme, num_agents, advanced_tva):
        """
        The constructor for the TVA

        When initialised, this constructor creates a dictionary of the candidates from the candidate string.
        The class then imports the respective voting scheme - raises an exception if not found in voting_schemes.py
        It also creates the specified number of agents

        :param candidate_string: A string of candidates, for example: "ABCDEFG"
        :param voting_scheme: A string indicating the type of voting
        :param num_agents: An integer for the number of agents in the election
        """

        self.candidate_string = candidate_string
        self.candidates = self.create_candidates()
        self.num_agents = num_agents
        self.voting_scheme = voting_scheme
        self.is_atva = advanced_tva

        module = importlib.import_module("voting.voting_schemes")

        # Check if module has the voting scheme
        if not hasattr(module, voting_scheme):
            raise Exception(f"{voting_scheme} has not been implemented")

        self.scheme = getattr(module, voting_scheme)

        self.agents = self.create_agents(num_agents)

        self.results = {}

        self.happinesses = {}

    def run(self):
        """
        A void function to run the selected voting scheme

        :return: void
        """
        self.results = self.scheme().run_scheme(self.candidates, self.agents)

    def get_agents(self):
        """
        :return: Returns a list of agent objects in the election
        """
        return self.agents

    def create_agents(self, num_agents):
        """
        Creates a specified number of agents

        :param num_agents: An integer indicating the number of agents to create
        :return: Returns a list of agent objects
        """
        agents = []

        for i in range(num_agents):
            agents.append(Agent(f"Agent{i + 1}", self.generate_preferences(), self.scheme))

        return agents

    def generate_preferences(self):
        """
        Generates a randomly shuffled string from the candidate string. This is used to generate random
        agent preferences

        :return: Returns a randomly shuffled string
        """
        return "".join(random.sample(self.candidate_string, len(self.candidate_string)))

    def create_candidates(self):
        """
        Creates a dictionary of the candidates in the election. It initially sets all votes to 0

        :return: Returns a dictionary of the candidates, will all their votes set to 0
        """

        candidate_dict = {}

        for letter in self.candidate_string:
            candidate_dict[letter] = 0

        return candidate_dict

    def get_preference_matrix(self):
        """
        Creates a matrix representation of all agents' preferences. Each column in the matrix represents the
        preferences of an agent, in preference order

        :return: Returns a nested list (or matrix) representing all preferences of all agents
        """

        matrix = []

        for agent in self.agents:

            row = [agent.name]

            for candidate in agent.get_preferences():
                row.append(f"{candidate}")

            matrix.append(row)

        np_matrix = np.array(matrix)

        return np_matrix.transpose()

    def get_overall_happiness(self):

        for a in self.agents:
            happiness = a.get_happiness(self.results)

            for happiness_computation in happiness:
                if happiness_computation not in self.happinesses:
                    self.happinesses[happiness_computation] = []
                self.happinesses[happiness_computation].append(happiness[happiness_computation])

        overall_happiness = {}

        for happiness_computation in self.happinesses:
            overall_happiness[happiness_computation] = sum(self.happinesses[happiness_computation]) / len(
                self.happinesses[happiness_computation])

        return overall_happiness

    def get_report(self):
        """
        Creates a report of the entire election, and highlights the most important information
        :return: Returns a string reporting the important info of the election
        """

        string = ""

        preference_happiness_count = 0
        social_index_count = 0

        string += "##### ELECTION RESULTS #####\n\n"
        string += f"Voting scheme: {self.voting_scheme}\n"

        agent_string = ""
        for a in self.agents:
            agent_string += str(a) + " "

        string += f"The voters: {agent_string}\n"

        string += f"The voters preferences are summarised below\n"
        string += str(self.get_preference_matrix()) + "\n"

        string += f"Here are all the results\n"
        string += str(self.results) + "\n"
        string += f"The winner of this election is: {get_winner(self.results)}\n"

        string += "The happiness of all agents are:\n"

        for a in self.agents:
            happiness = a.get_happiness(self.results)
            string += f"{a.name} : {happiness} %\n"

        overall_happiness = self.get_overall_happiness()

        string += f"The overall happiness is: {overall_happiness}\n\n"

        string += "##### TACTICAL VOTING #####\n\n"

        happiness_threshold = 99

        # Check how agents would change their votes depending on happiness
        for a in self.agents:

            happiness_dict = a.get_happiness(self.results)

            string += f"For {str(a)} with initial happiness: {happiness_dict}\n"

            if happiness_dict["H_si"] > happiness_threshold and happiness_dict["H_p"] > happiness_threshold:

                string += f"{str(a)} was happy and didn't change their preferences\n\n"

            else:
                tact_dictionary = self.scheme().tactical_options(a, copy(self))

                string += f"For {str(a)}, the tactical options are:\n"

                for key in tact_dictionary:

                    if len(tact_dictionary[key]) < 1:
                        string += f"{str(a)} was unhappy ({key}), but did not have any tactical voting strategy\n\n"
                        continue

                    if key == "H_p":
                        preference_happiness_count += 1

                    if key == "H_si":
                        social_index_count += 1

                    for option in tact_dictionary[key]:
                        string += f"Type of happiness: {key} \n" \
                                  f"Option:{option} new preferences: {tact_dictionary[key][option][0]} , " \
                                  f"new winner: {tact_dictionary[key][option][1]}, " \
                                  f"new voting outcome: {tact_dictionary[key][option][2]}, " \
                                  f"new {key}: {tact_dictionary[key][option][3][key]}, " \
                                  f"new overall {key}: {tact_dictionary[key][option][4][key]}\n"

            string += "------------------------\n"

        string += f"Risk based on H_p: {(preference_happiness_count / len(self.agents))*100}%\n"
        string += f"Risk based on H_si: {(social_index_count / len(self.agents))*100}%\n\n"

        if self.is_atva:

            string += f"##### ADVANCED TVA: Counter voting strategies #####\n\n"

            for a in self.agents:

                counter_voting_set = self.scheme().counter_vote(a, copy(self))

                string += f"For {str(a)} \n"

                # element is a list = [other_agent, their prefs (list), new results (list),
                # tactical options of agent after the other agents prefs (dict)]
                for happiness_type in counter_voting_set:
                    string += f"\tConsidering {happiness_type}:\n\n"

                    for sublist in counter_voting_set[happiness_type]:

                        other_agent = sublist[0]
                        other_prefs = sublist[1]
                        new_results = sublist[2]
                        new_tact_options = sublist[3]

                        if other_prefs is None:
                            string += f"\t{other_agent} didn't have any tactical voting strategies, so {a} isn't affected\n"
                            string += "--------------------------\n"
                            continue

                        string += f"\tFor the type of happiness: {happiness_type}\n"
                        string += f"\tIf {str(other_agent)} decides to go with new preferences: {other_prefs}\n"
                        string += f"\tThe new results would be: {new_results}\n"

                        if len(new_tact_options) < 1:
                            string += f"\tBut {str(a)} would not have any tactical options for this counter\n"
                            string += "--------------------------\n"
                            continue

                        string += f"\tTherefore, {str(a)} has these tactical options:\n"

                        for option in new_tact_options:
                            string += f"\tType of happiness {happiness_type}: Option:{option} new preferences: {new_tact_options[option][0]} , " \
                                      f"new winner: {new_tact_options[option][1]}, " \
                                      f"new voting outcome: {new_tact_options[option][2]}, " \
                                     f"new {happiness_type}: {new_tact_options[option][3][happiness_type]}, " \
                                     f"new overall {happiness_type}: {new_tact_options[option][4][happiness_type]}\n"
                        string += "--------------------------\n"

            string += f"##### ADVANCED TVA: Concurrent voting strategies #####\n\n"

            new_social_outcomes = self.scheme().concurrent_vote(copy(self))

            for happiness_type in new_social_outcomes:

                string += f"For {happiness_type}, the new social outcome if all agents voted concurrently:\n"

                winner = new_social_outcomes[happiness_type][0]
                string += f"The new winner is: {winner} if the following agents voted:\n"

                agent_list = new_social_outcomes[happiness_type][2:]
                for nested_list in agent_list:

                    string += f"{str(nested_list[0])}: {nested_list[1]}, is original: {nested_list[2]}\n"

        return string


def create_and_run_election(n_voters, n_candidates, voting_scheme, is_advanced):

    candidates = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    candidates = candidates[:n_candidates]

    election = TVA(candidates, voting_scheme, n_voters, is_advanced)
    election.run()

    risk_preference_happiness_count = 0
    risk_social_index_count = 0

    basic_tva_happiness_increases = {"H_p": 0, "H_si": 0}

    for agent in election.get_agents():

        old_happiness = agent.get_happiness(election.results)

        tactical_dictionary = election.scheme().tactical_options(agent, election)

        for key in tactical_dictionary:
            prev_happiness = old_happiness[key]
            if key == "H_p" and len(tactical_dictionary[key]) > 0:
                risk_preference_happiness_count += 1
                maximum_tactical_happiness = 0
                for index in tactical_dictionary[key]:
                    tactical_option = tactical_dictionary[key][index]
                    new_happiness = tactical_option[3][key]
                    if new_happiness > maximum_tactical_happiness:
                        maximum_tactical_happiness = new_happiness
                basic_tva_happiness_increases[key] += maximum_tactical_happiness - prev_happiness
            elif key == "H_si" and len(tactical_dictionary[key]) > 0:
                risk_social_index_count += 1
                maximum_tactical_happiness = 0
                for index in tactical_dictionary[key]:
                    tactical_option = tactical_dictionary[key][index]
                    new_happiness = tactical_option[3][key]
                    if new_happiness > maximum_tactical_happiness:
                        maximum_tactical_happiness = new_happiness
                basic_tva_happiness_increases[key] += maximum_tactical_happiness - prev_happiness

    if basic_tva_happiness_increases["H_p"] != 0:
        total_increase = basic_tva_happiness_increases["H_p"]
        basic_tva_happiness_increases["H_p"] = total_increase/risk_preference_happiness_count
    else:
        basic_tva_happiness_increases["H_p"] = 0

    if basic_tva_happiness_increases["H_si"] != 0:
        total_increase = basic_tva_happiness_increases["H_si"]
        basic_tva_happiness_increases["H_si"] = total_increase/risk_social_index_count
    else:
        basic_tva_happiness_increases["H_si"] = 0

    risk_preference_happiness_count = risk_preference_happiness_count / n_voters
    risk_social_index_count = risk_social_index_count / n_voters

    if is_advanced:

        '''
        for Concurrent Voting
        '''

        election_copy = copy(election)
        concurrent_voting_outcome = election_copy.scheme().concurrent_vote(election_copy)
        conc_voting_happiness_increases = {"H_p": [0, 0], "H_si": [0, 0]}
        conc_overall_happiness = {"H_p": 0, "H_si": 0}

        for key in concurrent_voting_outcome:

            election_copy.results = concurrent_voting_outcome[key][1]
            conc_overall_happiness[key] = election_copy.get_overall_happiness()[key]

            for agent in [tactical_agent for tactical_agent in concurrent_voting_outcome[key][2:]]:
                old_happiness = agent[0].get_happiness(election.results)[key]
                new_happiness = agent[0].get_happiness(election_copy.results)[key]
                conc_voting_happiness_increases[key][0] += new_happiness - old_happiness
                conc_voting_happiness_increases[key][1] += 1

        for key in conc_voting_happiness_increases:
            conc_voting_happiness_increases[key] = conc_voting_happiness_increases[key][0]/conc_voting_happiness_increases[key][1]

        '''
        for Counter Strategic Voting
        '''

        counter_voting_dict_overall = {"H_p": [0, 0], "H_si": [0, 0]}
        counter_voting_dict_increases = {"H_p": [0, 0], "H_si": [0, 0]}
        agents_copy = [copy(agent) for agent in election.get_agents()]

        for agent in agents_copy:

            election_copy = copy(election)
            old_happiness = agent.get_happiness(election.results)

            counter_voting_options = election_copy.scheme().counter_vote(agent, election_copy)

            for key in counter_voting_options:
                for counter_set in counter_voting_options[key]:
                    if counter_set[3] is not None:
                        if len(counter_set[3]) > 0:
                            maximum_tactical_happiness = 0
                            best_tactical_option = None
                            for index in counter_set[3]:
                                tactical_option = counter_set[3][index]
                                if tactical_option[3][key] > maximum_tactical_happiness:
                                    maximum_tactical_happiness = tactical_option[3][key]
                                    best_tactical_option = tactical_option

                            counter_voting_dict_overall[key][0] += best_tactical_option[4][key]
                            counter_voting_dict_increases[key][0] += best_tactical_option[3][key] - old_happiness[key]

                        else:

                            election_copy.results = counter_set[4]
                            new_overall_happiness = election_copy.get_overall_happiness()[key]
                            counter_voting_dict_overall[key][0] += new_overall_happiness
                            new_happiness = agent.get_happiness(counter_set[4])[key]
                            counter_voting_dict_increases[key][0] += new_happiness - old_happiness[key]

                        counter_voting_dict_overall[key][1] += 1
                        counter_voting_dict_increases[key][1] += 1

        for key in counter_voting_dict_overall:
            if counter_voting_dict_overall[key][1] != 0:
                counter_voting_dict_overall[key] = counter_voting_dict_overall[key][0]/counter_voting_dict_overall[key][1]
            else:
                counter_voting_dict_overall[key] = None

        for key in counter_voting_dict_increases:
            if counter_voting_dict_increases[key][1] != 0:
                counter_voting_dict_increases[key] = counter_voting_dict_increases[key][0]/counter_voting_dict_increases[key][1]
            else:
                counter_voting_dict_increases[key] = None

    return election.get_overall_happiness(), risk_preference_happiness_count, risk_social_index_count, \
           basic_tva_happiness_increases, conc_overall_happiness, conc_voting_happiness_increases,\
           counter_voting_dict_overall, counter_voting_dict_increases


def run_tests(data_folder, tests, voting_scheme, show_atva_features):

    print("##########################TESTS########################################")

    n_voters_test = [2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 50]
    n_candidates_test = [3, 4, 5, 6, 7, 8, 9, 10]

    print(f"Running tests for {voting_scheme}...")

    for curr_n_candidates in n_candidates_test:
        n_candidates = curr_n_candidates
        for curr_n_voters in n_voters_test:
            n_voters = curr_n_voters

            print(f"Running for {n_candidates} candidates with {curr_n_voters} voters")

            j, k = 0, 0
            total_basic_overall_happiness = {"H_p": 0, "H_si": 0}
            total_risk_percentage_my_preference = 0
            total_risk_percentage_social_outcome = 0
            total_basic_happiness_increase = {"H_p": 0, "H_si": 0}
            total_conc_overall_happiness = {"H_p": 0, "H_si": 0}
            total_conc_voting_happiness_increases = {"H_p": 0, "H_si": 0}
            counter_voting_dict_overall = {"H_p": 0, "H_si": 0}
            counter_voting_dict_increases = {"H_p": 0, "H_si": 0}

            for i in range(tests):

                election_results = create_and_run_election(n_voters, n_candidates, voting_scheme, show_atva_features)

                for key in election_results[0]:
                    total_basic_overall_happiness[key] += election_results[0][key]

                total_risk_percentage_my_preference += election_results[1]
                total_risk_percentage_social_outcome += election_results[2]

                for key in election_results[3]:
                    elect_3 = election_results[3][key]
                    total_basic_happiness_increase[key] += elect_3

                for key in election_results[4]:
                    elect_4 = election_results[4][key]
                    total_conc_overall_happiness[key] += elect_4

                for key in election_results[5]:
                    elect_5 = election_results[5][key]
                    total_conc_voting_happiness_increases[key] += elect_5

                for key in election_results[6]:
                    elect_6 = election_results[6][key]
                    if elect_6 is not None:
                        counter_voting_dict_overall[key] += elect_6
                        if key == "percentage_my_preference":
                            j += 1
                        else:
                            k += 1

                for key in election_results[7]:
                    elect_7 = election_results[7][key]
                    if elect_7 is not None:
                        counter_voting_dict_increases[key] += elect_7

            if not os.path.exists(data_folder + voting_scheme):
                os.mkdir(data_folder + voting_scheme)

            with open(data_folder + voting_scheme + "/results_" + voting_scheme + "_n_candidates_" + str(
                            n_candidates) + "_n_voters_" + str(n_voters) + ".txt", "w") as out_file:

                out_file.write("Voting Scheme: " + voting_scheme)
                out_file.write("\n")

                basic_average_overall_happiness = {}
                for key in total_basic_overall_happiness:
                    basic_average_overall_happiness[key] = total_basic_overall_happiness[key] / tests

                out_file.write("basic_average_overall_happiness")
                out_file.write("\n")
                out_file.write(str(basic_average_overall_happiness))
                out_file.write("\n")

                out_file.write("Average tactical voting risk for percentage_my_preference: ")
                out_file.write("\n")
                out_file.write(str(total_risk_percentage_my_preference / tests))
                out_file.write("\n")
                out_file.write("Average tactical voting risk for percentage_social_index: ")
                out_file.write("\n")
                out_file.write(str(total_risk_percentage_social_outcome / tests))
                out_file.write("\n")

                basic_average_happiness_increase = {}
                for key in total_basic_happiness_increase:
                    basic_average_happiness_increase[key] = total_basic_happiness_increase[key] / tests

                out_file.write("basic_average_happiness_increase")
                out_file.write("\n")
                out_file.write(str(basic_average_happiness_increase))
                out_file.write("\n")

                conc_average_overall_happiness = {}
                for key in total_conc_overall_happiness:
                    conc_average_overall_happiness[key] = total_conc_overall_happiness[key] / tests

                out_file.write("conc_average_overall_happiness")
                out_file.write("\n")
                out_file.write(str(conc_average_overall_happiness))
                out_file.write("\n")

                conc_average_voting_happiness_increases = {}
                for key in total_conc_voting_happiness_increases:
                    conc_average_voting_happiness_increases[key] = total_conc_voting_happiness_increases[key] / tests

                out_file.write("conc_average_voting_happiness_increases")
                out_file.write("\n")
                out_file.write(str(conc_average_voting_happiness_increases))
                out_file.write("\n")

                counter_average_voting_dict_overall = {}
                for key in counter_voting_dict_overall:
                    if key == "percentage_my_preference" and j != 0:
                        counter_average_voting_dict_overall[key] = counter_voting_dict_overall[key] / j
                    elif k != 0:
                        counter_average_voting_dict_overall[key] = counter_voting_dict_overall[key] / k

                out_file.write("counter_average_voting_dict_overall")
                out_file.write("\n")
                out_file.write(str(counter_average_voting_dict_overall))
                out_file.write("\n")

                counter_average_voting_dict_increases = {}
                for key in counter_voting_dict_increases:
                    if key == "percentage_my_preference" and j != 0:
                        counter_average_voting_dict_increases[key] = counter_voting_dict_increases[key] / j
                    elif k != 0:
                        counter_average_voting_dict_increases[key] = counter_voting_dict_increases[key] / k

                out_file.write("counter_average_voting_dict_increases")
                out_file.write("\n")
                out_file.write(str(counter_average_voting_dict_increases))
                out_file.write("\n")

                out_file.write(str(j) + ", " + str(k))

    print(f"Tests were run for {voting_scheme}, and saved in {data_folder+voting_scheme}")


if __name__ == "__main__":

    # Change parameters as desired
    data_folder = "C:/Users/31618/Desktop/VUB/Scripting Languages/Projects/TacticalVotingAnalyst/"

    run_multiple_tests = False

    show_atva_features = True

    # Candidates are assumed to be letters of the alphabet
    candidates = "ABCDEFGIJK"

    # Voting schemes must be written out with the first letter capitalised; Plurality, AntiPlurality, VotingForTwo, Borda
    voting_scheme = "Borda"
    voters = 3

    # Runs election and prints out report
    election = TVA(candidates, voting_scheme, voters, show_atva_features)
    election.run()

    print(election.get_report())
    print("\n")

    # Here multiple elections can be run to see average results over multiple elections
    if run_multiple_tests:

        tests = 2

        run_tests(data_folder, tests, voting_scheme, show_atva_features)

    # In order to visualise results, please run mas_visualization.ipynb in a Jupyter environment
    # The notebook requires tests to be run for all voting schemes
