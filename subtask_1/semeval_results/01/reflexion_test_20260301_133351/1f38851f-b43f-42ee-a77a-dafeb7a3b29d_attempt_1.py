% Witness: a basketball player who is also a human
basketball_player(kareem).
human(kareem).

% Rule from A-premise
over_10_feet_tall(X) :- human(X).

% Check for conclusion: Some basketball players are over 10 feet tall
valid_syllogism :- basketball_player(X), over_10_feet_tall(X).