% Counterexample: a fish that is an animal, but some animals NOT in water
fish(tuna).
lives_in_water(tuna).

animal(tuna).              % tuna is a fish and an animal
animal(dog).               % dog is an animal that does NOT live in water

% A-premise 1: All fish live in water
lives_in_water(X) :- fish(X).

% A-premise 2: All fish are animals
animal(X) :- fish(X).

% Validity check: All animals live in water? (Conclusion to test)
valid_syllogism :- \+ (animal(X), \+ lives_in_water(X)).