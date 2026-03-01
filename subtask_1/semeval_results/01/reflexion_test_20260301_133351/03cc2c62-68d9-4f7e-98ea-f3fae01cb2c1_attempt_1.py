% Witnesses for birds that are swimmers
bird(sparrow).
swimmer(sparrow).

bird(duck).
swimmer(duck).

% Rule from first premise: Every fish is a swimmer
swimmer(X) :- fish(X).

% Validity check - does any bird satisfy fish(X)?
valid_syllogism :- bird(X), fish(X).