% Counterexample: The mammal is NOT a bird
mammal(dog1).
pet(dog1).

% Fail clause for birds since there are none in this model
bird(_) :- fail.

% E-premise constraint: No bird is a mammal
conflict :- bird(X), mammal(X).

% Validity check: Some pets are birds
valid_syllogism :- pet(X), bird(X).