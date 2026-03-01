% COUNTEREXAMPLE: humans are NOT chairs

% Witness: a human that is NOT a chair
human(alice).

% No facts for chair/1 and animal/1 since they have no entities
chair(_) :- fail.
animal(_) :- fail.

% Rule from "every animal is a type of human"
human(X) :- animal(X).

% Validity check for conclusion "All humans are chairs"
% This is an A-conclusion (universal affirmative), so check: \+ (human(X), \+ chair(X))
valid_syllogism :- \+ (human(X), \+ chair(X)).