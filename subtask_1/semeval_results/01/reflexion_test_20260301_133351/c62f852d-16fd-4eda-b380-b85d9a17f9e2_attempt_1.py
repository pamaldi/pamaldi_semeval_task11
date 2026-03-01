% Facts for witnesses
creature(w).

% Fail clause for amphibian (no facts)
amphibian(_) :- fail.

% Rule from "Every creature is a mammal"
mammal(X) :- creature(X).

% Rule from "No mammal is an amphibian"
conflict :- mammal(X), amphibian(X).

% Validity check: "No amphibian is a creature" = \+ (amphibian(X), creature(X))
valid_syllogism :- \+ (amphibian(X), creature(X)).