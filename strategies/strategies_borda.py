class Strategies_borda:
    """
    Class for a Borda voting strategy
    """


    def __init__(self, voting_scheme, opt_limit):
        """
        Constructor for the Borda voting strategy

        :param voting_scheme: voting scheme used
        :param opt_limit: maximum number of tactical voting options
        """
        self.opt_limit = opt_limit
        valid = False
        if voting_scheme == "Borda":
            valid = True

        if not valid:
            print("Error: unsupported voting and happiness scheme combination.")

    def check_if_best(self, agent, remainder_votes, pref_pos, winner):
        """
        Checks if an agent can change voting strategy to find a better outcome

        :param agent: the agent changing their voting strategy
        :param remainder_votes: tallied votes of all other agents except ours
        :param pref_pos: position from all tallied votes of highest preferred candidate of agent
        :return [res_pref, res_si]: list containing the new preference dictionaries for both happiness metrics
        """

        new_votes = remainder_votes.copy()
        prefs = agent.get_preferences()
        res_si = self.highest_position(next(iter(prefs)), prefs, new_votes, pref_pos)
        for x in prefs:
            if x == winner:
                return [[], res_si]
            res_pref = self.check_winner_possible(x, prefs, new_votes)
            if len(res_pref) > 0:
                return [res_pref, res_si]
        return [[], []]

    def check_winner_possible(self, candidate, prefs, votes):
        """
        Checks if an agent can change voting strategy to make a specific candidate win,
        which is what gives the "my preference" happiness metric its score

        :param candidate: the candidate to get to 1st place
        :param prefs: preference dict of the agent changing their voting strategy
        :param votes: tallied votes without our agents votes
        :return new_prefs: list of new preferences for tactical voting
        """
        up_bound = votes[candidate]+(len(prefs)-1)
        lee = []
        for x in prefs:
            if x != candidate:
                # if our wanted winner wins the tie, x can get up to the same score
                if candidate < x:
                    diff = up_bound - votes[x]
                    if diff < 0:
                        return []
                    lee.append((x, diff))
                # if our wanted winner loses the tie, x can get up to 1 below the same score
                else:
                    diff = up_bound - votes[x] - 1
                    if diff < 0:
                        return []
                    lee.append((x, diff))

        # sort the list of leeway in descending order
        sorted_lee = sorted(lee, key=lambda k: k[1], reverse=True)

        # if any leeway is negative, the candidate cannot win
        if sorted_lee[-1][1] < 0:
            return []

        # check if tactical voting is possible
        i = 0
        for x in range(len(prefs)-2, -1, -1):
            if x > sorted_lee[i][1]:
                return []
            i += 1

        # populate tact voting options with recursion
        database = self.populate_recur([], sorted_lee, len(sorted_lee) - 1, [], True)
        new_prefs = []
        for x in database:
            i = len(prefs)-1
            new_prefs.append({candidate: i})
            for y in x:
                i -= 1
                new_prefs[-1].update({y[0]: i})

        return new_prefs

    def highest_position(self, candidate, prefs, votes, pref_pos):
        """
        Finds the highest position the candidate can be made to achieve with tactical voting,
        which is proportional to the score of the "social index" happiness metric

        :param candidate: the candidate to get to 1st place
        :param prefs: preference dict of the agent changing their voting strategy
        :param votes: tallied votes without our agents votes
        :param pref_pos: position of highest preference in voting
        :return new_prefs: list of new preferences for tactical voting
        """
        new_prefs = {}
        up_bound = votes[candidate]+(len(prefs)-1)
        new_prefs[candidate] = len(prefs)-1
        lee = []
        for x in prefs:
            if x != candidate:
                # if our wanted winner wins the tie, x can get up to the same score
                if candidate < x:
                    diff = up_bound - votes[x]
                    lee.append((x, diff))
                # if our wanted winner loses the tie, x can get up to 1 below the same score
                else:
                    diff = up_bound - votes[x] - 1
                    lee.append((x, diff))

        # sort the list of leeway in descending order
        sorted_lee = sorted(lee, key=lambda k: k[1], reverse=True)

        max_losers = 0
        for l in range(0, len(sorted_lee)):
            if sorted_lee[-1-l][1] >= max_losers:
                max_losers += 1
        if not (len(sorted_lee) - max_losers) < pref_pos:
            return []
        database = self.populate_recur([], sorted_lee, max_losers-1, [], False)
        new_prefs = []
        if len(database) == 1 and len(database[0]) == 1:
            database = [database]
        for x in database:
            i = len(prefs) - 1
            new_prefs.append({candidate: i})
            for y in x:
                i -= 1
                new_prefs[-1].update({y[0]: i})
        return new_prefs

    def populate_recur(self, current, sorted_leeway, threshold, database, tight):
        """
        depth-first tree expansion using recursion for populating the tactical options for both happiness metrics,
        the expansion will stop if it reaches the limit of tactical options allowed during creation of this object

        :param current: The new preference list to be populated, to be made empty when starting recursion
        :param sorted_leeway: a sorted list of candidate-leeway pairs in decreasing order of leeway
        :param threshold: number of minimum leeway required for expansion
        :param database: list of preferences collecting all leaf nodes of the recursive process
        :param tight: Boolean of whether or not all items in the sorted list are required to fit under their respective
        threshold, set to true for "my preference" and false for "social index" happiness metrics
        :return: filled database of new preferences for tactical voting options
        """
        if len(database) >= self.opt_limit:
            return database
        if threshold == -1:
            database.append(current)
            # put remainder on the start
            if not tight and len(sorted_leeway) > 0:
                for x in sorted_leeway:
                    database[-1].insert(0, x)
            return database
        i = 0
        while i < len(sorted_leeway):
            if sorted_leeway[i][1] >= threshold:
                new_current = current.copy()
                new_current.append(sorted_leeway[i])
                new_sorted_leeway = sorted_leeway.copy()
                new_sorted_leeway.pop(i)
                database = self.populate_recur(new_current, new_sorted_leeway, threshold - 1, database, tight)
            elif tight:
                break
            i += 1
        return database

