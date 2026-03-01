% Facts for counterexample
creature_with_scales(s1).
fish(s1).

% mythical_creature has at least one witness
mythical_creature(s1).

% Fail clause for empty predicates (none needed in this case)

% Premise 1: No creatures with scales are mythical creatures
conflict :- creature_with_scales(X), mythical_creature(X).

% Premise 2: Some creatures with scales are fish
fish(X) :- creature_with_scales(X).

% Conclusion: Some fish are mythical creatures
valid_syllogism :- fish(X), mythical_creature(X).