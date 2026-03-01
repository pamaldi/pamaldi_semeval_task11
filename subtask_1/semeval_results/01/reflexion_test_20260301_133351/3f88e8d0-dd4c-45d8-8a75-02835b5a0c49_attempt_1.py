% Facts (witness - bird that is both an insect and animal)
bird(spiderling).

% Rules from premises
animal(X) :- bird(X).
insect(X) :- bird(X).

% Validity check: All insects are animals (universal statement)
valid_syllogism :- \+ (insect(X), \+ animal(X)).