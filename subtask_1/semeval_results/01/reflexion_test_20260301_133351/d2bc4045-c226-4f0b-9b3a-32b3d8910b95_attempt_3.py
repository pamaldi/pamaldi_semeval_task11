% Facts for predicates that have instances
dog(buddy).

% Fail clause only for fish/1 (no facts defined)
fish(_) :- fail.

% Rules from premises
animal(X) :- dog(X).

% Rule from premise: No fish is an animal
conflict :- fish(X), animal(X).

% Validity check: Every fish is a dog
valid_syllogism :- \+ (fish(X), \+ dog(X)).