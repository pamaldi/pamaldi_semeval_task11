% Fail clause for celestial_body since it has no facts
celestial_body(_) :- fail.

% Fail clause for giant_ball_of_gas since it has no facts
giant_ball_of_gas(_) :- fail.

% Rule from A-premise: All stars are giant balls of gas
giant_ball_of_gas(X) :- star(X).

% Validity check for conclusion: Some stars are not celestial bodies
valid_syllogism :- star(X), \+ celestial_body(X).