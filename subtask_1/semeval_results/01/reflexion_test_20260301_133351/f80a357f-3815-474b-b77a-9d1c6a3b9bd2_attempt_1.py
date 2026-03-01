% Facts for I-premise: Some things with furnitures are reptiles
has_furniture(reptile1).
reptile(reptile1).

% Fail clause for birds: No reptiles are birds
bird(_) :- fail.

% E-premise constraint: No reptile is a bird
conflict :- reptile(X), bird(X).

% Validity check: Some things with furnitures are birds
valid_syllogism :- has_furniture(X), bird(X).