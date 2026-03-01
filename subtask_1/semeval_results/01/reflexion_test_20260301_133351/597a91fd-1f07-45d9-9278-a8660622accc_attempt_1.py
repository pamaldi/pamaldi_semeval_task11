% Facts (counterexample entities)
ocean(ant1).
insect(ant1).
animal(ant1).

% Rules from premises
animal(X) :- insect(X).

% Validity check: Some animals are oceans
valid_syllogism :- animal(X), ocean(X).