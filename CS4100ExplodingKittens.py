from email import policy
import random
import copy
from collections import Counter
from shutil import move


# An agent in an Exploding Kittens Game
# This is the defaul class of an agent; it makes all of its decisions randomly
class Player:
    def __init__(self, ID):
        # player name
        self.player_ID = ID
        # is the player still in the game?
        self.alive = True
        # is the player skipping their current turn?
        self.skipping = False
        # cards in the player's hand
        self.hand = []
        # other players in the game
        self.other_players = []
        # (we will probably have other variables to store gamestate knowledge)
        self.deck_size = None
        self.future_seen = []
        self.game_states = []
        self.actions = []

    def __str__(self):
        return self.player_ID

    def __repr__(self):
        return str(self.player_ID)

    # decide which player to target with a favor card
    def choose_favor_target(self):
        possible_choices = list(filter(lambda p: len(p.hand) > 0 and p.alive, self.other_players))
        return random.choice(possible_choices)

    # decide which player to target with a cat card pairing
    def choose_cat_target(self):
        possible_choices = list(filter(lambda p: len(p.hand) > 0 and p.alive, self.other_players))
        return random.choice(possible_choices)

    # decide which card to give to a player asking for a favor
    def give_card(self, other_player):
        return random.choice(self.hand)

    # decide where in the deck to replant an exploding kitten
    def choose_spot_in_deck(self, deck_size):
        return random.randrange(deck_size)

    def get_game_state(self, game):
        player_hand = Counter([card.card_type for card in self.hand])
        opponent = self.other_players[0]
        opp_hand = Counter([card.card_type for card in opponent.hand])
        possible_actions = []
        for card_type in player_hand:
            if card_type != 'Defuse':
                # need two or more like cat cards to play
                if card_type in ['Cattermelon', 'Tacocat', 'Rainbow-Ralphing Cat']:
                    if player_hand[card_type] > 1:
                        possible_actions.append('Cat')
                # otherwise only one card is needed
                else:
                    possible_actions.append(card_type)
        hand = list(set(sorted(possible_actions)))
        deck_size = len(game.deck)
        future = self.future_seen[0] if self.future_seen else None
        players_left = game.players_left
        attack_counter = game.attack_counter
        game_key = {
            'hand': hand,
            'opponent_hand_sizes': list(sorted([len(opp.hand) for opp in self.other_players])),
            'deck_size': deck_size,
            'future': future,
            'attack_counter': attack_counter,
            'defuses_owned': player_hand['Defuse'],
            'defuses_with_opp': opp_hand['Defuse']
        }
        return str(game_key)

    # player makes a turn
    def player_card_play(self, game):
        # 50/50 of playing a card or not
        opponent_hand_sizes = [len(opp.hand) for opp in self.other_players]
        playing = random.randrange(0, 2)
        while playing == 1 and not self.skipping:
            game_state = self.get_game_state(game)
            # get all possible actions for a player
            player_hand = Counter([card.card_type for card in self.hand])
            possible_actions = []
            for card_type in player_hand:
                if card_type != 'Defuse':
                    # need two or more like cat cards to play
                    if card_type in ['Cattermelon', 'Tacocat', 'Rainbow-Ralphing Cat']:
                        if 0 not in opponent_hand_sizes:
                            if player_hand[card_type] > 1:
                                possible_actions.append(card_type)
                    # otherwise only one card is needed
                    elif card_type == 'Favor':
                        if 0 not in opponent_hand_sizes:
                            possible_actions.append(card_type)
                    else:
                        possible_actions.append(card_type)
            # if a move can be made, decide which move to make
            if possible_actions:
                # randomly select an action and play the appropriate card(s)
                action = possible_actions[random.randrange(len(possible_actions))]
                game.last_played = Card(action)
                game.play_card(self, action)
                if action in ['Rainbow-Ralphing Cat', 'Tacocat', 'Cattermelon']:
                    self.actions.append('Cat')
                else:
                    self.actions.append(action)
                self.game_states.append(game_state)
            # randomly decide to play another card or not
            playing = random.randrange(0, 2)
        game_state = self.get_game_state(game)
        self.actions.append('Finish Turn')
        self.game_states.append(game_state)


# This agent will obey 2 laws,
#   -  If they have to give a card, will not choose randomly rather give according to
#   -  the list specified in the give_card method
#   -  When they draw an exploding kitten, will put it back at the top of the deck
#   -  so that the other player is highly likely to draw it
# This agent is built to play against a random agent, not one that acts intelligently.
# If the opponent acted intelligently, then they could play an attack or skip card after
# this agent replants an exploding kitten
class NonRandomPlayer(Player):
    def __repr__(self):
        return 'Non-Random Player'

    # Try to give the other player the least valuable card we have
    def give_card(self, other_player):
        # The order that we give our cards out
        order = ['Tacocat', 'Cattermelon', 'Rainbow-Ralphing Cat', 'Favor', 'Shuffle', 'See The Future',
                 'Skip', 'Attack', 'Defuse']
        for name in order:
            for card in self.hand:
                if card.__repr__() == name:
                    return card

    # Always choose the top spot in the deck, so the other player will get it
    def choose_spot_in_deck(self, deck_size):
        return 0


# This agent will attempt to counter the NonRandomPLayer agent, namely playing an attack/skip/shuffle card if the other
# draws an exploding kitten
class SmartPlayer(NonRandomPlayer):
    def __repr__(self):
        return 'Smart PLayer'

    def player_card_play(self, game):
        player_hand = Counter([card.card_type for card in self.hand])
        if game.last_played is not None and game.last_played.card_type == 'Defuse':
            if 'Attack' in player_hand:
                game.last_played = Card('Attack')
                game.play_card(self, 'Attack')
                return
            elif 'Skip' in player_hand:
                game.last_played = Card('Skip')
                game.play_card(self, 'Skip')
                return
            elif 'Shuffle' in player_hand:
                game.last_played = Card('Shuffle')
                game.play_card(self, 'Shuffle')
                return
        else:
            super().player_card_play(game)


class ObservedPolicyPlayer(SmartPlayer):
    def __init__(self, ID):
        super().__init__(ID)
        self.policy = {}

    def __repr__(self):
        return 'Observed-Policy PLayer'

    def train(self, player_type):
        policy = {}
        for i in range(2500000):
            players = [
                player_type('Player1'),
                player_type('Player2')
            ]
            game = Game(players)
            game.start_game()
            winner = game.decide_winner()
            for player in players:
                states_seen = player.game_states
                actions = player.actions
                did_win = player.player_ID == winner
                moves = len(states_seen)
                move_on = 0
                while move_on < moves:
                    state = states_seen[move_on]
                    action = actions[move_on]
                    if state not in policy.keys():
                        policy[state] = {}
                    if action not in policy[state].keys():
                        policy[state][action] = {
                            'win': 0,
                            'loss': 0
                        }
                    if did_win:
                        policy[state][action]['win'] += 1
                    else:
                        policy[state][action]['loss'] += 1
                    move_on += 1
        self.policy = policy

    # player makes a turn
    def policy_best_independent_move(self, game):
        game_state = self.get_game_state(game)
        if game_state in self.policy.keys():
            precedent = self.policy[game_state]
            probabilities = {}
            for action in precedent.keys():
                if action not in ['Cat', 'Favor']:
                    wins = precedent[action]['win']
                    losses = precedent[action]['loss']
                    probabilities[action] = wins / (wins + losses)
            return max(probabilities, key=probabilities.get) if probabilities else self.random_move(game)
        else:
            return self.random_move(game)

    def random_move(self, game):
        # 50/50 of playing a card or not
        opponent_hand_sizes = [len(opp.hand) for opp in self.other_players]
        playing = random.randrange(0, 2)
        if playing == 0:
            return 'Finish Turn'
        game_state = self.get_game_state(game)
        # get all possible actions for a player
        player_hand = Counter([card.card_type for card in self.hand])
        if game.last_played is not None and game.last_played.card_type == 'Defuse':
            if 'Attack' in player_hand:
                return ('Attack')
            elif 'Skip' in player_hand:
                return ('Skip')
            elif 'Shuffle' in player_hand:
                return ('Shuffle')
        possible_actions = []
        for card_type in player_hand:
            if card_type != 'Defuse':
                # need two or more like cat cards to play
                if card_type in ['Cattermelon', 'Tacocat', 'Rainbow-Ralphing Cat']:
                    if 0 not in opponent_hand_sizes:
                        if player_hand[card_type] > 1:
                            possible_actions.append(card_type)
                # otherwise only one card is needed
                elif card_type == 'Favor':
                    if 0 not in opponent_hand_sizes:
                        possible_actions.append(card_type)
                else:
                    possible_actions.append(card_type)
        # if a move can be made, decide which move to make
        if possible_actions:
            # randomly select an action and play the appropriate card(s)
            return possible_actions[random.randrange(len(possible_actions))]
        return 'Finish Turn'

    # player makes a turn
    def policy_best_move(self, game):
        game_state = self.get_game_state(game)
        if game_state in self.policy.keys():
            precedent = self.policy[game_state]
            probabilities = {}
            for action in precedent.keys():
                wins = precedent[action]['win']
                losses = precedent[action]['loss']
                probabilities[action] = wins / (wins + losses)
            return max(probabilities, key=probabilities.get) if probabilities else self.random_move(game)
        else:
            return self.random_move(game)

        # player makes a turn

    def player_card_play(self, game):
        action = self.policy_best_move(game)
        if action is None:
            super().player_card_play(game)
        else:
            opponent_hands = [len(opp.hand) for opp in self.other_players]
            if action in ['Cat', 'Favor'] and 0 in opponent_hands:
                action = self.policy_best_independent_move(game)
            while action != 'Finish Turn':
                if action is None:
                    super().player_card_play(game)
                else:
                    if action == 'Cat':
                        player_hand = Counter([card.card_type for card in self.hand])
                        for possible_cat in ['Rainbow-Ralphing Cat', 'Tacocat', 'Cattermelon']:
                            if possible_cat in player_hand and player_hand[possible_cat] > 1:
                                action = possible_cat
                    if action == 'Cat':
                        print(self.hand)
                        print("NOOOOOOOOOOOOOOOOOOO")
                    game.last_played = Card(action)
                    game.play_card(self, action)
                    action = self.policy_best_move(game)
                    opponent_hands = [len(opp.hand) for opp in self.other_players]
                    if action in ['Cat', 'Favor'] and 0 in opponent_hands:
                        action = self.policy_best_independent_move(game)

                    # a class for a card


# An agent that is going to watch a lot of games, and see which moves in different states
# led to that agent surviving many more turns
# Meaning the reward function is the amount of turns the agent survives
class SurvivalAgent(ObservedPolicyPlayer):
    def __init__(self, ID):
        super().__init__(ID)
        self.policy = {}

    def train(self, player_type):
        policy = {}
        iters = 50000
        for i in range(iters):
            if i % (iters / 10) == 0:
                print(str((i / iters) * 100) + "%")
            players = [
                player_type('Player1'),
                player_type('Player2')
            ]
            game = Game(players)
            game.start_game()
            for player in players:
                states_seen = player.game_states
                actions_taken = player.actions
                num_moves = len(states_seen)
                # Cycle through moves and assign reward, either a flat reward for
                # length of moves, or reward based on how many more moves are survived
                for pos, state in enumerate(states_seen):
                    curr_action = actions_taken[pos]
                    if state not in policy.keys():
                        # state -> {action, value}
                        policy[state] = {}
                    if curr_action not in policy[state].keys():
                        policy[state][curr_action] = 0
                    policy[state][curr_action] = (policy[state][curr_action] + num_moves) / 2
        self.policy = policy

    def policy_best_move(self, game):
        game_state = self.get_game_state(game)
        if game_state in self.policy.keys():
            actions = self.policy[game_state]
            best_action = max(actions, key=actions.get)
            return best_action
        else:
            return None

    def player_card_play(self, game):
        action = self.policy_best_move(game)
        while action != 'Finish Turn':
            if action == 'Cat':
                player_hand = Counter([card.card_type for card in self.hand])
                for possible_cat in ['Rainbow-Ralphing Cat', 'Tacocat', 'Cattermelon']:
                    if possible_cat in player_hand and player_hand[possible_cat] > 1:
                        action = possible_cat
            if action == 'Cat':
                print(self.hand)
                print("NOOOOOOOOOOOOOOOOOOO")

            # ========== I added this clause to just return if the action is None cause it was giving ============== #
            # ========== an error, lmk if there is something better to be done but this seems to work ============== #
            if action is None:
                Player.player_card_play(self, game)
                return
            game.last_played = Card(action)
            game.play_card(self, action)
            action = self.policy_best_move(game)


class Card:
    def __init__(self, card_type):
        # the type of card (Defuse, Attack, Favor, etc.)
        self.card_type = card_type

    def __str__(self):
        return self.card_type

    def __repr__(self):
        return str(self.card_type)


# a class for one game of Exploding Kittens
# most of this class can be ignored as it does not related to the AI implementation directly and merely defines the course of the game
class Game:
    def __init__(self, players):
        # the most recently-played card
        self.last_played = None
        # number of players
        self.num_players = len(players)
        # the hand size for players
        self.hand_size = 7
        # the number of exploding kittens in the deck
        self.exploding_kittens = self.num_players - 1
        # the number of Attack cards
        self.attacks = 4
        # the number of Skip cards
        self.skips = 4
        # the number of StF cards
        self.see_the_futures = 3
        # the number of Shuffle cards
        self.shuffles = 2
        # the number of Favor cards
        self.favors = 2
        # the number of Tacocat cards
        self.tacocats = 3
        # the number of Cattermelon cards
        self.cattermelons = 3
        # the number of RRC cards
        self.rainbow_ralphing_cats = 3
        # the deck/draw pile
        self.deck = []
        # the list of Players
        self.player_list = players
        # the player whose turn it is
        self.turn = -1
        # the number of players left in the game
        self.players_left = self.num_players
        # the number of queued attacks
        self.attack_counter = 0
        # a map of cards and their behavior
        self.card_functions = {
            'Attack': self.play_attack,
            'Skip': self.play_skip,
            'See The Future': self.play_see_the_future,
            'Shuffle': self.play_shuffle,
            'Favor': self.play_favor,
            'Tacocat': self.play_cat,
            'Cattermelon': self.play_cat,
            'Rainbow-Ralphing Cat': self.play_cat
        }

    def do_nothing(self, player):
        print("This card does nothing!")

    def play_attack(self, player):
        player.skipping = True
        self.attack_counter += 1

    def play_skip(self, player):
        player.skipping = True

    def play_see_the_future(self, player):
        max_deck_index = len(self.deck) - 1
        card_on = 0
        future = []
        while card_on <= max_deck_index and card_on < 3:
            future.append(self.deck[card_on])
            card_on += 1
        player.future_seen = future

    def play_shuffle(self, player):
        self.shuffle_deck()
        for p in self.player_list:
            p.future_seen = []

    def play_favor(self, player):
        other_players = list(filter(lambda p: p != player and len(p.hand) > 0 and p.alive, self.player_list))
        if len(other_players) == 0:
            player.hand.append(self.last_played)
        else:
            target_player = player.choose_favor_target()
            card_given = target_player.give_card(player)
            target_player.hand.remove(card_given)
            player.hand.append(card_given)
            # print(f"{target_player.player_ID} gives a(n) {card_given.card_type} to {player.player_ID}")

    def play_cat(self, player):
        other_players = list(filter(lambda p: p != player and len(p.hand) > 0 and p.alive, self.player_list))
        if len(other_players) != 0:
            target_player = player.choose_cat_target()
            card_given = random.choice(target_player.hand)  # choice is always random
            target_player.hand.remove(card_given)
            player.hand.append(card_given)
            # print(f"{target_player.player_ID} gives a(n) {card_given.card_type} to {player.player_ID}")

    def play_game(self):
        while self.players_left > 1 and self.deck:
            if self.attack_counter == 0:
                self.turn = self.turn + 1 if self.turn < len(self.player_list) - 1 else 0
            else:
                self.attack_counter -= 1
            player_on = self.player_list[self.turn]
            if player_on.alive:
                self.take_turn(player_on)

    def take_turn(self, player):
        player.player_card_play(self)
        if not player.skipping:
            self.draw_card(player)
        else:
            # print(f"{player.player_ID} skips drawing")
            player.skipping = False

    def play_card(self, player, action):
        if action in ['Cattermelon', 'Tacocat', 'Rainbow-Ralphing Cat']:
            for card in player.hand:
                if card.card_type == action:
                    # print(f"{player.player_ID} plays {action}")
                    player.hand.remove(card)
                    break
        for card in player.hand:
            if card.card_type == action:
                # print(f"{player.player_ID} plays {action}")
                player.hand.remove(card)
                break
        self.card_functions[action](player)

    def reinsert_exploding_kitten(self, player, card, deck_size):
        spot = player.choose_spot_in_deck(deck_size)
        self.deck.insert(spot, card)

    def draw_card(self, player):
        next_card = self.deck.pop(0)
        # print(f"{player.player_ID} draws a(n) {next_card.card_type}")
        if next_card.card_type == 'Exploding Kitten':
            if 'Defuse' in [card.card_type for card in player.hand]:
                # print(f"{player.player_ID} uses a Defuse!")
                for card in player.hand:
                    if card.card_type == 'Defuse':
                        player.hand.remove(card)
                        break
                self.reinsert_exploding_kitten(player, next_card, len(self.deck) + 1)
                for p in self.player_list:
                    p.future_seen = []
            else:
                # print(f"{player.player_ID} EXPLODES!")
                player.alive = False
                self.players_left -= 1
        else:
            player.hand.append(next_card)
            for p in self.player_list:
                if len(p.future_seen) > 0:
                    del p.future_seen[0]
        for p in self.player_list:
            p.deck_size = len(self.deck)

    def start_game(self):
        self.initialize_deck()
        for player in self.player_list:
            player.other_players = list(filter(lambda p: p != player, self.player_list))
            player.hand.append(Card('Defuse'))
        for i in range(self.hand_size - 1):
            for player in self.player_list:
                player.hand.append(self.deck.pop(0))
        for i in range(self.exploding_kittens):
            self.deck.append(Card('Exploding Kitten'))
        for player in self.player_list:
            player.deck_size = len(self.deck)
        self.shuffle_deck()
        self.play_game()

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def initialize_deck(self):
        for i in range(self.attacks):
            self.deck.append(Card('Attack'))
        for i in range(self.skips):
            self.deck.append(Card('Skip'))
        for i in range(self.see_the_futures):
            self.deck.append(Card('See The Future'))
        for i in range(self.shuffles):
            self.deck.append(Card('Shuffle'))
        for i in range(self.favors):
            self.deck.append(Card('Favor'))
        for i in range(self.tacocats):
            self.deck.append(Card('Tacocat'))
        for i in range(self.cattermelons):
            self.deck.append(Card('Cattermelon'))
        for i in range(self.rainbow_ralphing_cats):
            self.deck.append(Card('Rainbow-Ralphing Cat'))
        self.shuffle_deck()

    def decide_winner(self):
        for player in self.player_list:
            if player.alive:
                return player.player_ID


if __name__ == "__main__":
    random_player = Player('Player1')
    random_player2 = Player('Player2')
    nonrandom_player = NonRandomPlayer('Player2')
    nonrandom_player_1 = NonRandomPlayer('Player1')
    smart_player = SmartPlayer('Player2')

    survival_player = SurvivalAgent('Player2')
    print('Training Survival Agent...')
    survival_player.train(Player)
    surv_policy = survival_player.policy

    observed_policy_player = ObservedPolicyPlayer('Player2')
    print("Training OPP...")
    observed_policy_player.train(SmartPlayer)
    opp_policy = observed_policy_player.policy

    print("Simulating Random v Random")
    players = [
        random_player,
        random_player2
    ]
    wins = {player.player_ID: 0 for player in players}
    for i in range(500):
        players = [Player('Player1'), Player('Player2')]
        game = Game(players)
        game.start_game()
        wins[game.decide_winner()] += 1
    print(f"RESULTS (P1 is random): {wins}")

    print("Simulating Random v NonRandom")
    players = [
        random_player,
        nonrandom_player
    ]
    wins = {player.player_ID: 0 for player in players}
    for i in range(500):
        players = [Player('Player1'), NonRandomPlayer('Player2')]
        game = Game(players)
        game.start_game()
        wins[game.decide_winner()] += 1
    print(f"RESULTS (P1 is random): {wins}")

    print("Simulating Random v Smart")
    players = [
        random_player,
        smart_player
    ]
    wins = {player.player_ID: 0 for player in players}
    for i in range(500):
        players = [Player('Player1'), SmartPlayer('Player2')]
        game = Game(players)
        game.start_game()
        wins[game.decide_winner()] += 1
    print(f"RESULTS (P1 is random): {wins}")

    print("Simulating Smart v NonRandom")
    players = [
        smart_player,
        nonrandom_player_1
    ]
    wins = {player.player_ID: 0 for player in players}
    for i in range(500):
        players = [SmartPlayer('Player1'), NonRandomPlayer('Player2')]
        game = Game(players)
        game.start_game()
        wins[game.decide_winner()] += 1
    print(f"RESULTS (P1 is Smart): {wins}")

    print("Simulating Random v Survival")
    players = [
        random_player,
        survival_player
    ]
    wins = {player.player_ID: 0 for player in players}
    for i in range(500):
        surv = SurvivalAgent('Player2')
        surv.policy = surv_policy
        players = [Player('Player1'), surv]
        game = Game(players)
        game.start_game()
        wins[game.decide_winner()] += 1
    print(f"RESULTS (P1 is random): {wins}")


    print("Simulating Random v OPP")
    players = [
        random_player,
        observed_policy_player
    ]
    wins = {player.player_ID: 0 for player in players}
    for i in range(500):
        opp = ObservedPolicyPlayer('Player2')
        opp.policy = opp_policy
        players = [Player('Player1'), opp]
        game = Game(players)
        game.start_game()
        wins[game.decide_winner()] += 1
    print(f"RESULTS (P1 is random): {wins}")

