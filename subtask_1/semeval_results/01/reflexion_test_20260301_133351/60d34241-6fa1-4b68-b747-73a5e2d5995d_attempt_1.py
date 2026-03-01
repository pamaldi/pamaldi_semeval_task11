% Witness: a machine that is also an animal
machine(m1).
animal(m1).

% computer is empty in this model
computer(_) :- fail.

% Rule from first premise (All machines are animals)
animal(X) :- machine(X).

% Rule from second premise (No animals are computers)
conflict :- animal(X), computer(X).

% Validity check: Some computers are not machines
valid_syllogism :- computer(X), \+ machine(X).