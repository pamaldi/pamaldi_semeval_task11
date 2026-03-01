% Witness: a cat that is not a dog
cat(felix).

% Fail clause for dogs (no dog exists in this model)
dog(_) :- fail.

% Rule from "every cat is an animal"
animal(X) :- cat(X).

% Introduce animals not from cats to make conclusion false
animal(zebra1).
animal(zebra2).

% Validity check: Some animal is a cat
valid_syllogism :- animal(X), cat(X).