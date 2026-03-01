% Facts for counterexample
creature_with_scales(s1).
fish(s1).

% mythical_creature has no facts (since no creatures with scales are mythical)
mythical_creature(_) :- fail.

% Premise 1: No creatures with scales are mythical creatures
conflict :- creature_with_scales(X), mythical_creature(X).

% Premise 2: Some creatures with scales are fish
% (We already have s1 as a creature_with_scales that is a fish via the fact)

% Conclusion: Some fish are mythical creatures
valid_syllogism :- fish(X), mythical_creature(X).