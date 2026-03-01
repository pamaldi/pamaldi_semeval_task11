% COUNTEREXAMPLE: insect is NOT an animal
bird(spiderling).

% Rules from premises
animal(X) :- bird(X).
insect(X) :- bird(X).

% Add an insect that is NOT an animal to invalidate the conclusion
insect(ant1).

% Validity check: All insects are animals (universal statement)
valid_syllogism :- \+ (insect(X), \+ animal(X)).