% Facts for witness: penguin is an animal
animal(penguin1).
penguin(penguin1).

% Rule from first premise: some animals are birds (A is P)
bird(X) :- animal(X), \+ penguin(X).

% Validity check: Some penguin is NOT a bird
valid_syllogism :- penguin(X), \+ bird(X).