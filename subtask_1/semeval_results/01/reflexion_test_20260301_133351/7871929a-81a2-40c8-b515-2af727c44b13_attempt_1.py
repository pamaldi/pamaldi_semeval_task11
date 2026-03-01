% Facts: a fish that lives in water
fish(trout1).
lives_in_water(trout1).

% animal has facts, so no fail clause needed
animal(X) :- fish(X).

% Validity check: All animals live in water?
valid_syllogism :- \+ (animal(X), \+ lives_in_water(X)).