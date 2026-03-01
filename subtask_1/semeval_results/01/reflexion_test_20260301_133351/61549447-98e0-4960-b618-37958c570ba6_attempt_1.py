% Witness: a bird that is also a mammal
bird(parrot).
mammal(parrot).

% Witness: a dog that is a bird
dog(buddy).
bird(buddy).

% A thing that is a dog is never a bird
conflict :- dog(X), bird(X).

% Validity check: No dog is a mammal
valid_syllogism :- \+ (dog(X), mammal(X)).