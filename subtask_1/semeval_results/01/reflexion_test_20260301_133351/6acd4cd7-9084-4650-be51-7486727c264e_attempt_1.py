% Witness: a rose that is NOT a stone
rose(rose1).

% flower has NO facts in this model
flower(_) :- fail.

% stone has NO facts in this model
stone(_) :- fail.

% Rule from A-premise: All flowers are stones
stone(X) :- flower(X).

% E-premise constraint: No stone is a rose
conflict :- stone(X), rose(X).

% O-conclusion: Some roses are not flowers
valid_syllogism :- rose(X), \+ flower(X).