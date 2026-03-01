% Witness for dog and animal
dog(buddy).
animal(buddy).

% fish has no facts in this counterexample - we don't want to assert any fish
% animal has facts, so we don't need a fail clause

% Rule from premise: Every dog is an animal
animal(X) :- dog(X).

% Rule from premise: No fish is an animal
conflict :- fish(X), animal(X).

% Validity check: Every fish is a dog
valid_syllogism :- \+ (fish(X), \+ dog(X)).