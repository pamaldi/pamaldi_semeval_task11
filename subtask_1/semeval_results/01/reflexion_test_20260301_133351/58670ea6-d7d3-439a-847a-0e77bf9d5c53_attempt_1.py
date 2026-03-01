% Witness: a dog that has fur
dog(buddy).
has_fur(buddy).

% cat that is NOT a dog (to satisfy E-premise)
cat(whiskers).

% E-premise constraint: No cat is a dog
conflict :- cat(X), dog(X).

% Rule from A-premise: All dogs have fur
has_fur(X) :- dog(X).

% O-conclusion: Some cats have fur
valid_syllogism :- cat(X), has_fur(X).