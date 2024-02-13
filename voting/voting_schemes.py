from abc import ABC, abstractmethod
from copy import copy
from agents.agent import get_winner, Agent
from strategies import strategies_borda
import sys

'''
TO DO: move get_tactical_overall_happiness anywhere else where it makes sense, for now it's here just for convenience sake
'''


def get_tactical_overall_happiness(tva_object, agent, agent_happiness, results_copy):
    happinesses = {}

    for other_agent in tva_object.get_agents():
        if other_agent != agent:
            other_happiness = other_agent.get_happiness(results_copy)
            for key in other_happiness:
                if key not in happinesses:
                    happinesses[key] = []
                happinesses[key].append(other_happiness[key])
        else:
            for key in agent_happiness:
                if key not in happinesses:
                    happinesses[key] = []
                happinesses[key].append(agent_happiness[key])

    for key in happinesses:
        happinesses[key] = sum(happinesses[key]) / len(happinesses[key])

    return happinesses


class VotingScheme(ABC):
    """
    Abstract class voting scheme
    """

    def run_scheme(self, candidates, agents):
        """
        This function tallies the overall votes for all the candidates, based on the agents' preferences

        :param candidates: A dictionary of the candidates in the election
        :param agents: A list of agents who are voting
        :return: Returns a dictionary of the tallied votes for each candidate
        """
        candidate_dict = copy(candidates)

        for agent in agents:

            preference_dict = agent.get_preferences()

            for key in preference_dict:
                candidate_dict[key] += preference_dict[key]

        return candidate_dict

    @abstractmethod
    def tally_personal_votes(self, preferences):
        """
        Abstract method for the voting schemes. Requires a dictionary of personal preferences from an agent
        It modifies the preference dictionary of a user

        :param preferences: A dictionary of an agent's preferences
        :return: void
        """
        pass

    def counter_ts_by_key(self, key, agent, other_agent, tva_object_copy, all_other_agents):
        """
        Returns a list containing an opposing agent to the agent of interest. The list contains the
        opposing agent, with their best tactical preference, the resulting outcome, and the
        possible tactical options of the agent to counter

        :param key: A string indicating the type of happiness
        :param agent: An agent object, for whom the counter tactical votes must be made
        :param other_agent: An agent object, who is the opposing agent
        :param tva_object_copy: A copy of the original tva object
        :param all_other_agents: A list of agent objects, excluding the opposing agent, and agent of interest
        :return: Returns a list as mentioned above. Type = [str, list, list, dict]
        """

        other_tactical_options = self.tactical_options(other_agent, tva_object_copy)

        # Hold original values to reset later
        original_options = other_agent.preferences
        original_results = tva_object_copy.results

        percentage_happiness_options = other_tactical_options[key]

        # If other agent has no tactical options, nothing to do
        if len(percentage_happiness_options) < 1:
            return [other_agent, None, None, None]

        best_option = None
        best_happiness = 0

        # Get the best tactical option of the other agent
        for option in percentage_happiness_options:

            sublist = percentage_happiness_options[option]
            happiness = sublist[3][key]

            if happiness > best_happiness:
                best_option = percentage_happiness_options[option]
                best_happiness = happiness

        '''
        TO DO: make the following work when best_option is never updated and is None
        '''

        best_preference = best_option[0]

        # Get the personal tally if the other agent had chosen their best tactical option
        best_preference_dictionary = {}
        for preference in best_preference:
            best_preference_dictionary[preference] = 0

        self.tally_personal_votes(best_preference_dictionary)
        other_agent.preferences = best_preference_dictionary

        new_list_agents = [agent, other_agent]
        for i in all_other_agents:
            if not i == other_agent:
                new_list_agents.append(i)

        # Get the social outcome if the other agent had chosen their best tactical option
        new_results = self.run_scheme(tva_object_copy.candidates, new_list_agents)
        new_results_list = sorted(new_results, key=new_results.get, reverse=True)
        tva_object_copy.results = new_results

        # Depending on the new social outcome, compute the agent's new tactical options
        counter_tactical_set = [other_agent, list(best_preference_dictionary.keys()),
                                new_results_list,
                                self.tactical_options(agent, tva_object_copy)[key],
                                new_results]

        # Reset to defaults so future elections aren't hindered by these changes
        tva_object_copy.results = original_results
        other_agent.preferences = original_options

        return counter_tactical_set

    def counter_vote(self, agent, tva_object_copy):
        """
        Computes the dictionary of counter votes for an agent, once each other agent has voted tactically.
        For example, when an election is run, each agent may have tactical voting strategies. If an agent was to apply
        their best strategic preferences, the agent of interest may be able to counter that strategic vote.

        This method returns a dictionary, whose indexes are the types of happiness. Each key has a list of lists. Each
        nested list contains an opposing agent, with their best tactical preference, the resulting outcome, and the
        possible tactical options of the agent to counter

        :param agent: An agent object, for whom the counter tactical votes must be made
        :param tva_object_copy: A copy of the original tva object
        :return: Returns a dictionary as mentioned above
        """

        counter_voting_options = {"H_p": [], "H_si": []}

        all_other_agents = [copy(a) for a in tva_object_copy.get_agents() if not a == agent]

        for other_agent in all_other_agents:
            counter_voting_options["H_p"].append(self.counter_ts_by_key("H_p",
                                                                        agent, other_agent,
                                                                        tva_object_copy,
                                                                        all_other_agents))

            counter_voting_options["H_si"].append(self.counter_ts_by_key("H_si",
                                                                         agent, other_agent,
                                                                         tva_object_copy,
                                                                         all_other_agents))

        return counter_voting_options

    def concurrent_vote(self, tva_object_copy):
        """
        Concurrent voting is when every agent decides to apply their tactical vote at the same time, thereby (maybe)
        changing the outcome of the election.

        :param tva_object_copy
        :returns - A dictionary with a list for the two types of happiness

        The following indexes in each list contains:
        0 - new winner
        1 - new social outcome
        2 -> n - a nested lists

        The following indexes in each nested list contains:
        0 - Agent object
        1 - Preference list of the agent
        2 - Boolean, True if preference list is the agent's original preferences, False if they are tactical
        """

        agent_best_pref = {"H_p": {}, "H_si": {}}
        social_outcome = {}

        # Get tactical options for each agent
        for a in tva_object_copy.get_agents():

            all_tact_options = self.tactical_options(a, tva_object_copy)

            for happiness_type in all_tact_options:
                # If no tactical options to begin with, do not update new preferences
                if len(all_tact_options[happiness_type]) < 1:
                    agent_best_pref[happiness_type][a] = list(a.get_preferences().keys())
                    continue

                best_option = None
                best_happiness = 0

                # Get the best tactical option of the agent
                for option in all_tact_options[happiness_type]:
                    sublist = all_tact_options[happiness_type][option]
                    new_prefs = sublist[0]
                    new_winner = sublist[1]
                    new_happiness = sublist[3][happiness_type]

                    # A concurrent vote is not considered if the new winner isn't an agent's best preferred
                    # candidate
                    if new_winner != new_prefs[0]:
                        agent_best_pref[happiness_type][a] = list(a.get_preferences().keys())
                        continue

                    if new_happiness > best_happiness:
                        best_option = sublist
                        best_happiness = new_happiness

                # Add best option to the dict. Sometimes
                if best_option is None:
                    agent_best_pref[happiness_type][a] = list(a.get_preferences().keys())
                else:
                    agent_best_pref[happiness_type][a] = best_option[0]

        # Run an election for each happiness type
        for happiness_type in agent_best_pref:

            all_agents = [agent for agent in agent_best_pref[happiness_type]]

            agents_original_prefs = {}

            # Save original preference
            for agent in all_agents:
                agents_original_prefs[agent] = agent.preferences

            for agent in all_agents:

                pref_dict = {}
                for candidate in agent_best_pref[happiness_type][agent]:
                    pref_dict[candidate] = 0

                # Tally votes with new prefs
                self.tally_personal_votes(pref_dict)
                agent.preferences = pref_dict

            new_results = self.run_scheme(tva_object_copy.candidates, all_agents)
            latest_winner = get_winner(new_results)

            # Revert to original preferences to perform boolean check below
            for agent in all_agents:
                agent.preferences = agents_original_prefs[agent]

            agent_list = [[agent, agent_best_pref[happiness_type][agent],
                           agent_best_pref[happiness_type][agent] == list(agent.get_preferences().keys())]
                          for agent in agent_best_pref[happiness_type]]

            agent_list.insert(0, latest_winner)
            agent_list.insert(1, new_results)

            social_outcome[happiness_type] = agent_list

        return social_outcome

    @abstractmethod
    def tactical_options(self, agent, tva_object):
        """
        Abstract function to change an agent's order of votes, depending on the winner. For each voting strategy, the
        agent is able to tactically change their votes to increase happiness. This function returns a dictionary
        containing all tactical options for a given voting strategy.

        The dictionary follows the structure:
        # TODO TO BE DECIDED. FOR NOW IT'S:
        # TODO <key> : <value>, where key = option number, and value is a list with three indices
        # TODO index 1 = new voting preference list
        # TODO index 2 = new winner because of this agent's new preference list
        # TODO index 3 = new happiness after subsequent re-election

        :param tva_object: A TVA object
        :param agent: The agent object for which tactical voting must be applied
        :return: Returns a dictionary of several tactical voting strategies the agent can apply
        """
        pass


class Borda(VotingScheme):
    """
    Borda voting class

    Borda voting tallies votes in a way where, an agent's preference receive a score of m - i, where "m"
    is the number of candidates, and "i" is the position of the preference in their preference list

    For example, "A" would receive a score of 3-1 = 2, if the preferences of the agent were ACB, and the candidates
    were ABC
    """

    def tactical_options(self, agent, tva_object):
        results = tva_object.results
        result_list = sorted(results, key=lambda k: results[k], reverse=True)
        index = result_list.index(list(agent.preferences.keys())[0])

        original_agents = []
        # remake agent set without our agent
        old_happiness = agent.get_happiness(tva_object.results)
        old_winner = get_winner(tva_object.results)

        for other_agent in tva_object.agents:
            if other_agent.name != agent.name:
                original_agents.append(other_agent)
        new_results = self.run_scheme(tva_object.candidates, original_agents)

        borda_strat = strategies_borda.Strategies_borda("Borda", 20)
        [res_pref, res_si] = borda_strat.check_if_best(agent, new_results, index, old_winner)
        tactical_set = {"H_p": {}, "H_si": {}}

        if len(res_pref) > 0:
            res_pref_winner = next(iter(res_pref[0]))
            i = 0
            for x in res_pref:
                alt_agent = Agent(agent.name, ''.join(x), tva_object.scheme)
                original_agents.append(alt_agent)
                new_results = self.run_scheme(tva_object.candidates, original_agents)
                new_happiness = agent.get_happiness(new_results)

                new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                       new_happiness, new_results)
                tactical_set["H_p"][i] = [list(x.keys()), res_pref_winner,
                                          new_results, new_happiness,
                                          new_overall_happiness]
                i += 1
                original_agents.pop()

        if len(res_si) > 0:
            j = 0
            for y in res_si:
                alt_agent = Agent(agent.name, ''.join(y), tva_object.scheme)
                original_agents.append(alt_agent)
                new_results = self.run_scheme(tva_object.candidates, original_agents)
                new_happiness = agent.get_happiness(new_results)
                new_winner = get_winner(new_results)

                new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                       new_happiness, new_results)
                tactical_set["H_si"][j] = [list(y.keys()), new_winner,
                                           new_results, new_happiness,
                                           new_overall_happiness]
                j += 1
                original_agents.pop()
        return tactical_set

    def tally_personal_votes(self, preferences):
        m = len(preferences)
        i = 1
        for key in preferences:
            preferences[key] = m - i
            i += 1


class Plurality(VotingScheme):
    """
    Plurality voting class

    The agents highest preference gets a score of 1
    """

    def tally_personal_votes(self, preferences):

        first_preference = next(iter(preferences))
        preferences[first_preference] += 1

    def tactical_options(self, agent, tva_object):

        tactical_set = {"H_p": {}, "H_si": {}}

        """
        For percentage_my_preference
        """

        total_agents = len(tva_object.get_agents())

        winner = get_winner(tva_object.results)

        # If more than half agents voted for the winning candidate, there is no tactical voting strategy for the
        # current agent
        if not tva_object.results[winner] > (total_agents / 2):

            original_list = list(agent.preferences)
            stop_index = original_list.index(winner)

            for i in range(1, stop_index):

                new_pref_list = copy(original_list)
                temp = new_pref_list[i]
                new_pref_list[i] = new_pref_list[0]
                new_pref_list[0] = temp

                results_copy = copy(tva_object.results)
                # Our original vote is taken away from the results
                results_copy[original_list[0]] -= 1

                # We add one vote to the candidate that we switch
                results_copy[original_list[i]] += 1

                new_winner = get_winner(results_copy)

                if new_winner != winner:
                    agent_happiness = agent.get_happiness(results_copy)
                    new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                           agent_happiness, results_copy)

                    tactical_set["H_p"][i] = [new_pref_list, new_winner,
                                              results_copy, agent_happiness,
                                              new_overall_happiness]

        """
        For percentage_social_index
        """

        # Not possible

        return tactical_set


class AntiPlurality(VotingScheme):
    """
    Anti-plurality voting class

    The agent's lowest preference gets a score of 0, while others get 1
    """

    def tally_personal_votes(self, preferences):

        i = 0
        for key in preferences:

            if i < len(preferences) - 1:
                preferences[key] += 1

            i += 1

    def tactical_options(self, agent, tva_object):

        tactical_set = {"H_p": {}, "H_si": {}}

        """
        For percentage_my_preference
        """

        winner = get_winner(tva_object.results)
        original_list = list(agent.preferences)
        winner_index = original_list.index(winner)

        # if the winner is not already in the last position I can investigate if I have a
        # tactical voting option
        if original_list[-1] != winner:

            new_pref_list = copy(original_list)
            temp = new_pref_list[-1]
            new_pref_list[-1] = winner
            new_pref_list[winner_index] = temp

            results_copy = copy(tva_object.results)
            results_copy[original_list[-1]] += 1
            results_copy[original_list[winner_index]] -= 1

            new_winner = get_winner(results_copy)

            agent_happiness = agent.get_happiness(results_copy)

            if agent_happiness["H_p"] > agent.get_happiness(tva_object.results)["H_p"]:
                new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                       agent_happiness, results_copy)

                tactical_set["H_p"][0] = [new_pref_list, new_winner,
                                          results_copy, agent_happiness,
                                          new_overall_happiness]

        """
        For percentage_social_index
        """
        pref_dict = copy(agent.get_preferences())
        pref_list = list(pref_dict.keys())

        least_preferred = pref_list[-1]

        results_copy = copy(tva_object.results)
        results_copy[least_preferred] += 1

        original_happiness = agent.get_happiness(tva_object.results)

        if results_copy[least_preferred] > results_copy[pref_list[0]]:

            tactical_set["H_si"] = {}

        elif results_copy[least_preferred] == results_copy[pref_list[0]] and least_preferred < pref_list[0]:

            tactical_set["H_si"] = {}

        else:

            results_copy = copy(tva_object.results)
            results_list = sorted(results_copy, key=lambda k: results_copy[k], reverse=True)

            stop_index = results_list.index(pref_list[0])

            for i in range(0, stop_index):

                list_copy = copy(pref_list)

                temp_i = results_list[i]
                temp_last = pref_list[-1]

                list_copy[pref_list.index(temp_i)] = temp_last
                list_copy[-1] = temp_i
                agent_copy = copy(agent)

                new_prefs = {}
                for candidate in list_copy:
                    new_prefs[candidate] = 0

                self.tally_personal_votes(new_prefs)
                agent_copy.preferences = new_prefs

                new_agents = [agent_copy]

                for a in tva_object.get_agents():
                    if not a == agent:
                        new_agents.append(a)

                new_results = self.run_scheme(tva_object.candidates, new_agents)
                new_winner = get_winner(new_results)

                new_happiness = agent.get_happiness(new_results)

                if new_happiness["H_si"] <= original_happiness["H_si"]:
                    continue

                new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                       new_happiness, new_results)

                tactical_set["H_si"][i] = [list_copy, new_winner, new_results,
                                           new_happiness, new_overall_happiness]

        return tactical_set


class VotingForTwo(VotingScheme):
    """
    Voting for two

    First and second choice get a score of 1
    """

    def tally_personal_votes(self, preferences):

        iterable = iter(preferences)

        preference = next(iterable)
        preferences[preference] += 1
        preference = next(iterable)
        preferences[preference] += 1

    def tactical_options(self, agent, tva_object):

        tactical_set = {"H_p": {}, "H_si": {}}

        """
        For percentage_my_preference
        """

        winner = get_winner(tva_object.results)
        original_list = list(agent.preferences)
        winner_index = original_list.index(winner)

        # if the winner is not in the third position of my preference order I can investigate
        # if I have tactical voting options
        if winner_index != 2:

            if winner_index == 1:

                for i in range(2, len(original_list)):

                    new_pref_list = copy(original_list)
                    temp = new_pref_list[i]
                    new_pref_list[i] = winner
                    new_pref_list[1] = temp

                    results_copy = copy(tva_object.results)
                    results_copy[original_list[1]] -= 1
                    results_copy[original_list[i]] += 1

                    new_winner = get_winner(results_copy)

                    if new_winner == original_list[0]:
                        agent_happiness = agent.get_happiness(results_copy)
                        new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                               agent_happiness, results_copy)

                        tactical_set["H_p"][i - 2] = [new_pref_list, new_winner,
                                                      results_copy, agent_happiness,
                                                      new_overall_happiness]

            else:

                for i in range(2, winner_index):

                    new_pref_list = copy(original_list)
                    temp = new_pref_list[i]
                    new_pref_list[i] = new_pref_list[1]
                    new_pref_list[1] = temp

                    results_copy = copy(tva_object.results)
                    results_copy[original_list[i]] += 1
                    results_copy[original_list[1]] -= 1

                    new_winner = get_winner(results_copy)

                    if original_list.index(new_winner) < winner_index:
                        agent_happiness = agent.get_happiness(results_copy)
                        new_overall_happiness = get_tactical_overall_happiness(tva_object, agent,
                                                                               agent_happiness, results_copy)

                        tactical_set["H_p"][i - 2] = [new_pref_list, new_winner,
                                                      results_copy, agent_happiness,
                                                      new_overall_happiness]

        """
        For percentage_social_index
        """
        pref_dict = copy(agent.get_preferences())
        pref_list = list(pref_dict.keys())

        first_pref = pref_list[0]
        second_pref = pref_list[1]

        original_happiness = agent.get_happiness(tva_object.results)

        results_dict = copy(tva_object.results)

        if not results_dict[second_pref] - results_dict[first_pref] >= 2 or \
                (results_dict[second_pref] - results_dict[first_pref] == 1 and second_pref < first_pref):

            for i in range(2, len(pref_list)):

                results_dict_copy = copy(results_dict)

                results_dict_copy[pref_list[i]] += 1

                if results_dict_copy[pref_list[i]] > results_dict_copy[first_pref] and pref_list[i] < first_pref:
                    results_dict_copy[pref_list[i]] -= 1
                    continue

                else:

                    results_dict_copy[pref_list[i]] -= 1

                    pref_list_copy = copy(pref_list)

                    temp = pref_list_copy[i]
                    pref_list_copy[i] = second_pref
                    pref_list_copy[1] = temp

                    new_pref_dict = {}
                    for element in pref_list_copy:
                        new_pref_dict[element] = 0

                    self.tally_personal_votes(new_pref_dict)
                    agent_copy = copy(agent)
                    agent_copy.preferences = new_pref_dict

                    new_agents = [agent_copy]

                    for a in tva_object.get_agents():
                        if not a == agent:
                            new_agents.append(a)

                    new_results = self.run_scheme(tva_object.candidates, new_agents)
                    new_winner = get_winner(new_results)

                    new_happiness = agent.get_happiness(new_results)

                    if new_happiness["H_si"] <= original_happiness["H_si"]:
                        continue

                    new_overall_happiness = get_tactical_overall_happiness(tva_object, agent, new_happiness,
                                                                           new_results)

                    tactical_set["H_si"][i - 2] = [pref_list_copy, new_winner, new_results,
                                                   new_happiness, new_overall_happiness]

        return tactical_set
