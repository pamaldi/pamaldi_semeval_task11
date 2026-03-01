% Fail clause for metal_object since there are no facts
metal_object(_) :- fail.

% Rule from E-premise: No plant is a metal object
conflict :- plant(X), metal_object(X).

% Rule from A-premise: All flower is a plant
plant(X) :- flower(X).

% Witness for I-conclusion: Some flower is a metal object
flower(w1).

% Validity check: Does the I-conclusion hold?
valid_syllogism :- flower(X), metal_object(X).