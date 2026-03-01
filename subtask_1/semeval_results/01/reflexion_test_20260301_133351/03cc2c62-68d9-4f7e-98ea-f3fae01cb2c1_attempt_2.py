% Facts for birds that are swimmers
bird(sparrow).
bird(duck).
swimmer(sparrow).
swimmer(duck).

% Rule from first premise: Every fish is a swimmer
swimmer(X) :- fish(X).

% fish/1 has no facts, so we need a fail clause
fish(_) :- fail.

% Validity check - does any bird satisfy fish(X)?
valid_syllogism :- bird(X), fish(X).