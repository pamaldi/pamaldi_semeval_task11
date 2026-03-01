% Witness: a bird that is also a mammal
bird(parrot).
mammal(parrot).

% Witness: a dog that is NOT a bird but IS a mammal
dog(rex).
mammal(rex).

% A thing that is a dog is never a bird
conflict :- dog(X), bird(X).

% Validity check: No dog is a mammal
valid_syllogism :- \+ (dog(X), mammal(X)).