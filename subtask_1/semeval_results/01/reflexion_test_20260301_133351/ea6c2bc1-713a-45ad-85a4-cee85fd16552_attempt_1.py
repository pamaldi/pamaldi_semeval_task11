% Facts for I-premise: "A few birds are categorized as pets"
bird(canary).
pet(canary).

% Fail clause for E-premise: "No pets are animals"
animals(_) :- fail.

% Rule from E-premise: "No pets are animals"
conflict :- pet(X), animals(X).

% Rule from I-premise: "Birds are pets"
pet(X) :- bird(X).

% Validity check: "Some birds are not animals"
valid_syllogism :- bird(X), \+ animals(X).