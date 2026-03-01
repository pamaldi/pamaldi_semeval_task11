% Facts (witness: a non-round object that is an official game ball)
official_game_ball(non_round_ball).
not_round(non_round_ball).

% Rules from premises
official_game_ball(X) :- basketball(X).

% Validity check: Some basketballs are not round
valid_syllogism :- basketball(X), not_round(X).