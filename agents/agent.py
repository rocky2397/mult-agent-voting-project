def get_winner(results):
    """
    Returns the winning candidate. In the case of a tie, the winner will be chosen alphabetically (i.e., the agent
    whose name begins with the lowest letter in the alphabet)

    :param: results: A dictionary of results
    :return: A string with one character indicating the winner
    """

    winner = ""
    max_votes = 0

    for candidate in results:
        if results[candidate] > max_votes:
            winner = candidate
            max_votes = results[candidate]

        elif results[candidate] < max_votes:
            continue

        else:
            # Lexicographically determine winner if votes are equal
            if candidate < winner:
                winner = candidate
                max_votes = results[candidate]

    return winner


class Agent:
    """
    Class for an agent
    """

    def __init__(self, name, preference_string, voting_scheme):
        """
        Constructor for an agent

        :param name: A string for the name of the agent
        :param preference_string: A string indicating the preferences in order
        :param voting_scheme: A voting scheme object (Borda, Plurality, etc.)
        """

        self.name = name

        self.preferences = {}

        for preference in preference_string:
            self.preferences[preference] = 0

        # Tally votes depending on voting scheme
        voting_scheme().tally_personal_votes(self.preferences)

    def __str__(self):
        """
        String representation of an agent will be their name

        :return: Returns a string indicating the name of the agent
        """
        return self.name

    def get_preferences(self):
        """
        Gets the tallied preferences of the agent

        :return: A dictionary with the tallied preferences of the agent
        """
        return self.preferences

    def get_happiness(self, result_dict):
        """
        Computes happiness of an agent

        :param: result_dict: A dictionary of results
        :return: Returns a dictionary of happiness values, representing the agent's happiness in different ways
        """
        happiness_dict = {}

        """
        What is the index of the winner in my preference list
        """
        pref_list = list(self.preferences.keys())
        index = pref_list.index(get_winner(result_dict))

        happiness_dict["H_p"] = ((len(pref_list) - index - 1)/(len(pref_list) - 1)) * 100

        """
        What is the index of my first preference in the results
        """
        result_list = sorted(result_dict, key=lambda k: result_dict[k], reverse=True)

        index = result_list.index(pref_list[0])

        happiness_dict["H_si"] = ((len(result_list) - index - 1)/(len(result_list) - 1)) * 100

        return happiness_dict


