% Counterexample: Animal that is a mammal (not through being a human)
animal(lion1).
mammal(lion1).

% Rule from A-premise: All humans are mammals
mammal(X) :- human(X).

% E-premise constraint: No animal is human
conflict :- animal(X), human(X).

% Validity check: No animal is a mammal → Check if this holds
valid_syllogism :- \+ (animal(X), mammal(X)).