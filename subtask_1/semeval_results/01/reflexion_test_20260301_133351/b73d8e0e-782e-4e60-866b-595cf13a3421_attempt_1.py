% Witness for rocks that are plants
rock(plant1).
plant(plant1).

% animal has NO facts in this model
animal(_) :- fail.

% Rule from first premise: No animal is a rock
conflict :- animal(X), rock(X).

% Rule from second premise: Some rocks are plants (using the witness)
% Already encoded via facts

% Validity check: Some animals are plants
valid_syllogism :- animal(X), plant(X).