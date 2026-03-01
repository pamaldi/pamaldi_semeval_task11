% Facts: giant_ball_of_gas has one instance (sun)
giant_ball_of_gas(sun).

% Rule from A-premise: All stars are giant balls of gas
giant_ball_of_gas(X) :- star(X).

% Fail clause for celestial_body since it has no facts
celestial_body(_) :- fail.

% Validity check for conclusion: Some stars are not celestial bodies
valid_syllogism :- star(X), \+ celestial_body(X).