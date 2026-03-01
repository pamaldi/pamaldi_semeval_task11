% Facts for the syllogism
dog(rover).
mammal(rover).
fish(goldie).
mammal(goldie).

% Rule for "Some member of the group of fish is not in the group of mammals"
% This is encoded by having a fish that is NOT a mammal (goldie is a mammal, so we need another fish that is not a mammal)
fish(tuna).

% Validity check: "At least one dog is a mammal" is satisfied by rover.
% Validity check: "At least one dog is not a fish" is satisfied by rover.
% Conclusion: "Some member of the group of fish is not in the group of mammals"
% We check if there exists a fish that is not a mammal (tuna is a fish and not a mammal)
valid_syllogism :- fish(X), \+ mammal(X).