% Facts for the syllogism

% Premise 2: "At least one dog is a mammal" (I-type)
dog(rover).
mammal(rover).

% Premise 3: "At least one dog is not a fish" (O-type)
dog(rover).

% Premise 1: "Some member of the group of fish is not in the group of mammals" (O-type)
% Counterexample: Make ALL fish mammals (so the conclusion is FALSE despite premises being TRUE)
fish(goldie).
mammal(goldie).

% fish is a subset of mammals in this model (so "some fish are not mammals" is FALSE)
mammal(X) :- fish(X).

% Validity check: "Some member of the group of fish is not in the group of mammals"
% This should FAIL, proving the syllogism is INVALID
valid_syllogism :- fish(X), \+ mammal(X).