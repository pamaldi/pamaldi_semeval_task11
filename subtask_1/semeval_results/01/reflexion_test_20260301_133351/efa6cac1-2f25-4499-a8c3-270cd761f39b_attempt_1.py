% Facts: There are no birds in this model (since we need to build a counterexample)

% Fail clause for bird/1 (no birds exist)
bird(_) :- fail.

% Fail clause for penguin/1 (no penguins exist)
penguin(_) :- fail.

% Rule from premise: Every bird has a beak
beak(X) :- bird(X).

% Validity check: Some penguins have beaks
valid_syllogism :- penguin(X), beak(X).